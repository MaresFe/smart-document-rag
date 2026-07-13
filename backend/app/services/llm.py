import httpx

from app.core.config import settings
from app.services.retrieval import RetrievedChunk


class LLMError(Exception):
    pass


def build_context_from_chunks(retrieved_chunks: list[RetrievedChunk]) -> str:
    context_parts: list[str] = []

    for index, chunk in enumerate(retrieved_chunks, start=1):
        context_parts.append(
            "\n".join(
                [
                    f"[Kaynak {index}]",
                    f"Dosya: {chunk.original_filename}",
                    f"Chunk index: {chunk.chunk_index}",
                    f"Benzerlik skoru: {chunk.similarity_score:.4f}",
                    "İçerik:",
                    chunk.content,
                ]
            )
        )

    return "\n\n---\n\n".join(context_parts)


def build_rag_prompt(
    question: str,
    retrieved_chunks: list[RetrievedChunk],
) -> str:
    context = build_context_from_chunks(retrieved_chunks)

    return f"""
Sen Türkçe cevap veren bir doküman soru-cevap asistanısın.

Kurallar:
- Sadece verilen kaynak metinlere dayanarak cevap ver.
- Kaynaklarda bilgi yoksa bunu açıkça söyle.
- Cevabı kısa, net ve anlaşılır yaz.
- Uydurma bilgi ekleme.
- Gerekirse hangi kaynağa dayandığını belirt.

Kullanıcının sorusu:
{question}

Kaynak metinler:
{context}

Cevap:
""".strip()


def generate_answer_with_ollama(
    question: str,
    retrieved_chunks: list[RetrievedChunk],
) -> str:
    if not retrieved_chunks:
        return (
            "Bu soruyla ilgili yeterli doküman parçası bulunamadı. "
            "Daha ilgili bir doküman yüklemeyi veya soruyu farklı sormayı deneyebilirsin."
        )

    prompt = build_rag_prompt(
        question=question,
        retrieved_chunks=retrieved_chunks,
    )

    url = f"{settings.ollama_base_url}/api/generate"

    try:
        response = httpx.post(
            url,
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                },
            },
            timeout=settings.llm_timeout_seconds,
        )

        response.raise_for_status()

        data = response.json()
        answer = data.get("response", "").strip()

        if not answer:
            raise LLMError("LLM returned an empty response.")

        return answer

    except Exception as error:
        raise LLMError(f"LLM response could not be generated: {error}") from error


def generate_answer(
    question: str,
    retrieved_chunks: list[RetrievedChunk],
) -> str:
    if settings.llm_provider == "ollama":
        return generate_answer_with_ollama(
            question=question,
            retrieved_chunks=retrieved_chunks,
        )

    raise LLMError(f"Unsupported LLM provider: {settings.llm_provider}")