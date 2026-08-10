import uuid
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings


password_hasher = PasswordHash.recommended()


class InvalidAccessTokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(
    password: str,
    password_hash: str,
) -> bool:
    return password_hasher.verify(
        password,
        password_hash,
    )


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now
        + timedelta(
            minutes=settings.auth_access_token_minutes,
        ),
    }

    return jwt.encode(
        payload,
        settings.auth_secret_key.get_secret_value(),
        algorithm=settings.auth_algorithm,
    )


def decode_access_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(
            token,
            settings.auth_secret_key.get_secret_value(),
            algorithms=[settings.auth_algorithm],
        )

        if payload.get("type") != "access":
            raise InvalidAccessTokenError

        subject = payload.get("sub")

        if not isinstance(subject, str):
            raise InvalidAccessTokenError

        return uuid.UUID(subject)

    except (
        InvalidTokenError,
        TypeError,
        ValueError,
    ) as error:
        raise InvalidAccessTokenError from error