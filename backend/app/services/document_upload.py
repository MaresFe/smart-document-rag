import shutil
import uuid
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


TEXT_SAMPLE_SIZE = 64 * 1024
MAX_ARCHIVE_ENTRY_COUNT = 10_000
MAX_ARCHIVE_UNCOMPRESSED_SIZE = 100 * 1024 * 1024

OFFICE_REQUIRED_ENTRIES = {
    "docx": {
        "[Content_Types].xml",
        "word/document.xml",
    },
    "xlsx": {
        "[Content_Types].xml",
        "xl/workbook.xml",
    },
}


def reset_file_position(file: UploadFile) -> None:
    file.file.seek(0)


def get_file_extension(filename: str) -> str:
    return Path(filename).suffix.lower().removeprefix(".")


def validate_filename(filename: str) -> None:
    normalized_filename = filename.strip()

    if not normalized_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dosya adı gereklidir.",
        )

    if len(normalized_filename) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dosya adı 255 karakterden uzun olamaz.",
        )

    if any(
        ord(character) < 32
        for character in normalized_filename
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dosya adı geçersiz karakterler içeriyor.",
        )


def validate_file_extension(filename: str) -> str:
    extension = get_file_extension(filename)

    if not extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dosyanın uzantısı bulunmuyor.",
        )

    if extension not in settings.allowed_file_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Desteklenmeyen dosya türü: {extension}. "
                "Desteklenen türler: PDF, DOCX, TXT, CSV ve XLSX."
            ),
        )

    return extension


def validate_file_size(file: UploadFile) -> int:
    file.file.seek(0, 2)
    file_size = file.file.tell()
    reset_file_position(file)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Boş dosyalar yüklenemez.",
        )

    max_size_bytes = (
        settings.max_upload_size_mb
        * 1024
        * 1024
    )

    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            ),
            detail=(
                "Dosya boyutu "
                f"{settings.max_upload_size_mb} MB "
                "sınırını aşıyor."
            ),
        )

    return file_size


def validate_pdf_content(file: UploadFile) -> None:
    try:
        reset_file_position(file)
        header = file.file.read(1024)

        if b"%PDF-" not in header:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Dosyanın içeriği geçerli bir PDF "
                    "dosyasıyla eşleşmiyor."
                ),
            )
    finally:
        reset_file_position(file)


def validate_office_archive(
    file: UploadFile,
    file_type: str,
) -> None:
    required_entries = OFFICE_REQUIRED_ENTRIES[file_type]

    try:
        reset_file_position(file)

        with ZipFile(file.file) as archive:
            entries = archive.infolist()

            if len(entries) > MAX_ARCHIVE_ENTRY_COUNT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Office dosyası güvenli giriş "
                        "sayısı sınırını aşıyor."
                    ),
                )

            total_uncompressed_size = sum(
                entry.file_size
                for entry in entries
            )

            if (
                total_uncompressed_size
                > MAX_ARCHIVE_UNCOMPRESSED_SIZE
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Office dosyasının açılmış boyutu "
                        "güvenlik sınırını aşıyor."
                    ),
                )

            if any(
                entry.flag_bits & 0x1
                for entry in entries
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Parola korumalı Office dosyaları "
                        "desteklenmiyor."
                    ),
                )

            archive_names = {
                entry.filename
                for entry in entries
            }

            missing_entries = (
                required_entries - archive_names
            )

            if missing_entries:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Dosyanın içeriği geçerli bir "
                        f"{file_type.upper()} dosyasıyla "
                        "eşleşmiyor."
                    ),
                )

            corrupted_entry = archive.testzip()

            if corrupted_entry is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"{file_type.upper()} dosyası "
                        "bozuk veya eksik içerik barındırıyor."
                    ),
                )

    except BadZipFile as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Dosyanın içeriği geçerli bir "
                f"{file_type.upper()} dosyasıyla eşleşmiyor."
            ),
        ) from error

    finally:
        reset_file_position(file)


def validate_text_content(
    file: UploadFile,
    file_type: str,
) -> None:
    try:
        reset_file_position(file)
        sample = file.file.read(TEXT_SAMPLE_SIZE)

        if b"\x00" in sample:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"{file_type.upper()} dosyası "
                    "ikili veya geçersiz içerik barındırıyor."
                ),
            )

        decoded_sample: str | None = None

        for encoding in (
            "utf-8-sig",
            "utf-8",
            "cp1254",
            "windows-1252",
            "latin-1",
        ):
            try:
                decoded_sample = sample.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if decoded_sample is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"{file_type.upper()} dosyasının "
                    "karakter kodlaması okunamadı."
                ),
            )

        if not decoded_sample.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Boş dosyalar yüklenemez.",
            )

        readable_character_count = sum(
            character.isprintable()
            or character in "\r\n\t"
            for character in decoded_sample
        )

        readable_ratio = (
            readable_character_count
            / max(len(decoded_sample), 1)
        )

        if readable_ratio < 0.85:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"{file_type.upper()} dosyası "
                    "okunabilir metin içermiyor."
                ),
            )

    finally:
        reset_file_position(file)


def validate_file_content(
    file: UploadFile,
    file_type: str,
) -> None:
    if file_type == "pdf":
        validate_pdf_content(file)
        return

    if file_type in OFFICE_REQUIRED_ENTRIES:
        validate_office_archive(
            file=file,
            file_type=file_type,
        )
        return

    if file_type in {"txt", "csv"}:
        validate_text_content(
            file=file,
            file_type=file_type,
        )


def generate_stored_filename(
    original_filename: str,
) -> str:
    extension = get_file_extension(
        original_filename,
    )
    unique_name = uuid.uuid4()

    return f"{unique_name}.{extension}"


def save_upload_file(
    file: UploadFile,
) -> tuple[str, str, int, str]:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dosya adı gereklidir.",
        )

    validate_filename(file.filename)

    file_type = validate_file_extension(
        file.filename,
    )
    file_size = validate_file_size(file)

    validate_file_content(
        file=file,
        file_type=file_type,
    )

    settings.upload_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    stored_filename = generate_stored_filename(
        file.filename,
    )
    storage_path = (
        settings.upload_dir / stored_filename
    )

    try:
        reset_file_position(file)

        with storage_path.open("wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer,
            )

    except OSError as error:
        storage_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Dosya sunucuya kaydedilemedi.",
        ) from error

    finally:
        reset_file_position(file)

    return (
        stored_filename,
        str(storage_path),
        file_size,
        file_type,
    )