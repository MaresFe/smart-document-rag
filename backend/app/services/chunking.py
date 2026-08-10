def split_long_text(text: str, max_chars: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + max_chars
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start = end - overlap

        if start < 0:
            start = 0

        if start >= len(text):
            break

    return chunks


def chunk_text(
    text: str,
    max_chars: int = 1200,
    overlap: int = 150,
) -> list[str]:
    cleaned_text = text.strip()

    if not cleaned_text:
        return []

    paragraphs = [
        paragraph.strip()
        for paragraph in cleaned_text.replace("\r\n", "\n").split("\n\n")
        if paragraph.strip()
    ]

    chunks: list[str] = []
    current_chunk = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
                current_chunk = ""

            chunks.extend(
                split_long_text(
                    text=paragraph,
                    max_chars=max_chars,
                    overlap=overlap,
                )
            )
            continue

        candidate = f"{current_chunk}\n\n{paragraph}".strip()

        if len(candidate) <= max_chars:
            current_chunk = candidate
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = paragraph

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks