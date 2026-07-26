from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.embedding import create_query_embedding


@dataclass
class RetrievedChunk:
    document_id: UUID
    chunk_id: UUID
    chunk_index: int
    content: str
    similarity_score: float
    original_filename: str | None


def retrieve_relevant_chunks(
    db: Session,
    query: str,
    user_id: UUID,
    limit: int = 5,
    document_ids: list[UUID] | None = None,
) -> list[RetrievedChunk]:
    if document_ids is not None and not document_ids:
        return []

    safe_limit = min(max(limit, 1), 20)

    query_embedding = create_query_embedding(query)

    distance = DocumentChunk.embedding.cosine_distance(
        query_embedding,
    )

    statement = (
        select(
            DocumentChunk,
            Document.original_filename,
            distance.label("distance"),
        )
        .join(
            Document,
            Document.id == DocumentChunk.document_id,
        )
        .where(
            Document.user_id == user_id,
            DocumentChunk.embedding.is_not(None),
            Document.status == "ready",
        )
    )

    if document_ids is not None:
        statement = statement.where(
            DocumentChunk.document_id.in_(document_ids),
        )

    statement = (
        statement
        .order_by(distance)
        .limit(safe_limit)
    )

    rows = db.execute(statement).all()

    results: list[RetrievedChunk] = []

    for chunk, original_filename, chunk_distance in rows:
        similarity_score = 1 - float(chunk_distance)

        results.append(
            RetrievedChunk(
                document_id=chunk.document_id,
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                similarity_score=similarity_score,
                original_filename=original_filename,
            )
        )

    return results