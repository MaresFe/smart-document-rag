from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes import chat as chat_routes
from app.api.routes import documents as document_routes
from app.core.config import settings


PASSWORD = "TestPassword123!"


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


def register_user(
    client: TestClient,
    email: str,
    full_name: str,
) -> dict[str, object]:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": full_name,
        },
    )

    assert response.status_code == 201
    return response.json()


def upload_text_document(
    client: TestClient,
    filename: str = "private-document.txt",
) -> dict[str, object]:
    response = client.post(
        "/api/documents",
        files={
            "file": (
                filename,
                (
                    "Bu belge yalnızca belge sahibine aittir. "
                    "Belgenin kodu GUVENLI-42'dir."
                ).encode("utf-8"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 201
    return response.json()


@pytest.mark.database
def test_protected_endpoints_require_authentication(
    api_client_factory,
) -> None:
    client = api_client_factory()

    protected_requests = [
        client.get("/api/auth/me"),
        client.get("/api/documents"),
        client.get("/api/chat/sessions"),
    ]

    assert all(
        response.status_code == 401
        for response in protected_requests
    )


@pytest.mark.database
def test_register_login_logout_and_cookie_security(
    api_client_factory,
) -> None:
    client = api_client_factory()
    email = unique_email("auth-flow")

    register_response = client.post(
        "/api/auth/register",
        json={
            "email": email.upper(),
            "password": PASSWORD,
            "full_name": "Auth Test User",
        },
    )

    assert register_response.status_code == 201

    response_body = register_response.json()
    assert response_body["email"] == email
    assert "password" not in response_body
    assert "password_hash" not in response_body

    set_cookie_header = register_response.headers[
        "set-cookie"
    ].casefold()

    assert "httponly" in set_cookie_header
    assert "samesite=lax" in set_cookie_header
    assert settings.auth_cookie_name in client.cookies

    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email

    duplicate_response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Duplicate User",
        },
    )

    assert duplicate_response.status_code == 409

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 204
    assert client.get("/api/auth/me").status_code == 401

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
    )

    assert login_response.status_code == 200
    assert client.get("/api/auth/me").status_code == 200


@pytest.mark.database
def test_documents_are_isolated_between_users(
    api_client_factory,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client_a = api_client_factory()
    client_b = api_client_factory()

    register_user(
        client_a,
        unique_email("document-owner"),
        "Document Owner",
    )
    register_user(
        client_b,
        unique_email("document-outsider"),
        "Document Outsider",
    )

    monkeypatch.setattr(
        settings,
        "upload_dir",
        tmp_path / "uploads",
    )
    monkeypatch.setattr(
        document_routes,
        "create_passage_embeddings",
        lambda chunks: [
            [0.0] * settings.embedding_dimension
            for _ in chunks
        ],
    )

    document = upload_text_document(client_a)
    document_id = document["id"]

    assert "user_id" not in document
    assert "stored_filename" not in document
    assert "storage_path" not in document

    owner_list = client_a.get("/api/documents")
    outsider_list = client_b.get("/api/documents")

    assert owner_list.status_code == 200
    assert [item["id"] for item in owner_list.json()] == [
        document_id
    ]
    assert outsider_list.status_code == 200
    assert outsider_list.json() == []

    assert client_b.get(
        f"/api/documents/{document_id}"
    ).status_code == 404
    assert client_b.get(
        f"/api/documents/{document_id}/chunks"
    ).status_code == 404
    assert client_b.delete(
        f"/api/documents/{document_id}"
    ).status_code == 404

    assert client_a.get(
        f"/api/documents/{document_id}"
    ).status_code == 200


@pytest.mark.database
def test_chat_sessions_and_sources_are_isolated(
    api_client_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_a = api_client_factory()
    client_b = api_client_factory()

    register_user(
        client_a,
        unique_email("chat-owner"),
        "Chat Owner",
    )
    register_user(
        client_b,
        unique_email("chat-outsider"),
        "Chat Outsider",
    )

    session_a_response = client_a.post(
        "/api/chat/sessions",
        json={"title": "Private chat"},
    )
    session_b_response = client_b.post(
        "/api/chat/sessions",
        json={"title": "Outsider chat"},
    )

    assert session_a_response.status_code == 201
    assert session_b_response.status_code == 201

    session_a_id = session_a_response.json()["id"]
    session_b_id = session_b_response.json()["id"]

    assert [
        session["id"]
        for session in client_a.get(
            "/api/chat/sessions"
        ).json()
    ] == [session_a_id]
    assert [
        session["id"]
        for session in client_b.get(
            "/api/chat/sessions"
        ).json()
    ] == [session_b_id]

    assert client_b.get(
        f"/api/chat/sessions/{session_a_id}/documents"
    ).status_code == 404
    assert client_b.get(
        f"/api/chat/sessions/{session_a_id}/messages"
    ).status_code == 404
    assert client_b.patch(
        f"/api/chat/sessions/{session_a_id}",
        json={"title": "Unauthorized title"},
    ).status_code == 404
    assert client_b.delete(
        f"/api/chat/sessions/{session_a_id}"
    ).status_code == 404
    assert client_b.post(
        f"/api/chat/sessions/{session_a_id}/messages",
        json={"content": "Unauthorized message"},
    ).status_code == 404

    monkeypatch.setattr(
        chat_routes,
        "retrieve_relevant_chunks",
        lambda **kwargs: [],
    )

    message_response = client_a.post(
        f"/api/chat/sessions/{session_a_id}/messages",
        json={"content": "Belgenin sahibi kim?"},
    )

    assert message_response.status_code == 201
    assistant_message_id = message_response.json()[
        "assistant_message"
    ]["id"]

    source_url = (
        f"/api/chat/sessions/{session_a_id}/messages/"
        f"{assistant_message_id}/sources"
    )

    assert client_a.get(source_url).status_code == 200
    assert client_a.get(source_url).json() == []
    assert client_b.get(source_url).status_code == 404
