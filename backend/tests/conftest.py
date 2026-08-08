import os
import sys
from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ENV_FILE = BACKEND_ROOT.parent / ".env"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


test_database_url = os.getenv("TEST_DATABASE_URL")

if test_database_url:
    os.environ["DATABASE_URL"] = test_database_url

elif not PROJECT_ENV_FILE.exists():
    # Yalnızca saf birim testlerinin .env olmadan toplanabilmesi için
    # sahte değerler tanımlanır. Veritabanı testleri bağlantı kurulamazsa
    # otomatik olarak atlanır.
    os.environ.setdefault("POSTGRES_USER", "test_user")
    os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
    os.environ.setdefault("POSTGRES_DB", "test_database")
    os.environ.setdefault(
        "DATABASE_URL",
        (
            "postgresql+psycopg://test_user:"
            "test_password@localhost:5432/test_database"
        ),
    )
    os.environ.setdefault(
        "AUTH_SECRET_KEY",
        "test-only-secret-key-that-is-not-used-in-production",
    )


from app.db.session import engine, get_db  # noqa: E402
from app.main import app  # noqa: E402


ApiClientFactory = Callable[[], TestClient]


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    try:
        connection = engine.connect()
    except SQLAlchemyError:
        pytest.skip(
            "PostgreSQL test bağlantısı kurulamadı.",
        )

    outer_transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()

        if outer_transaction.is_active:
            outer_transaction.rollback()

        connection.close()


@pytest.fixture
def api_client_factory(
    db_session: Session,
) -> Generator[ApiClientFactory, None, None]:
    clients: list[TestClient] = []

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def create_client() -> TestClient:
        client = TestClient(app)
        clients.append(client)
        return client

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield create_client
    finally:
        for client in clients:
            client.close()

        app.dependency_overrides.pop(get_db, None)
