import pytest

from app.services.chunking import (
    chunk_text,
    split_long_text,
)


def test_chunk_text_returns_empty_list_for_blank_text() -> None:
    assert chunk_text("  \n\n  ") == []


def test_chunk_text_combines_paragraphs_within_limit() -> None:
    chunks = chunk_text(
        "Birinci paragraf.\n\nİkinci paragraf.",
        max_chars=40,
        overlap=5,
    )

    assert chunks == [
        "Birinci paragraf.\n\nİkinci paragraf.",
    ]


def test_chunk_text_separates_paragraphs_over_limit() -> None:
    chunks = chunk_text(
        "Birinci paragraf.\n\nİkinci paragraf.",
        max_chars=20,
        overlap=5,
    )

    assert chunks == [
        "Birinci paragraf.",
        "İkinci paragraf.",
    ]


def test_split_long_text_preserves_configured_overlap() -> None:
    chunks = split_long_text(
        text="abcdefghij",
        max_chars=4,
        overlap=1,
    )

    assert chunks == [
        "abcd",
        "defg",
        "ghij",
        "j",
    ]


def test_long_paragraph_is_split_into_bounded_chunks() -> None:
    chunks = chunk_text(
        "0123456789abcdefghij",
        max_chars=8,
        overlap=2,
    )

    assert chunks
    assert all(len(chunk) <= 8 for chunk in chunks)
    assert chunks[0][-2:] == chunks[1][:2]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("  kısa metin  ", ["kısa metin"]),
        ("ilk\r\n\r\nikinci", ["ilk\n\nikinci"]),
    ],
)
def test_chunk_text_normalizes_outer_whitespace_and_newlines(
    text: str,
    expected: list[str],
) -> None:
    assert chunk_text(text, max_chars=100) == expected
