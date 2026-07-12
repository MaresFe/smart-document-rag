from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    id: UUID
    user_id: UUID
    original_filename: str
    stored_filename: str
    file_type: str
    mime_type: str | None = None
    file_size: int | None = None
    storage_path: str
    status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)