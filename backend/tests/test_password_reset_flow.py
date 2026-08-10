from datetime import timedelta
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes import auth as auth_routes
from app.models.account_token import AccountToken
from app.services.account_tokens import (
    hash_account_token,
    utc_now,
)


OLD_PASSWORD = "OldPassword123!"
NEW_PASSWORD = "NewPassword456!"


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


def register_user(
    client: TestClient,
    email: str,
) -> dict[str, object]:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": OLD_PASSWORD,
            "full_name": "Password Reset User",
        },
    )

    assert response.status_code == 201
    return response.json()


@pytest.mark.database
def test_password_reset_is_generic_hashed_and_single_use(
    api_client_factory,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = api_client_factory()
    email = unique_email("password-reset")
    user = register_user(client, email)
    client.post("/api/auth/logout")

    delivered_messages: list[tuple[str, str]] = []
    monkeypatch.setattr(
        auth_routes,
        "send_password_reset_email",
        lambda recipient, password_reset_url: (
            delivered_messages.append(
                (recipient, password_reset_url),
            )
        ),
    )

    unknown_response = client.post(
        "/api/auth/password-reset/request",
        json={"email": unique_email("unknown")},
    )
    request_response = client.post(
        "/api/auth/password-reset/request",
        json={"email": email.upper()},
    )

    assert unknown_response.status_code == 202
    assert request_response.status_code == 202
    assert unknown_response.json() == request_response.json()
    assert len(delivered_messages) == 1
    assert delivered_messages[0][0] == email

    password_reset_url = delivered_messages[0][1]
    raw_token = parse_qs(
        urlparse(password_reset_url).query,
    )["token"][0]

    stored_token = db_session.scalar(
        select(AccountToken).where(
            AccountToken.user_id == UUID(str(user["id"])),
            AccountToken.purpose == "password_reset",
        )
    )
    assert stored_token is not None
    assert stored_token.token_hash != raw_token
    assert stored_token.token_hash == hash_account_token(
        raw_token,
    )

    preview_response = client.post(
        "/api/auth/password-reset/preview",
        json={"token": raw_token},
    )
    assert preview_response.status_code == 200
    assert "expires_at" in preview_response.json()
    assert "email" not in preview_response.json()

    confirm_response = client.post(
        "/api/auth/password-reset/confirm",
        json={
            "token": raw_token,
            "password": NEW_PASSWORD,
        },
    )
    assert confirm_response.status_code == 204

    db_session.refresh(stored_token)
    assert stored_token.used_at is not None

    assert client.post(
        "/api/auth/password-reset/confirm",
        json={
            "token": raw_token,
            "password": "AnotherPassword789!",
        },
    ).status_code == 400

    assert client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": OLD_PASSWORD,
        },
    ).status_code == 401

    assert client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": NEW_PASSWORD,
        },
    ).status_code == 200


@pytest.mark.database
def test_new_password_reset_invalidates_previous_link(
    api_client_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = api_client_factory()
    email = unique_email("replacement-reset")
    register_user(client, email)
    client.post("/api/auth/logout")

    delivered_urls: list[str] = []
    monkeypatch.setattr(
        auth_routes,
        "send_password_reset_email",
        lambda recipient, password_reset_url: (
            delivered_urls.append(password_reset_url)
        ),
    )

    for _ in range(2):
        response = client.post(
            "/api/auth/password-reset/request",
            json={"email": email},
        )
        assert response.status_code == 202

    first_token = parse_qs(
        urlparse(delivered_urls[0]).query,
    )["token"][0]
    second_token = parse_qs(
        urlparse(delivered_urls[1]).query,
    )["token"][0]

    assert client.post(
        "/api/auth/password-reset/preview",
        json={"token": first_token},
    ).status_code == 400
    assert client.post(
        "/api/auth/password-reset/preview",
        json={"token": second_token},
    ).status_code == 200


@pytest.mark.database
def test_expired_password_reset_is_rejected(
    api_client_factory,
    db_session: Session,
) -> None:
    client = api_client_factory()
    email = unique_email("expired-reset")
    user = register_user(client, email)
    client.post("/api/auth/logout")

    raw_token = "expired-password-reset-" + ("x" * 32)
    expired_token = AccountToken(
        user_id=UUID(str(user["id"])),
        token_hash=hash_account_token(raw_token),
        purpose="password_reset",
        expires_at=utc_now() - timedelta(minutes=1),
    )
    db_session.add(expired_token)
    db_session.commit()

    assert client.post(
        "/api/auth/password-reset/preview",
        json={"token": raw_token},
    ).status_code == 400
    assert client.post(
        "/api/auth/password-reset/confirm",
        json={
            "token": raw_token,
            "password": NEW_PASSWORD,
        },
    ).status_code == 400
