from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    document_id: UUID
    chunk_id: UUID
    chunk_index: int
    content: str
    similarity_score: float
    original_filename: str | None = None