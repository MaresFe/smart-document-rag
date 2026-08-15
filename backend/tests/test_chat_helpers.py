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


def test_retrieval_fallback_uses_source_panel() -> None:
    answer = build_retrieval_based_answer(
        question="Belge ne anlatıyor?",
        retrieved_chunks=[
            make_retrieved_chunk("Birinci kaynak"),
            make_retrieved_chunk(
                "İkinci kaynak",
                filename=None,
            ),
        ],
    )

    assert answer == (
        "Yanıt modeli şu anda kullanılamıyor. "
        "İlgili belge parçalarını Kaynaklar "
        "panelinden inceleyebilirsiniz."
    )
    assert "Belge ne anlatıyor?" not in answer
    assert "[Kaynak" not in answer
    assert "Birinci kaynak" not in answer
