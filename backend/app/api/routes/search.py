from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.search import SearchRequest, SearchResult
from app.services.embedding import EmbeddingError
from app.services.retrieval import retrieve_relevant_chunks


router = APIRouter(
    prefix="/search",
    tags=["Search"],
)


@router.post(
    "",
    response_model=list[SearchResult],
)
def search_document_chunks(
    request: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SearchResult]:
    try:
        retrieved_chunks = retrieve_relevant_chunks(
            db=db,
            query=request.query,
            user_id=current_user.id,
            limit=request.limit,
        )
    except EmbeddingError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return [
        SearchResult(
            document_id=result.document_id,
            chunk_id=result.chunk_id,
            chunk_index=result.chunk_index,
            content=result.content,
            similarity_score=result.similarity_score,
            original_filename=result.original_filename,
        )
        for result in retrieved_chunks
    ]