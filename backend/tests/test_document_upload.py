from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image

from app.core.config import settings
from app.services.document_upload import (
    validate_file_content,
    validate_file_extension,
    validate_file_size,
)


def create_upload(
    filename: str,
    content: bytes,
) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
    )


def create_image_bytes(
    image_format: str,
    size: tuple[int, int] = (320, 180),
) -> bytes:
    buffer = BytesIO()

    with Image.new("RGB", size, "white") as image:
        image.save(buffer, format=image_format)

    return buffer.getvalue()


@pytest.mark.parametrize(
    "filename, expected_extension",
    [
        ("belge.png", "png"),
        ("belge.JPG", "jpg"),
        ("belge.jpeg", "jpeg"),
        ("belge.pdf", "pdf"),
        ("belge.docx", "docx"),
        ("belge.txt", "txt"),
        ("belge.csv", "csv"),
        ("belge.xlsx", "xlsx"),
    ],
)
def test_supported_file_extensions_are_accepted(
    filename: str,
    expected_extension: str,
) -> None:
    assert (
        validate_file_extension(filename)
        == expected_extension
    )


def test_unsupported_file_extension_is_rejected() -> None:
    with pytest.raises(HTTPException) as error_info:
        validate_file_extension("zararli.exe")

    assert error_info.value.status_code == 400
    assert "Desteklenmeyen" in str(error_info.value.detail)


def test_empty_file_is_rejected() -> None:
    upload = create_upload("bos.png", b"")

    with pytest.raises(HTTPException) as error_info:
        validate_file_size(upload)

    assert error_info.value.status_code == 400
    assert "Boş dosyalar" in str(error_info.value.detail)


@pytest.mark.parametrize(
    "filename, image_format",
    [
        ("gorsel.png", "PNG"),
        ("gorsel.jpg", "JPEG"),
        ("gorsel.jpeg", "JPEG"),
    ],
)
def test_valid_image_content_is_accepted(
    filename: str,
    image_format: str,
) -> None:
    file_type = filename.rsplit(".", maxsplit=1)[1]
    upload = create_upload(
        filename,
        create_image_bytes(image_format),
    )

    validate_file_content(
        file=upload,
        file_type=file_type,
    )

    assert upload.file.tell() == 0


def test_fake_image_content_is_rejected() -> None:
    upload = create_upload(
        "sahte.png",
        b"Bu dosya bir gorsel degildir.",
    )

    with pytest.raises(HTTPException) as error_info:
        validate_file_content(
            file=upload,
            file_type="png",
        )

    assert error_info.value.status_code == 400
    assert "Görsel dosyası okunamadı" in str(
        error_info.value.detail,
    )


def test_image_extension_and_content_must_match() -> None:
    upload = create_upload(
        "uyusmayan.jpg",
        create_image_bytes("PNG"),
    )

    with pytest.raises(HTTPException) as error_info:
        validate_file_content(
            file=upload,
            file_type="jpg",
        )

    assert error_info.value.status_code == 400
    assert "eşleşmiyor" in str(error_info.value.detail)


def test_image_pixel_limit_is_enforced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "ocr_max_pixels_per_page",
        100,
    )

    upload = create_upload(
        "buyuk.png",
        create_image_bytes(
            "PNG",
            size=(11, 10),
        ),
    )

    with pytest.raises(HTTPException) as error_info:
        validate_file_content(
            file=upload,
            file_type="png",
        )

    assert error_info.value.status_code == 400
    assert "piksel sınırını" in str(
        error_info.value.detail,
    )
