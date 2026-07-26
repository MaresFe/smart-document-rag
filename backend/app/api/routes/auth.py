from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    UserLogin,
    UserRead,
    UserRegister,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def set_auth_cookie(
    response: Response,
    access_token: str,
) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=access_token,
        max_age=settings.auth_access_token_minutes * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )


def find_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    statement = select(User).where(
        func.lower(User.email) == normalize_email(email),
    )

    return db.scalar(statement)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: UserRegister,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    normalized_email = normalize_email(str(payload.email))

    existing_user = find_user_by_email(
        db,
        normalized_email,
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=normalized_email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        is_active=True,
    )

    db.add(user)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from error

    db.refresh(user)

    access_token = create_access_token(user.id)
    set_auth_cookie(response, access_token)

    return user


@router.post(
    "/login",
    response_model=UserRead,
)
def login(
    payload: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    user = find_user_by_email(
        db,
        str(payload.email),
    )

    credentials_are_valid = (
        user is not None
        and user.password_hash is not None
        and verify_password(
            payload.password,
            user.password_hash,
        )
    )

    if not credentials_are_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )

    access_token = create_access_token(user.id)
    set_auth_cookie(response, access_token)

    return user


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout() -> Response:
    response = Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )

    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )

    return response


@router.get(
    "/me",
    response_model=UserRead,
)
def read_current_user(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user