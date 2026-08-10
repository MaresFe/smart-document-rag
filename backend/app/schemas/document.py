from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    file_type: str
    mime_type: str | None = None
    file_size: int | None = None
    status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime