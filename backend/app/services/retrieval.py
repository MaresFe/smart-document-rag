import logging
import re
from dataclasses import dataclass
from time import perf_counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.embedding import (
    create_query_embedding,
)


performance_logger = logging.getLogger(
    "uvicorn.error",
)


@dataclass
class RetrievedChunk:
    document_id: UUID
    chunk_id: UUID
    chunk_index: int
    content: str
    similarity_score: float
    original_filename: str | None


STRUCTURED_REQUEST_PATTERN = re.compile(
    (
        r"\b(?:"
        r"özet\w*|"
        r"liste\w*|"
        r"madde\w*|"
        r"not(?:lar)?\s+(?:çıkar\w*|hazırla\w*)|"
        r"çalışma\s+not\w*|"
        r"konu\s+başlık\w*|"
        r"ana\s+(?:fikir|konu)\w*|"
        r"önemli\s+(?:bilgi|nokta|kural)\w*"
        r")\b"
    ),
    flags=re.IGNORECASE,
)


def is_structured_document_request(
    query: str,
) -> bool:
    return STRUCTURED_REQUEST_PATTERN.search(
        query.strip(),
    ) is not None


def get_evenly_spaced_indexes(
    total: int,
    limit: int,
) -> list[int]:
    if total <= limit:
        return list(range(total))

    if limit == 1:
        return [0]

    return [
        round(index * (total - 1) / (limit - 1))
        for index in range(limit)
    ]


def count_meaningful_query_characters(
    query: str,
) -> int:
    return sum(
        1
        for character in query
        if character.isalnum()
    )


def is_meaningful_query(query: str) -> bool:
    return (
        count_meaningful_query_characters(query)
        >= settings.retrieval_min_query_characters
    )


def get_safe_similarity_threshold() -> float:
    return min(
        1.0,
        max(
            -1.0,
            settings.retrieval_min_similarity_score,
        ),
    )


def retrieve_relevant_chunks(
    db: Session,
    query: str,
    user_id: UUID,
    limit: int = 5,
    document_ids: list[UUID] | None = None,
) -> list[RetrievedChunk]:
    total_started = perf_counter()
    normalized_query = query.strip()

    if not is_meaningful_query(normalized_query):
        performance_logger.info(
            "RAG retrieval timing | "
            "skipped=true | "
            "reason=query_too_short | "
            "meaningful_characters=%d | "
            "required_characters=%d",
            count_meaningful_query_characters(
                normalized_query,
            ),
            settings.retrieval_min_query_characters,
        )

        return []

    if document_ids is not None and not document_ids:
        performance_logger.info(
            "RAG retrieval timing | "
            "skipped=true | "
            "reason=no_linked_documents"
        )

        return []

    safe_limit = min(
        max(limit, 1),
        20,
    )

    minimum_similarity = (
        get_safe_similarity_threshold()
    )

    embedding_started = perf_counter()

    query_embedding = create_query_embedding(
        normalized_query,
    )

    embedding_ms = (
        perf_counter() - embedding_started
    ) * 1000

    distance = (
        DocumentChunk.embedding.cosine_distance(
            query_embedding,
        )
    )

    statement = (
        select(
            DocumentChunk,
            Document.original_filename,
            distance.label("distance"),
        )
        .join(
            Document,
            Document.id
            == DocumentChunk.document_id,
        )
        .where(
            Document.user_id == user_id,
            DocumentChunk.embedding.is_not(None),
            Document.status == "ready",
        )
    )

    if document_ids is not None:
        statement = statement.where(
            DocumentChunk.document_id.in_(
                document_ids,
            ),
        )

    statement = (
        statement
        .order_by(distance)
        .limit(safe_limit)
    )

    database_started = perf_counter()

    rows = db.execute(statement).all()

    database_ms = (
        perf_counter() - database_started
    ) * 1000

    result_build_started = perf_counter()

    results: list[RetrievedChunk] = []
    rejected_count = 0
    top_similarity: float | None = None

    for (
        chunk,
        original_filename,
        chunk_distance,
    ) in rows:
        similarity_score = (
            1 - float(chunk_distance)
        )

        if (
            top_similarity is None
            or similarity_score > top_similarity
        ):
            top_similarity = similarity_score

        if similarity_score < minimum_similarity:
            rejected_count += 1
            continue

        results.append(
            RetrievedChunk(
                document_id=chunk.document_id,
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                similarity_score=similarity_score,
                original_filename=(
                    original_filename
                ),
            )
        )

    result_build_ms = (
        perf_counter() - result_build_started
    ) * 1000

    total_ms = (
        perf_counter() - total_started
    ) * 1000

    top_similarity_text = (
        f"{top_similarity:.4f}"
        if top_similarity is not None
        else "none"
    )

    performance_logger.info(
        "RAG retrieval timing | "
        "embedding_ms=%.2f | "
        "database_ms=%.2f | "
        "result_build_ms=%.2f | "
        "total_ms=%.2f | "
        "candidate_count=%d | "
        "source_count=%d | "
        "rejected_count=%d | "
        "minimum_similarity=%.4f | "
        "top_similarity=%s",
        embedding_ms,
        database_ms,
        result_build_ms,
        total_ms,
        len(rows),
        len(results),
        rejected_count,
        minimum_similarity,
        top_similarity_text,
    )

    return results


def retrieve_document_overview_chunks(
    db: Session,
    query: str,
    user_id: UUID,
    limit: int = 10,
    document_ids: list[UUID] | None = None,
) -> list[RetrievedChunk]:
    """Select chunks spread across linked documents.

    Summary, note and list requests are broad. A semantic
    threshold can reject them even when a document is
    selected, so this path samples the beginning, middle
    and end of the selected content.
    """
    total_started = perf_counter()

    if document_ids is not None and not document_ids:
        return []

    safe_limit = min(max(limit, 1), 20)
    normalized_query = query.strip()

    embedding_started = perf_counter()

    query_embedding = create_query_embedding(
        normalized_query,
    )

    embedding_ms = (
        perf_counter() - embedding_started
    ) * 1000

    distance = (
        DocumentChunk.embedding.cosine_distance(
            query_embedding,
        )
    )

    statement = (
        select(
            DocumentChunk,
            Document.original_filename,
            distance.label("distance"),
        )
        .join(
            Document,
            Document.id
            == DocumentChunk.document_id,
        )
        .where(
            Document.user_id == user_id,
            DocumentChunk.embedding.is_not(None),
            Document.status == "ready",
        )
    )

    if document_ids is not None:
        statement = statement.where(
            DocumentChunk.document_id.in_(
                document_ids,
            ),
        )

    statement = statement.order_by(
        DocumentChunk.document_id,
        DocumentChunk.chunk_index,
    )

    database_started = perf_counter()
    rows = db.execute(statement).all()

    database_ms = (
        perf_counter() - database_started
    ) * 1000

    selected_indexes = get_evenly_spaced_indexes(
        total=len(rows),
        limit=safe_limit,
    )

    results: list[RetrievedChunk] = []

    for row_index in selected_indexes:
        (
            chunk,
            original_filename,
            chunk_distance,
        ) = rows[row_index]

        similarity_score = max(
            -1.0,
            min(
                1.0,
                1 - float(chunk_distance),
            ),
        )

        results.append(
            RetrievedChunk(
                document_id=chunk.document_id,
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                similarity_score=similarity_score,
                original_filename=(
                    original_filename
                ),
            ),
        )

    total_ms = (
        perf_counter() - total_started
    ) * 1000

    performance_logger.info(
        "RAG overview retrieval timing | "
        "embedding_ms=%.2f | "
        "database_ms=%.2f | "
        "total_ms=%.2f | "
        "candidate_count=%d | "
        "source_count=%d",
        embedding_ms,
        database_ms,
        total_ms,
        len(rows),
        len(results),
    )

    return results
