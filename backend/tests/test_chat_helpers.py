from uuid import uuid4

from app.api.routes.chat import (
    build_retrieval_based_answer,
)
from app.services.answer_validation import (
    FIXED_NOT_FOUND_ANSWER,
)
from app.services.retrieval import RetrievedChunk


def make_retrieved_chunk(
    content: str,
    *,
    filename: str | None = "source.txt",
) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=uuid4(),
        chunk_id=uuid4(),
        chunk_index=0,
        content=content,
        similarity_score=0.88,
        original_filename=filename,
    )


def test_retrieval_fallback_without_chunks_returns_fixed_answer() -> None:
    assert build_retrieval_based_answer(
        question="Soru",
        retrieved_chunks=[],
    ) == FIXED_NOT_FOUND_ANSWER


def test_retrieval_fallback_lists_sources_and_truncates_content() -> None:
    long_content = "a" * 750

    answer = build_retrieval_based_answer(
        question="Belge ne anlatıyor?",
        retrieved_chunks=[
            make_retrieved_chunk(long_content),
            make_retrieved_chunk(
                "İkinci kaynak",
                filename=None,
            ),
        ],
    )

    assert answer.startswith(
        "Yanıt modeli şu anda kullanılamıyor.",
    )
    assert "Soru: Belge ne anlatıyor?" in answer
    assert "[Kaynak 1 - source.txt]" in answer
    assert f"{'a' * 700}..." in answer
    assert "[Kaynak 2 - None]\nİkinci kaynak" in answer
