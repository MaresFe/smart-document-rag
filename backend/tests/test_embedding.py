from __future__ import annotations

from typing import Any

import pytest

from app.services import embedding


class FakeEncodedValue:
    def __init__(self, value: object) -> None:
        self.value = value

    def tolist(self) -> object:
        return self.value


class FakeEmbeddingModel:
    def __init__(self, encoded_value: object) -> None:
        self.encoded_value = encoded_value
        self.calls: list[tuple[object, dict[str, Any]]] = []

    def encode(
        self,
        value: object,
        **kwargs: Any,
    ) -> FakeEncodedValue:
        self.calls.append((value, kwargs))
        return FakeEncodedValue(self.encoded_value)


def test_create_passage_embeddings_returns_empty_without_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called() -> None:
        raise AssertionError("Model çağrılmamalıydı.")

    monkeypatch.setattr(
        embedding,
        "get_embedding_model",
        fail_if_called,
    )

    assert embedding.create_passage_embeddings([]) == []


def test_create_passage_embeddings_prefixes_and_normalizes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = FakeEmbeddingModel(
        [[0.1, 0.2], [0.3, 0.4]],
    )

    monkeypatch.setattr(
        embedding,
        "get_embedding_model",
        lambda: model,
    )

    result = embedding.create_passage_embeddings(
        ["birinci", "ikinci"],
    )

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    assert model.calls == [
        (
            ["passage: birinci", "passage: ikinci"],
            {
                "normalize_embeddings": True,
                "show_progress_bar": False,
            },
        ),
    ]


def test_create_query_embedding_rejects_blank_query() -> None:
    with pytest.raises(
        embedding.EmbeddingError,
        match="Query cannot be empty",
    ):
        embedding.create_query_embedding("  \n ")


def test_create_query_embedding_uses_query_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = FakeEmbeddingModel([0.4, 0.6])

    monkeypatch.setattr(
        embedding,
        "get_embedding_model",
        lambda: model,
    )

    result = embedding.create_query_embedding(
        "proje tarihi",
    )

    assert result == [0.4, 0.6]
    assert model.calls == [
        (
            "query: proje tarihi",
            {
                "normalize_embeddings": True,
                "show_progress_bar": False,
            },
        ),
    ]


@pytest.mark.parametrize(
    ("function_name", "argument", "message"),
    [
        (
            "create_passage_embeddings",
            ["metin"],
            "Embeddings could not be created",
        ),
        (
            "create_query_embedding",
            "soru",
            "Query embedding could not be created",
        ),
    ],
)
def test_embedding_failures_are_wrapped(
    monkeypatch: pytest.MonkeyPatch,
    function_name: str,
    argument: object,
    message: str,
) -> None:
    original_error = RuntimeError("model unavailable")

    def raise_error() -> None:
        raise original_error

    monkeypatch.setattr(
        embedding,
        "get_embedding_model",
        raise_error,
    )

    function = getattr(embedding, function_name)

    with pytest.raises(
        embedding.EmbeddingError,
        match=message,
    ) as captured:
        function(argument)

    assert captured.value.__cause__ is original_error


def test_get_embedding_model_is_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_models: list[object] = []

    def create_model(model_name: str) -> object:
        model = object()
        created_models.append((model_name, model))
        return model

    embedding.get_embedding_model.cache_clear()
    monkeypatch.setattr(
        embedding,
        "SentenceTransformer",
        create_model,
    )

    try:
        first = embedding.get_embedding_model()
        second = embedding.get_embedding_model()

        assert first is second
        assert len(created_models) == 1
        assert created_models[0][0] == (
            embedding.settings.embedding_model_name
        )
    finally:
        embedding.get_embedding_model.cache_clear()
