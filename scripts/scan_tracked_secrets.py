from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ALLOWED_ENV_FILES = {
    ".env.example",
    "frontend/.env.example",
}

SENSITIVE_SUFFIXES = {
    ".jks",
    ".key",
    ".p12",
    ".pfx",
}

SENSITIVE_FILENAMES = {
    "id_ed25519",
    "id_rsa",
}

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[bytes]], ...] = (
    (
        "private key",
        re.compile(
            rb"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----",
        ),
    ),
    (
        "AWS access key",
        re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    ),
    (
        "GitHub token",
        re.compile(
            rb"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})\b",
        ),
    ),
    (
        "OpenAI API key",
        re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b"),
    ),
    (
        "Slack token",
        re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    ),
    (
        "Stripe live secret",
        re.compile(rb"\bsk_live_[A-Za-z0-9]{20,}\b"),
    ),
    (
        "Google API key",
        re.compile(rb"\bAIza[0-9A-Za-z_-]{35}\b"),
    ),
    (
        "SendGrid API key",
        re.compile(rb"\bSG\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
    ),
)


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
    )

    return [
        Path(value.decode("utf-8"))
        for value in result.stdout.split(b"\0")
        if value
    ]


def is_forbidden_filename(path: Path) -> bool:
    normalized = path.as_posix()

    if normalized in ALLOWED_ENV_FILES:
        return False

    name = path.name.lower()

    if name == ".env" or name.startswith(".env."):
        return True

    if name in SENSITIVE_FILENAMES:
        return True

    return path.suffix.lower() in SENSITIVE_SUFFIXES


def scan_file(path: Path) -> list[str]:
    try:
        content = path.read_bytes()
    except OSError as error:
        return [f"dosya okunamadı: {error}"]

    return [
        label
        for label, pattern in SECRET_PATTERNS
        if pattern.search(content)
    ]


def main() -> int:
    findings: list[tuple[Path, str]] = []

    for path in tracked_files():
        if not path.is_file():
            continue

        if is_forbidden_filename(path):
            findings.append(
                (path, "hassas dosya adı Git tarafından takip ediliyor"),
            )

        for label in scan_file(path):
            findings.append((path, label))

    if not findings:
        print("Takip edilen dosyalarda bilinen secret kalıbı bulunmadı.")
        return 0

    print("Secret taraması başarısız:", file=sys.stderr)

    for path, reason in findings:
        print(f"- {path.as_posix()}: {reason}", file=sys.stderr)

    print(
        "Değeri Git geçmişinden de kaldırın ve ilgili anahtarı hemen yenileyin.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
