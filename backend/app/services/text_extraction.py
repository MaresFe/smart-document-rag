from pathlib import Path

import fitz
import pandas as pd
from docx import Document as DocxDocument


class TextExtractionError(Exception):
    pass


def extract_text_from_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_text_from_pdf(path: Path) -> str:
    text_parts: list[str] = []

    try:
        with fitz.open(path) as pdf_document:
            for page_index, page in enumerate(pdf_document, start=1):
                page_text = page.get_text("text").strip()

                if page_text:
                    text_parts.append(
                        f"[Sayfa {page_index}]\n{page_text}"
                    )

    except Exception as error:
        raise TextExtractionError(f"PDF could not be read: {error}") from error

    return "\n\n".join(text_parts)


def extract_text_from_docx(path: Path) -> str:
    text_parts: list[str] = []

    try:
        document = DocxDocument(path)

        for paragraph in document.paragraphs:
            paragraph_text = paragraph.text.strip()

            if paragraph_text:
                text_parts.append(paragraph_text)

    except Exception as error:
        raise TextExtractionError(f"DOCX could not be read: {error}") from error

    return "\n\n".join(text_parts)


def extract_text_from_csv(path: Path) -> str:
    try:
        dataframe = pd.read_csv(path)
    except Exception as error:
        raise TextExtractionError(f"CSV could not be read: {error}") from error

    return dataframe_to_text(dataframe)


def extract_text_from_xlsx(path: Path) -> str:
    try:
        sheets = pd.read_excel(path, sheet_name=None)
    except Exception as error:
        raise TextExtractionError(f"XLSX could not be read: {error}") from error

    text_parts: list[str] = []

    for sheet_name, dataframe in sheets.items():
        sheet_text = dataframe_to_text(dataframe)
        if sheet_text:
            text_parts.append(f"[Sheet: {sheet_name}]\n{sheet_text}")

    return "\n\n".join(text_parts)


def dataframe_to_text(dataframe: pd.DataFrame) -> str:
    if dataframe.empty:
        return ""

    text_rows: list[str] = []

    for index, row in dataframe.iterrows():
        row_parts: list[str] = []

        for column_name, value in row.items():
            if pd.isna(value):
                continue

            row_parts.append(f"{column_name}: {value}")

        if row_parts:
            text_rows.append(
                f"Satır {index + 1}: " + ", ".join(row_parts)
            )

    return "\n".join(text_rows)


def extract_text_from_document(file_type: str, storage_path: str) -> str:
    path = Path(storage_path)

    if not path.exists():
        raise TextExtractionError("File does not exist.")

    match file_type:
        case "txt":
            extracted_text = extract_text_from_txt(path)
        case "pdf":
            extracted_text = extract_text_from_pdf(path)
        case "docx":
            extracted_text = extract_text_from_docx(path)
        case "csv":
            extracted_text = extract_text_from_csv(path)
        case "xlsx":
            extracted_text = extract_text_from_xlsx(path)
        case _:
            raise TextExtractionError(
                f"Text extraction is not supported for file type: {file_type}"
            )

    extracted_text = extracted_text.strip()

    if not extracted_text:
        raise TextExtractionError("No extractable text found in document.")

    return extracted_text