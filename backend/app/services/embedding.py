from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import settings


class EmbeddingError(Exception):
    pass


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model_name)


def create_passage_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    try:
        model = get_embedding_model()

        prefixed_texts = [
            f"passage: {text}"
            for text in texts
        ]

        embeddings = model.encode(
            prefixed_texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return embeddings.tolist()

    except Exception as error:
        raise EmbeddingError(f"Embeddings could not be created: {error}") from error


def create_query_embedding(query: str) -> list[float]:
    if not query.strip():
        raise EmbeddingError("Query cannot be empty.")

    try:
        model = get_embedding_model()

        embedding = model.encode(
            f"query: {query}",
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return embedding.tolist()

    except Exception as error:
        raise EmbeddingError(f"Query embedding could not be created: {error}") from error