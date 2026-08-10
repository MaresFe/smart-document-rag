import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.account_token import AccountToken
from app.models.user import User


INVITATION_PURPOSE = "invitation"
PASSWORD_RESET_PURPOSE = "password_reset"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_account_token() -> str:
    return secrets.token_urlsafe(32)


def hash_account_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8"),
    ).hexdigest()


def create_invitation_token(
    db: Session,
    email: str,
    created_by_user: User,
) -> tuple[AccountToken, str]:
    now = utc_now()

    db.execute(
        update(AccountToken)
        .where(
            AccountToken.purpose == INVITATION_PURPOSE,
            AccountToken.email == email,
            AccountToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    raw_token = generate_account_token()

    invitation = AccountToken(
        email=email,
        token_hash=hash_account_token(raw_token),
        purpose=INVITATION_PURPOSE,
        created_by_user_id=created_by_user.id,
        expires_at=now
        + timedelta(
            hours=settings.account_invitation_hours,
        ),
    )

    db.add(invitation)
    db.flush()

    return invitation, raw_token


def find_valid_invitation(
    db: Session,
    raw_token: str,
) -> AccountToken | None:
    statement = select(AccountToken).where(
        AccountToken.token_hash
        == hash_account_token(raw_token),
        AccountToken.purpose == INVITATION_PURPOSE,
        AccountToken.used_at.is_(None),
        AccountToken.expires_at > utc_now(),
    )

    return db.scalar(statement)


def create_password_reset_token(
    db: Session,
    user: User,
) -> tuple[AccountToken, str]:
    now = utc_now()

    db.execute(
        update(AccountToken)
        .where(
            AccountToken.purpose
            == PASSWORD_RESET_PURPOSE,
            AccountToken.user_id == user.id,
            AccountToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    raw_token = generate_account_token()

    password_reset = AccountToken(
        user_id=user.id,
        token_hash=hash_account_token(raw_token),
        purpose=PASSWORD_RESET_PURPOSE,
        expires_at=now
        + timedelta(
            minutes=(
                settings.account_password_reset_minutes
            ),
        ),
    )

    db.add(password_reset)
    db.flush()

    return password_reset, raw_token


def find_valid_password_reset(
    db: Session,
    raw_token: str,
) -> AccountToken | None:
    statement = select(AccountToken).where(
        AccountToken.token_hash
        == hash_account_token(raw_token),
        AccountToken.purpose
        == PASSWORD_RESET_PURPOSE,
        AccountToken.used_at.is_(None),
        AccountToken.expires_at > utc_now(),
    )

    return db.scalar(statement)


def consume_password_reset_tokens(
    db: Session,
    user_id: UUID,
) -> None:
    db.execute(
        update(AccountToken)
        .where(
            AccountToken.purpose
            == PASSWORD_RESET_PURPOSE,
            AccountToken.user_id == user_id,
            AccountToken.used_at.is_(None),
        )
        .values(used_at=utc_now())
    )
