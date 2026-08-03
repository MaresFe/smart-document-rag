import logging
from collections.abc import Iterator
from pathlib import Path
from time import perf_counter

import fitz
import pandas as pd
import pytesseract
from docx import Document as DocxDocument
from docx.document import Document as DocxDocumentType
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
from PIL import Image, ImageOps

from app.core.config import settings


TEXT_ENCODINGS = (
    "utf-8-sig",
    "utf-8",
    "cp1254",
    "latin-1",
)

performance_logger = logging.getLogger(
    "uvicorn.error",
)


class TextExtractionError(Exception):
    pass


def normalize_inline_text(value: object) -> str:
    if pd.isna(value):
        return ""

    return " ".join(str(value).split())


def validate_extracted_text(text: str) -> str:
    normalized_text = (
        text.replace("\x00", "").strip()
    )

    if not normalized_text:
        raise TextExtractionError(
            "Belgede çıkarılabilir metin bulunamadı.",
        )

    visible_characters = [
        character
        for character in normalized_text
        if not character.isspace()
    ]

    if visible_characters:
        printable_count = sum(
            character.isprintable()
            for character in visible_characters
        )

        printable_ratio = (
            printable_count
            / len(visible_characters)
        )

        if printable_ratio < 0.85:
            raise TextExtractionError(
                "Dosya geçerli bir metin belgesi "
                "gibi görünmüyor.",
            )

    return normalized_text


def has_meaningful_text(text: str) -> bool:
    visible_character_count = sum(
        not character.isspace()
        for character in text
    )

    return (
        visible_character_count
        >= settings.ocr_min_text_characters
    )


def extract_text_from_txt(path: Path) -> str:
    try:
        file_bytes = path.read_bytes()
    except OSError as error:
        raise TextExtractionError(
            "TXT dosyası okunamadı.",
        ) from error

    if not file_bytes:
        return ""

    if b"\x00" in file_bytes:
        raise TextExtractionError(
            "TXT dosyası metin biçiminde görünmüyor.",
        )

    for encoding in TEXT_ENCODINGS:
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise TextExtractionError(
        "TXT dosyasının karakter kodlaması "
        "desteklenmiyor.",
    )


def extract_text_from_pdf_page_with_ocr(
    page: fitz.Page,
    page_number: int,
) -> str:
    try:
        pixmap = page.get_pixmap(
            dpi=settings.ocr_dpi,
            colorspace=fitz.csRGB,
            alpha=False,
        )
    except Exception as error:
        raise TextExtractionError(
            f"PDF dosyasının {page_number}. sayfası "
            "OCR için görüntüye dönüştürülemedi.",
        ) from error

    pixel_count = pixmap.width * pixmap.height

    if pixel_count > settings.ocr_max_pixels_per_page:
        raise TextExtractionError(
            f"PDF dosyasının {page_number}. sayfası "
            "OCR görüntü boyutu sınırını aşıyor.",
        )

    try:
        with Image.frombytes(
            "RGB",
            (pixmap.width, pixmap.height),
            pixmap.samples,
        ) as page_image:
            grayscale_image = ImageOps.grayscale(
                page_image,
            )

            enhanced_image = ImageOps.autocontrast(
                grayscale_image,
            )

            try:
                extracted_text = (
                    pytesseract.image_to_string(
                        enhanced_image,
                        lang=settings.ocr_languages,
                        config="--oem 1 --psm 3",
                        timeout=(
                            settings
                            .ocr_page_timeout_seconds
                        ),
                    )
                )
            finally:
                grayscale_image.close()
                enhanced_image.close()

    except RuntimeError as error:
        raise TextExtractionError(
            f"PDF dosyasının {page_number}. sayfasında "
            "OCR işlemi zaman sınırını aştı.",
        ) from error

    except pytesseract.TesseractNotFoundError as error:
        raise TextExtractionError(
            "Sunucuda OCR motoru bulunamadı.",
        ) from error

    except pytesseract.TesseractError as error:
        raise TextExtractionError(
            f"PDF dosyasının {page_number}. sayfasında "
            "OCR işlemi tamamlanamadı.",
        ) from error

    except Exception as error:
        raise TextExtractionError(
            f"PDF dosyasının {page_number}. sayfası "
            "OCR ile işlenemedi.",
        ) from error

    return extracted_text.strip()


def extract_text_from_pdf(path: Path) -> str:
    text_parts: list[str] = []
    ocr_page_count = 0
    ocr_started = perf_counter()

    try:
        with fitz.open(path) as pdf_document:
            if pdf_document.page_count == 0:
                return ""

            for page_index, page in enumerate(
                pdf_document,
                start=1,
            ):
                native_page_text = (
                    page.get_text("text").strip()
                )

                if has_meaningful_text(
                    native_page_text,
                ):
                    text_parts.append(
                        f"[Sayfa {page_index}]\n"
                        f"{native_page_text}",
                    )
                    continue

                if not settings.ocr_enabled:
                    if native_page_text:
                        text_parts.append(
                            f"[Sayfa {page_index}]\n"
                            f"{native_page_text}",
                        )
                    continue

                ocr_page_count += 1

                if (
                    ocr_page_count
                    > settings.ocr_max_pages
                ):
                    raise TextExtractionError(
                        "PDF içindeki OCR gerektiren "
                        "sayfa sayısı "
                        f"{settings.ocr_max_pages} "
                        "sınırını aşıyor.",
                    )

                ocr_page_text = (
                    extract_text_from_pdf_page_with_ocr(
                        page=page,
                        page_number=page_index,
                    )
                )

                if has_meaningful_text(
                    ocr_page_text,
                ):
                    text_parts.append(
                        f"[Sayfa {page_index} - OCR]\n"
                        f"{ocr_page_text}",
                    )
                    continue

                if native_page_text:
                    text_parts.append(
                        f"[Sayfa {page_index}]\n"
                        f"{native_page_text}",
                    )

    except TextExtractionError:
        raise

    except Exception as error:
        raise TextExtractionError(
            "PDF dosyası okunamadı veya bozuk.",
        ) from error

    if ocr_page_count > 0:
        elapsed_ms = (
            perf_counter() - ocr_started
        ) * 1000

        performance_logger.info(
            "PDF OCR timing | "
            "file=%s | "
            "ocr_pages=%s | "
            "elapsed_ms=%.2f",
            path.name,
            ocr_page_count,
            elapsed_ms,
        )

    return "\n\n".join(text_parts)


def iter_docx_blocks(
    document: DocxDocumentType,
) -> Iterator[Paragraph | Table]:
    for child in (
        document.element.body.iterchildren()
    ):
        if isinstance(child, CT_P):
            yield Paragraph(child, document)

        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def docx_table_to_text(
    table: Table,
    table_index: int,
) -> str:
    row_parts: list[str] = []

    for row_index, row in enumerate(
        table.rows,
        start=1,
    ):
        cell_values = [
            normalize_inline_text(cell.text)
            for cell in row.cells
        ]

        if any(cell_values):
            row_parts.append(
                f"Satır {row_index}: "
                + " | ".join(cell_values),
            )

    if not row_parts:
        return ""

    return "\n".join(
        [
            f"[Tablo {table_index}]",
            *row_parts,
        ],
    )


def extract_text_from_docx(path: Path) -> str:
    text_parts: list[str] = []
    table_index = 0

    try:
        document = DocxDocument(path)

        for block in iter_docx_blocks(
            document,
        ):
            if isinstance(block, Paragraph):
                paragraph_text = (
                    block.text.strip()
                )

                if paragraph_text:
                    text_parts.append(
                        paragraph_text,
                    )

                continue

            table_index += 1

            table_text = docx_table_to_text(
                block,
                table_index,
            )

            if table_text:
                text_parts.append(
                    table_text,
                )

    except Exception as error:
        raise TextExtractionError(
            "DOCX dosyası okunamadı veya bozuk.",
        ) from error

    return "\n\n".join(text_parts)


def read_csv_dataframe(
    path: Path,
) -> pd.DataFrame:
    for encoding in TEXT_ENCODINGS:
        try:
            return pd.read_csv(
                path,
                sep=None,
                engine="python",
                encoding=encoding,
                dtype=str,
                keep_default_na=False,
            )
        except Exception:
            continue

    raise TextExtractionError(
        "CSV dosyası okunamadı; dosya bozuk "
        "veya kodlaması desteklenmiyor.",
    )


def extract_text_from_csv(path: Path) -> str:
    dataframe = read_csv_dataframe(path)

    return dataframe_to_text(dataframe)


def extract_text_from_xlsx(path: Path) -> str:
    try:
        sheets = pd.read_excel(
            path,
            sheet_name=None,
            dtype=str,
            keep_default_na=False,
            engine="openpyxl",
        )

    except Exception as error:
        raise TextExtractionError(
            "XLSX dosyası okunamadı veya bozuk.",
        ) from error

    text_parts: list[str] = []

    for sheet_name, dataframe in sheets.items():
        sheet_text = dataframe_to_text(
            dataframe,
        )

        if sheet_text:
            text_parts.append(
                f"[Çalışma Sayfası: "
                f"{sheet_name}]\n"
                f"{sheet_text}",
            )

    return "\n\n".join(text_parts)


def dataframe_to_text(
    dataframe: pd.DataFrame,
) -> str:
    column_names = [
        normalize_inline_text(column_name)
        or f"Sütun {column_index}"
        for column_index, column_name
        in enumerate(
            dataframe.columns,
            start=1,
        )
    ]

    if not column_names:
        return ""

    text_rows = [
        "Sütunlar: "
        + " | ".join(column_names),
    ]

    for row_number, (_, row) in enumerate(
        dataframe.iterrows(),
        start=2,
    ):
        row_values: list[str] = []

        for column_name, value in zip(
            column_names,
            row.tolist(),
            strict=True,
        ):
            normalized_value = (
                normalize_inline_text(value)
            )

            if normalized_value:
                row_values.append(
                    f"{column_name}: "
                    f"{normalized_value}",
                )

        if row_values:
            text_rows.append(
                f"Satır {row_number}: "
                + " | ".join(row_values),
            )

    return "\n".join(text_rows)


def extract_text_from_document(
    file_type: str,
    storage_path: str,
) -> str:
    path = Path(storage_path)

    if not path.is_file():
        raise TextExtractionError(
            "Yüklenen dosya bulunamadı.",
        )

    match file_type:
        case "txt":
            extracted_text = (
                extract_text_from_txt(path)
            )

        case "pdf":
            extracted_text = (
                extract_text_from_pdf(path)
            )

        case "docx":
            extracted_text = (
                extract_text_from_docx(path)
            )

        case "csv":
            extracted_text = (
                extract_text_from_csv(path)
            )

        case "xlsx":
            extracted_text = (
                extract_text_from_xlsx(path)
            )

        case _:
            raise TextExtractionError(
                "Bu dosya türü için metin "
                "çıkarma desteklenmiyor.",
            )

    return validate_extracted_text(
        extracted_text,
    )
