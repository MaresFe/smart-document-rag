from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    InvalidAccessTokenError,
    decode_access_token,
)
from app.db.session import get_db
from app.models.user import User


UNAUTHORIZED_EXCEPTION = HTTPException(
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
        raise UNAUTHORIZED_EXCEPTION

    try:
        user_id = decode_access_token(access_token)
    except InvalidAccessTokenError as error:
        raise UNAUTHORIZED_EXCEPTION from error

    user = db.get(User, user_id)

    if user is None or not user.is_active:
        raise UNAUTHORIZED_EXCEPTION

    return user