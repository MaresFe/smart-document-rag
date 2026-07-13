from pathlib import Path


class TextExtractionError(Exception):
    pass


def extract_text_from_document(file_type: str, storage_path: str) -> str:
    path = Path(storage_path)

    if not path.exists():
        raise TextExtractionError("File does not exist.")

    if file_type == "txt":
        return path.read_text(encoding="utf-8", errors="replace")

    raise TextExtractionError(
        f"Text extraction is not implemented for file type: {file_type}"
    )