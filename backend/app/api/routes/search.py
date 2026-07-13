from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.schemas.search import SearchRequest, SearchResult
from app.services.embedding import EmbeddingError, create_query_embedding


router = APIRouter(
    prefix="/search",
    tags=["Search"],
)


@router.post("", response_model=list[SearchResult])
def search_document_chunks(
    request: SearchRequest,
    db: Session = Depends(get_db),
):
    try:
        query_embedding = create_query_embedding(request.query)
    except EmbeddingError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    distance = DocumentChunk.embedding.cosine_distance(query_embedding)

    statement = (
        select(
            DocumentChunk,
            Document.original_filename,
            distance.label("distance"),
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.embedding.is_not(None))
        .order_by(distance)
        .limit(request.limit)
    )

    rows = db.execute(statement).all()

    results: list[SearchResult] = []

    for chunk, original_filename, chunk_distance in rows:
        similarity_score = 1 - float(chunk_distance)

        results.append(
            SearchResult(
                document_id=chunk.document_id,
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                similarity_score=similarity_score,
                original_filename=original_filename,
            )
        )

    return results