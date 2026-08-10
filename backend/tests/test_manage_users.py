import sys

from scripts import manage_users


class FakeSession:
    def __init__(self) -> None:
        self.added_user = None
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None

    def scalar(self, _statement):
        return None

    def add(self, user) -> None:
        self.added_user = user

    def commit(self) -> None:
        self.committed = True


def test_bootstrap_admin_creates_verified_admin(
    monkeypatch,
) -> None:
    session = FakeSession()
    passwords = iter(("safe-password", "safe-password"))

    monkeypatch.setattr(
        manage_users,
        "SessionLocal",
        lambda: session,
    )
    monkeypatch.setattr(
        manage_users.getpass,
        "getpass",
        lambda _prompt: next(passwords),
    )
    monkeypatch.setattr(
        manage_users,
        "hash_password",
        lambda password: f"hashed:{password}",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "manage_users.py",
            "bootstrap-admin",
            "ADMIN@EXAMPLE.COM",
            "--full-name",
            "  Yakamoz   Demir  ",
        ],
    )

    assert manage_users.main() == 0
    assert session.committed is True
    assert session.added_user.email == "admin@example.com"
    assert session.added_user.full_name == "Yakamoz Demir"
    assert session.added_user.password_hash == "hashed:safe-password"
    assert session.added_user.is_active is True
    assert session.added_user.is_admin is True
    assert session.added_user.email_verified_at is not None
