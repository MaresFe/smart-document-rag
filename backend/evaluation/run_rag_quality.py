from __future__ import annotations

import argparse
import getpass
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


EVALUATION_DIR = Path(__file__).resolve().parent
DEFAULT_CASES_PATH = EVALUATION_DIR / "cases.json"

ENGLISH_LEAK_PATTERNS = [
    r"\bonly\b",
    r"\binformation\b",
    r"\baccording to\b",
    r"\bthe document\b",
    r"\bnot found\b",
    r"\bsource\b",
]
FALSE_NOT_FOUND_PHRASES = [
    "bulunmuyor",
    "yer almıyor",
    "belirtilmemiştir",
    "belirtilmiyor",
    "bilgi verilmemektedir",
]

LANGUAGE_QUALITY_ERROR_PATTERNS = [
    (
        r"\bbelgenin\b[^.!?\n]{0,80}"
        r"\bsaklanmaktadır\b"
    ),
]

NUMBER_EQUIVALENTS = {
    "0": "sıfır",
    "1": "bir",
    "2": "iki",
    "3": "üç",
    "4": "dört",
    "5": "beş",
    "6": "altı",
    "7": "yedi",
    "8": "sekiz",
    "9": "dokuz",
    "10": "on",
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smart Document RAG Türkçe cevap kalitesi değerlendirmesi.",
    )

    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
    )

    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES_PATH,
    )

    parser.add_argument(
        "--email",
        help="Testte kullanılacak mevcut kullanıcı hesabı.",
    )

    parser.add_argument(
        "--model-label",
        default="configured-model",
        help="Rapor üzerinde gösterilecek model adı.",
    )

    return parser.parse_args()


def normalize_text(value: str) -> str:
    normalized = " ".join(
        value.casefold().split()
    )

    for digit, word in NUMBER_EQUIVALENTS.items():
        normalized = re.sub(
            rf"\b{re.escape(digit)}\b",
            word,
            normalized,
        )

    return normalized


def contains_phrase(text: str, phrase: str) -> bool:
    return normalize_text(phrase) in normalize_text(text)


def contains_citation(text: str) -> bool:
    return re.search(
        r"\[Kaynak\s+\d+\]",
        text,
        flags=re.IGNORECASE,
    ) is not None


def contains_english_leak(text: str) -> bool:
    return any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in ENGLISH_LEAK_PATTERNS
    )


def contains_language_quality_error(
    text: str,
) -> bool:
    return any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        for pattern in LANGUAGE_QUALITY_ERROR_PATTERNS
    )


def require_success(
    response: httpx.Response,
    operation: str,
) -> None:
    if response.is_success:
        return

    detail = response.text[:500]

    raise RuntimeError(
        f"{operation} başarısız "
        f"({response.status_code}): {detail}"
    )


def evaluate_answer(
    case: dict[str, Any],
    answer: str,
    sources: list[dict[str, Any]],
) -> tuple[bool, dict[str, bool]]:
    checks: dict[str, bool] = {}

    required_phrases = case.get(
        "required_phrases",
        [],
    )

    forbidden_phrases = case.get(
        "forbidden_phrases",
        [],
    )

    checks["required_phrases"] = all(
        contains_phrase(answer, phrase)
        for phrase in required_phrases
    )

    checks["forbidden_phrases"] = not any(
        contains_phrase(answer, phrase)
        for phrase in forbidden_phrases
    )
    if case["expected_type"] == "fact":
        checks["no_false_not_found"] = not any(
            contains_phrase(answer, phrase)
            for phrase in FALSE_NOT_FOUND_PHRASES
        )

    if case["expected_type"] == "not_found":
        acceptable_phrases = case.get(
            "acceptable_not_found_phrases",
            [],
        )

        checks["not_found_response"] = any(
            contains_phrase(answer, phrase)
            for phrase in acceptable_phrases
        )

    if case.get("require_citation", False):
        checks["citation"] = contains_citation(answer)
        checks["source_returned"] = len(sources) > 0

    if case.get("forbid_citation", False):
        checks["citation_absent"] = not contains_citation(
        answer,
    )

    checks["turkish_language"] = not contains_english_leak(
        answer,
    )

    checks["language_quality"] = not (
        contains_language_quality_error(answer)
    )

    return all(checks.values()), checks


def safe_filename(value: str) -> str:
    normalized = re.sub(
        r"[^a-zA-Z0-9_.-]+",
        "-",
        value,
    )

    return normalized.strip("-") or "model"


def main() -> int:
    arguments = parse_arguments()

    cases_path = arguments.cases.resolve()
    evaluation_data = json.loads(
        cases_path.read_text(encoding="utf-8"),
    )

    fixture_path = (
        cases_path.parent
        / evaluation_data["document"]
    ).resolve()

    email = arguments.email

    if not email:
        email = input("E-posta: ").strip()

    password = getpass.getpass("Parola: ")

    if not email or not password:
        print(
            "E-posta ve parola zorunludur.",
            file=sys.stderr,
        )
        return 2

    document_id: str | None = None
    active_session_id: str | None = None
    results: list[dict[str, Any]] = []

    with httpx.Client(
        base_url=arguments.base_url.rstrip("/"),
        timeout=180.0,
        follow_redirects=True,
    ) as client:
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

        require_success(
            login_response,
            "Oturum açma",
        )

        try:
            with fixture_path.open("rb") as fixture_file:
                upload_response = client.post(
                    "/api/documents",
                    files={
                        "file": (
                            fixture_path.name,
                            fixture_file,
                            "text/plain",
                        ),
                    },
                )

            require_success(
                upload_response,
                "Test belgesini yükleme",
            )

            document_id = upload_response.json()["id"]

            for index, case in enumerate(
                evaluation_data["cases"],
                start=1,
            ):
                started_at = time.perf_counter()

                try:
                    session_response = client.post(
                        "/api/chat/sessions",
                        json={
                            "title": (
                                "RAG kalite testi - "
                                f"{case['id']}"
                            ),
                        },
                    )

                    require_success(
                        session_response,
                        "Test sohbetini oluşturma",
                    )

                    active_session_id = (
                        session_response.json()["id"]
                    )

                    attach_response = client.post(
                        (
                            "/api/chat/sessions/"
                            f"{active_session_id}/documents"
                        ),
                        json={
                            "document_ids": [
                                document_id,
                            ],
                        },
                    )

                    require_success(
                        attach_response,
                        "Belgeyi sohbete bağlama",
                    )

                    message_response = client.post(
                        (
                            "/api/chat/sessions/"
                            f"{active_session_id}/messages"
                        ),
                        json={
                            "content": case["question"],
                        },
                    )

                    require_success(
                        message_response,
                        "Soruyu gönderme",
                    )

                    elapsed_seconds = (
                        time.perf_counter() - started_at
                    )

                    response_data = message_response.json()
                    answer = response_data[
                        "assistant_message"
                    ]["content"]

                    sources = response_data.get(
                        "sources",
                        [],
                    )

                    passed, checks = evaluate_answer(
                        case=case,
                        answer=answer,
                        sources=sources,
                    )

                    result = {
                        "id": case["id"],
                        "question": case["question"],
                        "answer": answer,
                        "passed": passed,
                        "checks": checks,
                        "source_count": len(sources),
                        "elapsed_seconds": round(
                            elapsed_seconds,
                            3,
                        ),
                    }

                except Exception as error:
                    elapsed_seconds = (
                        time.perf_counter() - started_at
                    )

                    result = {
                        "id": case["id"],
                        "question": case["question"],
                        "answer": None,
                        "passed": False,
                        "checks": {},
                        "source_count": 0,
                        "elapsed_seconds": round(
                            elapsed_seconds,
                            3,
                        ),
                        "error": str(error),
                    }

                finally:
                    if active_session_id is not None:
                        client.delete(
                            (
                                "/api/chat/sessions/"
                                f"{active_session_id}"
                            ),
                        )

                        active_session_id = None

                results.append(result)

                status_label = (
                    "GEÇTİ"
                    if result["passed"]
                    else "KALDI"
                )

                print(
                    f"[{index}] {case['id']}: "
                    f"{status_label} "
                    f"({result['elapsed_seconds']} sn)"
                )

                if result.get("answer"):
                    print(
                        f"    Cevap: {result['answer']}"
                    )

                if result.get("error"):
                    print(
                        f"    Hata: {result['error']}"
                    )

                if (
                    not result["passed"]
                    and result.get("checks")
                ):
                    failed_checks = [
                        check_name
                        for check_name, check_passed
                        in result["checks"].items()
                        if not check_passed
                    ]

                    print(
                        "    Başarısız kontroller: "
                        + ", ".join(failed_checks)
                    )

        finally:
            if active_session_id is not None:
                client.delete(
                    (
                        "/api/chat/sessions/"
                        f"{active_session_id}"
                    ),
                )

            if document_id is not None:
                client.delete(
                    f"/api/documents/{document_id}",
                )

            client.post("/api/auth/logout")

    passed_count = sum(
        1
        for result in results
        if result["passed"]
    )

    total_count = len(results)

    average_seconds = (
        sum(
            result["elapsed_seconds"]
            for result in results
        )
        / total_count
        if total_count
        else 0.0
    )

    report = {
        "dataset": evaluation_data["dataset"],
        "model_label": arguments.model_label,
        "created_at": datetime.now(
            timezone.utc,
        ).isoformat(),
        "summary": {
            "passed": passed_count,
            "failed": total_count - passed_count,
            "total": total_count,
            "score_percent": round(
                100 * passed_count / total_count,
                2,
            )
            if total_count
            else 0.0,
            "average_seconds": round(
                average_seconds,
                3,
            ),
        },
        "results": results,
    }

    results_directory = (
        EVALUATION_DIR / "results"
    )

    results_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S",
    )

    model_filename = safe_filename(
        arguments.model_label,
    )

    report_path = (
        results_directory
        / f"{timestamp}-{model_filename}.json"
    )

    report_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(
        f"Sonuç: {passed_count}/{total_count} "
        f"(%{report['summary']['score_percent']})"
    )

    print(
        "Ortalama cevap süresi: "
        f"{report['summary']['average_seconds']} saniye"
    )

    print(f"Rapor: {report_path}")

    return 0 if passed_count == total_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
