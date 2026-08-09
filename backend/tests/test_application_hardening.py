from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app import main as main_module
from app.core.config import Settings, settings
from app.services.rate_limiting import (
    reset_auth_rate_limits,
)


PASSWORD = "TestPassword123!"


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


def register_user(
    client: TestClient,
    email: str,
) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Security Test User",
        },
    )

    assert response.status_code == 201


@pytest.fixture(autouse=True)
def clear_rate_limits() -> None:
    reset_auth_rate_limits()
    yield
    reset_auth_rate_limits()


@pytest.mark.database
def test_security_headers_and_trusted_hosts(
    api_client_factory,
) -> None:
    client = api_client_factory()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == (
        "nosniff"
    )
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == (
        "no-referrer"
    )
    assert response.headers["permissions-policy"] == (
        "camera=(), microphone=(), geolocation=()"
    )
    assert response.headers[
        "cross-origin-opener-policy"
    ] == "same-origin"

    untrusted_host = client.get(
        "/health",
        headers={"Host": "attacker.example"},
    )

    assert untrusted_host.status_code == 400
    assert untrusted_host.headers[
        "x-content-type-options"
    ] == "nosniff"

    auth_response = client.post(
        "/api/auth/login",
        json={
            "email": unique_email("missing"),
            "password": PASSWORD,
        },
    )

    assert auth_response.status_code == 401
    assert auth_response.headers["cache-control"] == (
        "no-store"
    )


@pytest.mark.database
def test_cross_site_authenticated_mutation_is_rejected(
    api_client_factory,
) -> None:
    client = api_client_factory()
    email = unique_email("origin-check")
    register_user(client, email)

    rejected_response = client.post(
        "/api/auth/logout",
        headers={
            "Origin": "https://attacker.example",
        },
    )

    assert rejected_response.status_code == 403
    assert rejected_response.json() == {
        "detail": "Request origin is not allowed.",
    }
    assert client.get("/api/auth/me").status_code == 200

    trusted_response = client.post(
        "/api/auth/logout",
        headers={
            "Origin": settings.cors_allowed_origins[0],
        },
    )

    assert trusted_response.status_code == 204
    assert client.get("/api/auth/me").status_code == 401


@pytest.mark.database
def test_login_attempts_are_rate_limited(
    api_client_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = api_client_factory()
    email = unique_email("login-limit")
    register_user(client, email)
    client.post("/api/auth/logout")

    monkeypatch.setattr(
        settings,
        "auth_login_max_attempts",
        3,
    )
    monkeypatch.setattr(
        settings,
        "auth_login_window_seconds",
        60,
    )

    for _ in range(3):
        response = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401

    blocked_response = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
    )

    assert blocked_response.status_code == 429
    assert int(blocked_response.headers["retry-after"]) >= 1

    reset_auth_rate_limits()

    successful_response = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
    )

    assert successful_response.status_code == 200


@pytest.mark.database
def test_password_reset_requests_are_rate_limited(
    api_client_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = api_client_factory()
    email = unique_email("reset-limit")

    monkeypatch.setattr(
        settings,
        "auth_password_reset_max_attempts",
        2,
    )
    monkeypatch.setattr(
        settings,
        "auth_password_reset_window_seconds",
        60,
    )

    for _ in range(2):
        response = client.post(
            "/api/auth/password-reset/request",
            json={"email": email},
        )
        assert response.status_code == 202

    blocked_response = client.post(
        "/api/auth/password-reset/request",
        json={"email": email},
    )

    assert blocked_response.status_code == 429
    assert blocked_response.json()["detail"] == (
        "Too many requests. Please try again later."
    )


@pytest.mark.database
def test_database_health_error_does_not_leak_details(
    api_client_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = api_client_factory()

    def fail_connection_check() -> None:
        raise SQLAlchemyError(
            "postgresql://database-user:secret@internal-host/db"
        )

    monkeypatch.setattr(
        main_module,
        "check_database_connection",
        fail_connection_check,
    )

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {"database": "error"}
    assert "secret" not in response.text
    assert "internal-host" not in response.text


def test_production_configuration_fails_closed() -> None:
    base_values = {
        "postgres_user": "test",
        "postgres_password": "test",
        "postgres_db": "test",
        "database_url": (
            "postgresql+psycopg://test:test@localhost/test"
        ),
        "auth_secret_key": "x" * 32,
        "app_environment": "production",
        "email_delivery_mode": "smtp",
        "security_hsts_enabled": True,
    }

    with pytest.raises(
        ValidationError,
        match="AUTH_COOKIE_SECURE",
    ):
        Settings(
            _env_file=None,
            **base_values,
            auth_cookie_secure=False,
        )

    production_settings = Settings(
        _env_file=None,
        **base_values,
        auth_cookie_secure=True,
    )

    assert production_settings.auth_cookie_secure is True
    assert production_settings.security_hsts_enabled is True
