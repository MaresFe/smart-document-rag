from datetime import timedelta
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routes import auth as auth_routes
from app.core.config import settings
from app.models.account_token import AccountToken
from app.models.user import User
from app.services.account_tokens import (
    hash_account_token,
    utc_now,
)


PASSWORD = "TestPassword123!"


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
            "password": PASSWORD,
            "full_name": "Invitation Test User",
        },
    )

    assert response.status_code == 201
    return response.json()


def promote_user(
    db: Session,
    user_id: str,
) -> User:
    user = db.get(User, UUID(user_id))
    assert user is not None

    user.is_admin = True
    db.commit()
    db.refresh(user)
    return user


@pytest.mark.database
def test_invite_only_mode_blocks_public_registration_and_non_admins(
    api_client_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = api_client_factory()
    register_user(client, unique_email("non-admin"))

    monkeypatch.setattr(
        settings,
        "registration_mode",
        "invite_only",
    )

    public_registration = client.post(
        "/api/auth/register",
        json={
            "email": unique_email("public"),
            "password": PASSWORD,
            "full_name": "Public User",
        },
    )
    invitation_attempt = client.post(
        "/api/auth/invitations",
        json={"email": unique_email("invitee")},
    )

    assert public_registration.status_code == 403
    assert invitation_attempt.status_code == 403


@pytest.mark.database
def test_admin_invitation_is_hashed_single_use_and_creates_user(
    api_client_factory,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_client = api_client_factory()
    invitee_client = api_client_factory()

    admin = register_user(
        admin_client,
        unique_email("admin"),
    )
    promote_user(db_session, str(admin["id"]))

    monkeypatch.setattr(
        settings,
        "registration_mode",
        "invite_only",
    )
    monkeypatch.setattr(
        settings,
        "email_delivery_mode",
        "console",
    )

    delivered_messages: list[tuple[str, str]] = []
    monkeypatch.setattr(
        auth_routes,
        "send_invitation_email",
        lambda recipient, invitation_url: delivered_messages.append(
            (recipient, invitation_url),
        ),
    )

    invitee_email = unique_email("invited")
    invitation_response = admin_client.post(
        "/api/auth/invitations",
        json={"email": invitee_email.upper()},
    )

    assert invitation_response.status_code == 201
    invitation_body = invitation_response.json()
    invitation_url = invitation_body["invitation_url"]
    assert invitation_url is not None
    assert invitation_body["email"] == invitee_email
    assert delivered_messages == [
        (invitee_email, invitation_url)
    ]

    raw_token = parse_qs(
        urlparse(invitation_url).query,
    )["token"][0]

    stored_invitation = db_session.scalar(
        select(AccountToken).where(
            AccountToken.id
            == UUID(invitation_body["id"]),
        )
    )
    assert stored_invitation is not None
    assert stored_invitation.token_hash != raw_token
    assert stored_invitation.token_hash == hash_account_token(
        raw_token
    )

    preview_response = invitee_client.post(
        "/api/auth/invitations/preview",
        json={"token": raw_token},
    )
    assert preview_response.status_code == 200
    assert preview_response.json()["email"] == invitee_email

    accept_response = invitee_client.post(
        "/api/auth/invitations/accept",
        json={
            "token": raw_token,
            "password": PASSWORD,
            "full_name": "Invited User",
        },
    )

    assert accept_response.status_code == 201
    accepted_user = accept_response.json()
    assert accepted_user["email"] == invitee_email
    assert accepted_user["is_admin"] is False
    assert accepted_user["email_verified_at"] is not None
    assert settings.auth_cookie_name in invitee_client.cookies

    db_session.refresh(stored_invitation)
    assert stored_invitation.used_at is not None

    second_use_response = api_client_factory().post(
        "/api/auth/invitations/accept",
        json={
            "token": raw_token,
            "password": PASSWORD,
            "full_name": "Second User",
        },
    )
    assert second_use_response.status_code == 400
    assert api_client_factory().post(
        "/api/auth/invitations/preview",
        json={"token": raw_token},
    ).status_code == 400

    invitee_client.post("/api/auth/logout")
    login_response = invitee_client.post(
        "/api/auth/login",
        json={
            "email": invitee_email,
            "password": PASSWORD,
        },
    )
    assert login_response.status_code == 200


@pytest.mark.database
def test_expired_invitation_is_rejected(
    api_client_factory,
    db_session: Session,
) -> None:
    raw_token = "expired-token-" + ("x" * 32)
    expired_email = unique_email("expired")

    expired_invitation = AccountToken(
        email=expired_email,
        token_hash=hash_account_token(raw_token),
        purpose="invitation",
        expires_at=utc_now() - timedelta(minutes=1),
    )
    db_session.add(expired_invitation)
    db_session.commit()

    response = api_client_factory().post(
        "/api/auth/invitations/accept",
        json={
            "token": raw_token,
            "password": PASSWORD,
            "full_name": "Expired User",
        },
    )

    assert response.status_code == 400
    assert db_session.scalar(
        select(User).where(
            func.lower(User.email) == expired_email,
        )
    ) is None
