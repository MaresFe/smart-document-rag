from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx
import pytest

from app.services import llm
from app.services.answer_validation import FIXED_NOT_FOUND_ANSWER
from app.services.retrieval import RetrievedChunk


class FakeResponse:
    def __init__(self, data: dict[str, object]) -> None:
        self.data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self.data


def make_retrieved_chunk(
    content: str = "Projenin kodu MAVI-27'dir.",
    *,
    filename: str | None = "project.txt",
) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=uuid4(),
        chunk_id=uuid4(),
        chunk_index=0,
        content=content,
        similarity_score=0.91,
        original_filename=filename,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1_500_000, 1.5),
        (2_000_000.0, 2.0),
        (None, 0.0),
        ("100", 0.0),
    ],
)
def test_nanoseconds_to_ms(
    value: object,
    expected: float,
) -> None:
    assert llm.nanoseconds_to_ms(value) == expected


def test_build_context_numbers_sources_and_handles_missing_filename() -> None:
    chunks = [
        make_retrieved_chunk("  Birinci içerik  "),
        make_retrieved_chunk(
            "İkinci içerik",
            filename=None,
        ),
    ]

    context = llm.build_context_from_chunks(chunks)

    assert "### Kaynak 1" in context
    assert "Dosya: project.txt" in context
    assert "Birinci içerik" in context
    assert "### Kaynak 2" in context
    assert "Dosya: Dosya adı bilinmiyor" in context
    assert "\n\n---\n\n" in context


def test_build_rag_prompt_uses_explicit_boundaries() -> None:
    prompt = llm.build_rag_prompt(
        question="Proje kodu nedir?",
        retrieved_chunks=[make_retrieved_chunk()],
    )

    assert "<kaynaklar>" in prompt
    assert "</kaynaklar>" in prompt
    assert "<soru>\nProje kodu nedir?\n</soru>" in prompt
    assert "Projenin kodu MAVI-27'dir." in prompt


def test_generate_answer_without_chunks_does_not_call_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_http(*args: object, **kwargs: object) -> None:
        raise AssertionError((args, kwargs))

    monkeypatch.setattr(llm.httpx, "post", fail_http)

    assert llm.generate_answer_with_ollama(
        question="Soru",
        retrieved_chunks=[],
    ) == FIXED_NOT_FOUND_ANSWER


def test_generate_answer_rejects_unsupported_role_before_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunks = [
        make_retrieved_chunk(
            "Belgenin sorumlusu Zeynep Aydın'dır.",
        ),
    ]

    def fail_http(*args: object, **kwargs: object) -> None:
        raise AssertionError((args, kwargs))

    monkeypatch.setattr(llm.httpx, "post", fail_http)

    assert llm.generate_answer_with_ollama(
        question="Belgenin onaylayıcısı kimdir?",
        retrieved_chunks=chunks,
    ) == FIXED_NOT_FOUND_ANSWER


def test_generate_answer_sends_deterministic_request_and_cleans_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_post(
        url: str,
        *,
        json: dict[str, object],
        timeout: int,
    ) -> FakeResponse:
        captured.update(
            {
                "url": url,
                "json": json,
                "timeout": timeout,
            },
        )
        return FakeResponse(
            {
                "response": (
                    "Yanıt: Projenin kodu MAVI-27'dir. [1]"
                ),
                "total_duration": 2_000_000,
                "load_duration": 500_000,
                "prompt_eval_duration": 600_000,
                "eval_duration": 700_000,
                "prompt_eval_count": 20,
                "eval_count": 10,
            },
        )

    monkeypatch.setattr(llm.httpx, "post", fake_post)

    result = llm.generate_answer_with_ollama(
        question="Proje kodu nedir?",
        retrieved_chunks=[make_retrieved_chunk()],
    )

    assert result == "Projenin kodu MAVI-27'dir."
    assert captured["url"] == (
        f"{llm.settings.ollama_base_url}/api/generate"
    )
    assert captured["timeout"] == (
        llm.settings.llm_timeout_seconds
    )

    payload = captured["json"]
    assert isinstance(payload, dict)
    assert payload["model"] == llm.settings.ollama_model
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["options"] == {
        "num_ctx": llm.settings.llm_context_window,
        "temperature": 0.0,
        "seed": 42,
        "num_predict": (
            llm.settings.llm_max_output_tokens
        ),
        "repeat_penalty": 1.1,
    }


def test_generate_answer_wraps_http_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx.Request(
        "POST",
        "http://localhost:11434/api/generate",
    )
    original_error = httpx.ConnectError(
        "connection refused",
        request=request,
    )

    def raise_http_error(*args: object, **kwargs: object) -> None:
        raise original_error

    monkeypatch.setattr(
        llm.httpx,
        "post",
        raise_http_error,
    )

    with pytest.raises(
        llm.LLMError,
        match="LLM response could not be generated",
    ) as captured:
        llm.generate_answer_with_ollama(
            question="Proje kodu nedir?",
            retrieved_chunks=[make_retrieved_chunk()],
        )

    assert captured.value.__cause__ is original_error


def test_generate_answer_wraps_invalid_json_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class InvalidResponse(FakeResponse):
        def json(self) -> dict[str, object]:
            raise ValueError("invalid json")

    monkeypatch.setattr(
        llm.httpx,
        "post",
        lambda *args, **kwargs: InvalidResponse({}),
    )

    with pytest.raises(
        llm.LLMError,
        match="LLM returned an invalid response",
    ):
        llm.generate_answer_with_ollama(
            question="Proje kodu nedir?",
            retrieved_chunks=[make_retrieved_chunk()],
        )


def test_generate_answer_rejects_empty_cleaned_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        llm.httpx,
        "post",
        lambda *args, **kwargs: FakeResponse(
            {"response": "  "},
        ),
    )

    with pytest.raises(
        llm.LLMError,
        match="empty response",
    ):
        llm.generate_answer_with_ollama(
            question="Proje kodu nedir?",
            retrieved_chunks=[make_retrieved_chunk()],
        )


def test_warm_up_ollama_sends_non_streaming_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_post(
        url: str,
        *,
        json: dict[str, object],
        timeout: int,
    ) -> FakeResponse:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse(
            {"load_duration": 0},
        )

    monkeypatch.setattr(llm.httpx, "post", fake_post)

    llm.warm_up_ollama()

    assert captured["url"] == (
        f"{llm.settings.ollama_base_url}/api/generate"
    )
    assert captured["json"] == {
        "model": llm.settings.ollama_model,
        "prompt": "",
        "stream": False,
        "think": False,
        "keep_alive": llm.settings.ollama_keep_alive,
    }


def test_warm_up_ollama_wraps_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx.Request(
        "POST",
        "http://localhost:11434/api/generate",
    )
    original_error = httpx.ConnectError(
        "connection refused",
        request=request,
    )

    def raise_http_error(*args: object, **kwargs: object) -> None:
        raise original_error

    monkeypatch.setattr(
        llm.httpx,
        "post",
        raise_http_error,
    )

    with pytest.raises(
        llm.LLMError,
        match="Ollama model could not be warmed up",
    ) as captured:
        llm.warm_up_ollama()

    assert captured.value.__cause__ is original_error


def test_generate_answer_rejects_unsupported_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        llm.settings,
        "llm_provider",
        "unsupported",
    )

    with pytest.raises(
        llm.LLMError,
        match="Unsupported LLM provider",
    ):
        llm.generate_answer(
            question="Soru",
            retrieved_chunks=[make_retrieved_chunk()],
        )


def test_structured_request_uses_expanded_answer_settings() -> None:
    question = "Belgeyi özetleyip maddeler halinde listele."

    assert llm.get_max_output_tokens(
        question,
    ) == llm.settings.llm_structured_max_output_tokens

    instruction = llm.get_answer_format_instruction(
        question,
    )

    assert "'- ' ile başlayan kısa maddeler" in instruction
    assert "ilgili konuları atlama" in instruction

def test_structured_prompt_forbids_false_not_found() -> None:
    prompt = llm.build_rag_prompt(
        question=(
            "Seçili belgeleri ana başlıklar altında özetle."
        ),
        retrieved_chunks=[make_retrieved_chunk()],
    )

    assert "bilgi bulunamadı cevabını verme" in prompt
    assert "ana konuları ve önemli bilgileri" in prompt
    assert "Tek paragraf yazma" in prompt
    assert "Her ana konu için ayrı bir başlık" in prompt
