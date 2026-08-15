from __future__ import annotations

from uuid import uuid4

import pytest

from app.services import answer_validation
from app.services.retrieval import RetrievedChunk


def make_retrieved_chunk(
    content: str,
    *,
    filename: str | None = "policy.txt",
) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=uuid4(),
        chunk_id=uuid4(),
        chunk_index=0,
        content=content,
        similarity_score=0.9,
        original_filename=filename,
    )


def test_normalize_for_matching_handles_case_accents_and_spaces() -> None:
    assert (
        answer_validation.normalize_for_matching(
            "  İLETİŞİM   ADRESİ ",
        )
        == "iletisim adresi"
    )


@pytest.mark.parametrize(
    ("question", "expected_role"),
    [
        ("Belgenin onaylayıcısı kimdir?", "onaylayıcı"),
        ("Bu belge kime ait?", "sahip"),
        ("Şirketin kurucusu kim?", "kurucu"),
        ("Yönetici kim?", "yönetici"),
    ],
)
def test_find_requested_roles(
    question: str,
    expected_role: str,
) -> None:
    assert expected_role in (
        answer_validation.find_requested_roles(question)
    )


def test_unsupported_single_role_is_rejected() -> None:
    chunks = [
        make_retrieved_chunk(
            "Belgenin sorumlusu Zeynep Aydın'dır.",
        ),
    ]

    assert (
        answer_validation.get_unsupported_requested_role(
            question="Belgenin onaylayıcısı kimdir?",
            retrieved_chunks=chunks,
        )
        == "onaylayıcı"
    )


def test_supported_role_is_not_rejected() -> None:
    chunks = [
        make_retrieved_chunk(
            "Belgenin onaylayıcısı Zeynep Aydın'dır.",
        ),
    ]

    assert (
        answer_validation.get_unsupported_requested_role(
            question="Belgenin onaylayıcısı kimdir?",
            retrieved_chunks=chunks,
        )
        is None
    )


def test_multiple_requested_roles_are_left_to_model() -> None:
    chunks = [make_retrieved_chunk("Belge metni")]

    assert (
        answer_validation.get_unsupported_requested_role(
            question="Sorumlu kim ve onaylayan kim?",
            retrieved_chunks=chunks,
        )
        is None
    )


def test_normalize_citations_converts_and_deduplicates() -> None:
    assert answer_validation.normalize_citations(
        "Bilgi [1] [Kaynak 1] ve başka bilgi [ 2 ].",
    ) == "Bilgi [Kaynak 1] ve başka bilgi [Kaynak 2]."


def test_remove_answer_prefix() -> None:
    assert (
        answer_validation.remove_answer_prefix(
            "Yanıt: Doğrudan cevap",
        )
        == "Doğrudan cevap"
    )


def test_false_not_found_suffix_is_removed_from_answer() -> None:
    assert answer_validation.remove_false_not_found_suffix(
        "Teslim tarihi 15 Ağustos'tur. [Kaynak 1] "
        "Bu ayrıntı seçili belgelerde belirtilmiyor. "
        "[Kaynak 1]",
    ) == "Teslim tarihi 15 Ağustos'tur. [Kaynak 1]"


def test_fixed_not_found_answer_never_keeps_citation() -> None:
    assert answer_validation.normalize_fixed_not_found_answer(
        "Seçili belgelerde bu bilgi bulunmuyor. [1]",
    ) == answer_validation.FIXED_NOT_FOUND_ANSWER


def test_single_source_email_is_preserved_exactly() -> None:
    chunks = [
        make_retrieved_chunk(
            "Bildirim guvenlik@example.com adresine gönderilir.",
        ),
    ]

    assert answer_validation.preserve_exact_email_literals(
        "Bildirim güvenlik@example.com adresine gönderilir.",
        chunks,
    ) == "Bildirim guvenlik@example.com adresine gönderilir."


def test_multiple_source_emails_are_not_guessed() -> None:
    chunks = [
        make_retrieved_chunk(
            "a@example.com ve b@example.com",
        ),
    ]

    answer = "Bildirim c@example.com adresine gönderilir."

    assert answer_validation.preserve_exact_email_literals(
        answer,
        chunks,
    ) == answer


def test_duration_literal_is_restored_from_source() -> None:
    chunks = [
        make_retrieved_chunk(
            "Proje belgeleri 5 yıl boyunca saklanır.",
        ),
    ]

    assert answer_validation.preserve_exact_duration_literals(
        "Belgeler beş yıl saklanır.",
        chunks,
    ) == "Belgeler 5 yıl boyunca saklanır."


def test_retention_subject_is_corrected_from_question() -> None:
    assert answer_validation.correct_retention_subject(
        answer="Belgenin 5 yıl boyunca saklanmaktadır.",
        question="Proje belgeleri ne kadar süre saklanır?",
    ) == "Proje belgeleri 5 yıl boyunca saklanmaktadır."


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ("bilge", "bilgi", True),
        ("kaya", "kayra", True),
        ("aynı", "aynı", False),
        ("kısa", "uzunca", False),
        ("bilge", "başka", False),
    ],
)
def test_is_single_edit_apart(
    left: str,
    right: str,
    expected: bool,
) -> None:
    assert (
        answer_validation.is_single_edit_apart(left, right)
        is expected
    )


def test_near_exact_source_word_is_corrected_with_context() -> None:
    chunks = [
        make_retrieved_chunk(
            "Belge sahibi Bilgi Teknolojileri Direktörlüğüdür.",
        ),
    ]

    assert answer_validation.preserve_near_exact_source_words(
        "Belge sahibi Bilge Teknolojileri Direktörlüğüdür.",
        chunks,
    ) == "Belge sahibi Bilgi Teknolojileri Direktörlüğüdür."


def test_clean_generated_answer_applies_full_pipeline() -> None:
    chunks = [
        make_retrieved_chunk(
            "Bildirim guvenlik@example.com adresine gönderilir.",
        ),
    ]

    answer = answer_validation.clean_generated_answer(
        answer=(
            "Yanıt: Bildirim güvenlik@example.com adresine "
            "gönderilir. [1] Bu ayrıntı seçili belgelerde "
            "belirtilmiyor. [Kaynak 1]"
        ),
        question="Bildirim hangi adrese gönderilir?",
        retrieved_chunks=chunks,
    )

    assert answer == (
        "Bildirim guvenlik@example.com adresine "
        "gönderilir."
    )


def test_clean_generated_answer_blocks_unsupported_role() -> None:
    chunks = [
        make_retrieved_chunk(
            "Belgenin sorumlusu Zeynep Aydın'dır.",
        ),
    ]

    assert answer_validation.clean_generated_answer(
        answer="Onaylayıcı Zeynep Aydın'dır. [Kaynak 1]",
        question="Belgenin onaylayıcısı kimdir?",
        retrieved_chunks=chunks,
    ) == answer_validation.FIXED_NOT_FOUND_ANSWER


def test_inline_citations_are_removed_without_losing_layout() -> None:
    answer = (
        "Akım [Kaynak 1]\n\n"
        "- Elektrik yüklerinin hareketidir. [1]\n"
        "- Birimi amperdir. [Kaynak 2]"
    )

    assert answer_validation.remove_inline_citations(
        answer,
    ) == (
        "Akım\n\n"
        "- Elektrik yüklerinin hareketidir.\n"
        "- Birimi amperdir."
    )


def test_markdown_formatting_is_normalized_for_plain_text_ui() -> None:
    answer = (
        "### Çalışma Notları\n\n"
        "* **Akım:** Elektrik yüklerinin hareketidir.\n"
        "- Formül örneği: 2**3"
    )

    assert (
        answer_validation.normalize_plain_text_formatting(
            answer,
        )
        == (
            "Çalışma Notları\n\n"
            "- Akım: Elektrik yüklerinin hareketidir.\n"
            "- Formül örneği: 2**3"
        )
    )

def test_parenthesized_inline_citations_are_removed() -> None:
    answer = (
        "- Destek bilgileri (Kaynak 1)\n"
        "- Proje bilgileri (Kaynak 2 ve Kaynak 3)"
    )

    assert (
        answer_validation.remove_inline_citations(answer)
        == (
            "- Destek bilgileri\n"
            "- Proje bilgileri"
        )
    )

def test_markdown_link_is_reduced_to_visible_text() -> None:
    answer = (
        "İletişim: "
        "[destek@example.com](mailto:destek@example.com)"
    )

    assert (
        answer_validation.normalize_plain_text_formatting(
            answer,
        )
        == "İletişim: destek@example.com"
    )
