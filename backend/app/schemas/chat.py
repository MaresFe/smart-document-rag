from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatSessionCreate(BaseModel):
    title: str | None = None


class ChatSessionRead(BaseModel):
    id: UUID
    user_id: UUID
    title: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1)


class ChatMessageRead(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSourceRead(BaseModel):
    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    similarity_score: float
    original_filename: str | None = None


class ChatResponse(BaseModel):
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead
    sources: list[ChatSourceRead]

class ChatSessionDocumentCreate(BaseModel):
    document_ids: list[UUID] = Field(min_length=1)


class ChatSessionDocumentRead(BaseModel):
    id: UUID
    session_id: UUID
    document_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)