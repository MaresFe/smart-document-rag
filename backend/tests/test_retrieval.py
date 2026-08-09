from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.services import retrieval


class FakeRowsResult:
    def __init__(self, rows: list[tuple[object, str | None, float]]) -> None:
        self.rows = rows

    def all(self) -> list[tuple[object, str | None, float]]:
        return self.rows


class FakeSession:
    def __init__(self, rows: list[tuple[object, str | None, float]]) -> None:
        self.rows = rows
        self.executed_statement: object | None = None

    def execute(self, statement: object) -> FakeRowsResult:
        self.executed_statement = statement
        return FakeRowsResult(self.rows)


def make_chunk(
    *,
    document_id: UUID | None = None,
    chunk_id: UUID | None = None,
    chunk_index: int = 0,
    content: str = "Belge içeriği",
) -> SimpleNamespace:
    return SimpleNamespace(
        document_id=document_id or uuid4(),
        id=chunk_id or uuid4(),
        chunk_index=chunk_index,
        content=content,
    )


def test_count_meaningful_query_characters_ignores_symbols() -> None:
    assert (
        retrieval.count_meaningful_query_characters(
            " ? A-1! ",
        )
        == 2
    )


def test_is_meaningful_query_uses_configured_minimum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        retrieval.settings,
        "retrieval_min_query_characters",
        3,
    )

    assert not retrieval.is_meaningful_query("a!")
    assert retrieval.is_meaningful_query("a-1-b")


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        (-4.0, -1.0),
        (0.75, 0.75),
        (4.0, 1.0),
    ],
)
def test_similarity_threshold_is_clamped(
    monkeypatch: pytest.MonkeyPatch,
    configured: float,
    expected: float,
) -> None:
    monkeypatch.setattr(
        retrieval.settings,
        "retrieval_min_similarity_score",
        configured,
    )

    assert (
        retrieval.get_safe_similarity_threshold()
        == expected
    )


def test_short_query_skips_embedding_and_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        retrieval.settings,
        "retrieval_min_query_characters",
        2,
    )

    def fail_embedding(query: str) -> list[float]:
        raise AssertionError(query)

    monkeypatch.setattr(
        retrieval,
        "create_query_embedding",
        fail_embedding,
    )

    result = retrieval.retrieve_relevant_chunks(
        db=FakeSession([]),
        query="m",
        user_id=uuid4(),
    )

    assert result == []


def test_empty_document_filter_skips_embedding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        retrieval.settings,
        "retrieval_min_query_characters",
        2,
    )

    def fail_embedding(query: str) -> list[float]:
        raise AssertionError(query)

    monkeypatch.setattr(
        retrieval,
        "create_query_embedding",
        fail_embedding,
    )

    result = retrieval.retrieve_relevant_chunks(
        db=FakeSession([]),
        query="geçerli soru",
        user_id=uuid4(),
        document_ids=[],
    )

    assert result == []


def test_retrieval_filters_low_similarity_and_maps_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    accepted_chunk = make_chunk(
        chunk_index=2,
        content="Kabul edilen içerik",
    )
    rejected_chunk = make_chunk(
        chunk_index=3,
        content="Reddedilen içerik",
    )
    session = FakeSession(
        [
            (accepted_chunk, "accepted.txt", 0.1),
            (rejected_chunk, "rejected.txt", 0.4),
        ],
    )

    monkeypatch.setattr(
        retrieval.settings,
        "retrieval_min_query_characters",
        2,
    )
    monkeypatch.setattr(
        retrieval.settings,
        "retrieval_min_similarity_score",
        0.75,
    )
    monkeypatch.setattr(
        retrieval,
        "create_query_embedding",
        lambda query: [0.1, 0.2],
    )

    results = retrieval.retrieve_relevant_chunks(
        db=session,
        query="  proje bilgisi  ",
        user_id=user_id,
        limit=100,
        document_ids=[accepted_chunk.document_id],
    )

    assert len(results) == 1
    assert results[0] == retrieval.RetrievedChunk(
        document_id=accepted_chunk.document_id,
        chunk_id=accepted_chunk.id,
        chunk_index=2,
        content="Kabul edilen içerik",
        similarity_score=pytest.approx(0.9),
        original_filename="accepted.txt",
    )
    assert session.executed_statement is not None
    assert session.executed_statement._limit_clause.value == 20


@pytest.mark.parametrize(
    ("requested_limit", "expected_limit"),
    [
        (0, 1),
        (1, 1),
        (20, 20),
        (100, 20),
    ],
)
def test_retrieval_clamps_result_limit(
    monkeypatch: pytest.MonkeyPatch,
    requested_limit: int,
    expected_limit: int,
) -> None:
    session = FakeSession([])

    monkeypatch.setattr(
        retrieval.settings,
        "retrieval_min_query_characters",
        1,
    )
    monkeypatch.setattr(
        retrieval,
        "create_query_embedding",
        lambda query: [0.1],
    )

    assert (
        retrieval.retrieve_relevant_chunks(
            db=session,
            query="soru",
            user_id=uuid4(),
            limit=requested_limit,
        )
        == []
    )
    assert session.executed_statement is not None
    assert (
        session.executed_statement._limit_clause.value
        == expected_limit
    )
