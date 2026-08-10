from uuid import uuid4

from app.services.answer_validation import (
    FIXED_NOT_FOUND_ANSWER,
    clean_generated_answer,
    get_unsupported_requested_role,
)
from app.services.retrieval import RetrievedChunk


def build_chunk(content: str) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=uuid4(),
        chunk_id=uuid4(),
        chunk_index=0,
        content=content,
        similarity_score=0.9,
        original_filename="politika.txt",
    )


def test_approval_condition_is_not_document_approver() -> None:
    chunks = [
        build_chunk(
            "Çalışanlar, yöneticilerinin onayıyla salı ve "
            "perşembe günleri uzaktan çalışabilirler."
        )
    ]
    question = "Belgenin onaylayıcısı kimdir?"

    assert get_unsupported_requested_role(
        question=question,
        retrieved_chunks=chunks,
    ) == "onaylayıcı"

    assert clean_generated_answer(
        answer=(
            "Yöneticiler belgenin onaylayıcısıdır. "
            "[Kaynak 1]"
        ),
        question=question,
        retrieved_chunks=chunks,
    ) == FIXED_NOT_FOUND_ANSWER


def test_explicit_document_approver_is_supported() -> None:
    chunks = [
        build_chunk(
            "Belgeyi onaylayan kişi Selin Ak'tır."
        )
    ]

    assert get_unsupported_requested_role(
        question="Belgenin onaylayıcısı kimdir?",
        retrieved_chunks=chunks,
    ) is None
