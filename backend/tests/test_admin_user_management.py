from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User


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
def test_admin_endpoints_reject_regular_users(
    api_client_factory,
) -> None:
    regular_client = api_client_factory()
    regular_user = register_user(
        regular_client,
        unique_email("regular"),
        "Regular User",
    )

    assert regular_client.get(
        "/api/admin/users",
    ).status_code == 403
    assert regular_client.patch(
        f"/api/admin/users/{regular_user['id']}",
        json={"is_active": False},
    ).status_code == 403


@pytest.mark.database
def test_admin_can_list_deactivate_and_reactivate_user(
    api_client_factory,
    db_session: Session,
) -> None:
    admin_client = api_client_factory()
    user_client = api_client_factory()

    admin = register_user(
        admin_client,
        unique_email("admin"),
        "Admin User",
    )
    regular_user = register_user(
        user_client,
        unique_email("managed"),
        "Managed User",
    )
    promote_user(db_session, str(admin["id"]))

    list_response = admin_client.get(
        "/api/admin/users",
    )

    assert list_response.status_code == 200
    users = list_response.json()
    listed_ids = {user["id"] for user in users}
    assert str(admin["id"]) in listed_ids
    assert str(regular_user["id"]) in listed_ids

    for user in users:
        assert "password" not in user
        assert "password_hash" not in user

    deactivate_response = admin_client.patch(
        f"/api/admin/users/{regular_user['id']}",
        json={"is_active": False},
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    assert user_client.get(
        "/api/auth/me",
    ).status_code == 401
    assert user_client.post(
        "/api/auth/login",
        json={
            "email": regular_user["email"],
            "password": PASSWORD,
        },
    ).status_code == 403

    reactivate_response = admin_client.patch(
        f"/api/admin/users/{regular_user['id']}",
        json={"is_active": True},
    )
    assert reactivate_response.status_code == 200
    assert reactivate_response.json()["is_active"] is True

    assert user_client.post(
        "/api/auth/login",
        json={
            "email": regular_user["email"],
            "password": PASSWORD,
        },
    ).status_code == 200


@pytest.mark.database
def test_admin_cannot_change_admin_status_or_assign_role(
    api_client_factory,
    db_session: Session,
) -> None:
    admin_client = api_client_factory()
    second_admin_client = api_client_factory()
    regular_client = api_client_factory()

    admin = register_user(
        admin_client,
        unique_email("protected-admin"),
        "Protected Admin",
    )
    second_admin = register_user(
        second_admin_client,
        unique_email("second-admin"),
        "Second Admin",
    )
    regular_user = register_user(
        regular_client,
        unique_email("role-target"),
        "Role Target",
    )

    promote_user(db_session, str(admin["id"]))
    promote_user(db_session, str(second_admin["id"]))

    assert admin_client.patch(
        f"/api/admin/users/{admin['id']}",
        json={"is_active": False},
    ).status_code == 400
    assert admin_client.patch(
        f"/api/admin/users/{second_admin['id']}",
        json={"is_active": False},
    ).status_code == 400
    assert admin_client.patch(
        f"/api/admin/users/{regular_user['id']}",
        json={
            "is_active": True,
            "is_admin": True,
        },
    ).status_code == 422
