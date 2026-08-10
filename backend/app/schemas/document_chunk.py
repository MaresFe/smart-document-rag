from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentChunkRead(BaseModel):
    id: UUID
    document_id: UUID
    chunk_index: int
    page_number: int | None = None
    content: str
    source_metadata: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)