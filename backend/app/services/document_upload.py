import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


def get_file_extension(filename: str) -> str:
    return Path(filename).suffix.lower().replace(".", "")


def validate_file_extension(filename: str) -> str:
    extension = get_file_extension(filename)

    if extension not in settings.allowed_file_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {extension}",
        )

    return extension


def validate_file_size(file: UploadFile) -> int:
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024

    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {settings.max_upload_size_mb} MB limit.",
        )

    return file_size


def generate_stored_filename(original_filename: str) -> str:
    extension = get_file_extension(original_filename)
    unique_name = uuid.uuid4()
    return f"{unique_name}.{extension}"


def save_upload_file(file: UploadFile) -> tuple[str, str, int, str]:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )

    file_type = validate_file_extension(file.filename)
    file_size = validate_file_size(file)

    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = generate_stored_filename(file.filename)
    storage_path = settings.upload_dir / stored_filename

    with storage_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return stored_filename, str(storage_path), file_size, file_type