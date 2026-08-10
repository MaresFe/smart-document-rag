from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatSessionCreate(BaseModel):
    title: str | None = Field(
        default=None,
        max_length=120,
    )


class ChatSessionUpdate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=120,
    )


class ChatSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None = None
    created_at: datetime


class ChatMessageCreate(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=8000,
    )


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime


class ChatSourceRead(BaseModel):
    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    similarity_score: float | None
    original_filename: str | None = None


class ChatResponse(BaseModel):
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead
    sources: list[ChatSourceRead]


class ChatSessionDocumentCreate(BaseModel):
    document_ids: list[UUID] = Field(
        default_factory=list,
        max_length=100,
    )


class ChatSessionDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    document_id: UUID
    created_at: datetime