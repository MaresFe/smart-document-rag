from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    InvalidAccessTokenError,
    decode_access_token,
)
from app.db.session import get_db
from app.models.user import User


def authentication_required() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
    )


def get_current_user(
    db: Session = Depends(get_db),
    access_token: str | None = Cookie(
        default=None,
        alias=settings.auth_cookie_name,
    ),
) -> User:
    if access_token is None:
        raise authentication_required()

    try:
        user_id = decode_access_token(access_token)
    except InvalidAccessTokenError as error:
        raise authentication_required() from error

    user = db.get(User, user_id)

    if (
        user is None
        or not user.is_active
        or user.email_verified_at is None
    ):
        raise authentication_required()

    return user


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator permission is required.",
        )

    return current_user
