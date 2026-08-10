from datetime import datetime, timezone
import logging
from urllib.parse import urlencode

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import (
    get_current_admin,
    get_current_user,
)
from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    InvitationAccept,
    InvitationCreate,
    InvitationPreview,
    InvitationRead,
    InvitationTokenRequest,
    PasswordResetConfirm,
    PasswordResetPreview,
    PasswordResetRequest,
    PasswordResetRequestRead,
    PasswordResetTokenRequest,
    UserLogin,
    UserRead,
    UserRegister,
)
from app.services.account_tokens import (
    consume_password_reset_tokens,
    create_password_reset_token,
    create_invitation_token,
    find_valid_invitation,
    find_valid_password_reset,
)
from app.services.email_delivery import (
    EmailDeliveryError,
    send_invitation_email,
    send_password_reset_email,
)
from app.services.rate_limiting import (
    RateLimitPolicy,
    clear_auth_rate_limit,
    enforce_auth_rate_limit,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

auth_logger = logging.getLogger("uvicorn.error")

PASSWORD_RESET_RESPONSE_MESSAGE = (
    "Hesap uygunsa parola yenileme bağlantısı gönderildi."
)

DUMMY_PASSWORD_HASH = hash_password(
    "dummy-password-used-only-for-timing-equality",
)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def login_rate_limit_policy() -> RateLimitPolicy:
    return RateLimitPolicy(
        max_attempts=settings.auth_login_max_attempts,
        window_seconds=(
            settings.auth_login_window_seconds
        ),
    )


def password_reset_rate_limit_policy() -> RateLimitPolicy:
    return RateLimitPolicy(
        max_attempts=(
            settings.auth_password_reset_max_attempts
        ),
        window_seconds=(
            settings.auth_password_reset_window_seconds
        ),
    )


def token_rate_limit_policy() -> RateLimitPolicy:
    return RateLimitPolicy(
        max_attempts=settings.auth_token_max_attempts,
        window_seconds=(
            settings.auth_token_window_seconds
        ),
    )


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


def build_invitation_url(raw_token: str) -> str:
    query = urlencode({"token": raw_token})
    base_url = settings.frontend_base_url.rstrip("/")
    return f"{base_url}/accept-invitation?{query}"


def build_password_reset_url(raw_token: str) -> str:
    query = urlencode({"token": raw_token})
    base_url = settings.frontend_base_url.rstrip("/")
    return f"{base_url}/reset-password?{query}"


def deliver_password_reset_safely(
    recipient: str,
    password_reset_url: str,
) -> None:
    try:
        send_password_reset_email(
            recipient=recipient,
            password_reset_url=password_reset_url,
        )
    except EmailDeliveryError:
        auth_logger.exception(
            "Password reset email delivery failed | recipient=%s",
            recipient,
        )


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
    if settings.registration_mode != "open":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration is disabled.",
        )

    normalized_email = normalize_email(str(payload.email))

    if find_user_by_email(db, normalized_email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=normalized_email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        is_active=True,
        email_verified_at=datetime.now(timezone.utc),
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
    "/invitations",
    response_model=InvitationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_invitation(
    payload: InvitationCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> InvitationRead:
    normalized_email = normalize_email(str(payload.email))

    if find_user_by_email(db, normalized_email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    invitation, raw_token = create_invitation_token(
        db=db,
        email=normalized_email,
        created_by_user=current_admin,
    )

    db.commit()
    db.refresh(invitation)

    invitation_url = build_invitation_url(raw_token)

    try:
        send_invitation_email(
            recipient=normalized_email,
            invitation_url=invitation_url,
        )
    except EmailDeliveryError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    return InvitationRead(
        id=invitation.id,
        email=normalized_email,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        delivery_mode=settings.email_delivery_mode,
        invitation_url=(
            invitation_url
            if settings.email_delivery_mode == "console"
            else None
        ),
    )


@router.post(
    "/invitations/accept",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def accept_invitation(
    payload: InvitationAccept,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    enforce_auth_rate_limit(
        scope="invitation-accept",
        request=request,
        identity=payload.token,
        policy=token_rate_limit_policy(),
    )

    invitation = find_valid_invitation(
        db=db,
        raw_token=payload.token,
    )

    if invitation is None or invitation.email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation is invalid or expired.",
        )

    normalized_email = normalize_email(invitation.email)

    if find_user_by_email(db, normalized_email) is not None:
        invitation.used_at = datetime.now(timezone.utc)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation is invalid or expired.",
        )

    now = datetime.now(timezone.utc)
    user = User(
        email=normalized_email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        is_active=True,
        is_admin=False,
        email_verified_at=now,
    )
    invitation.used_at = now

    db.add(user)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation is invalid or expired.",
        ) from error

    db.refresh(user)

    access_token = create_access_token(user.id)
    set_auth_cookie(response, access_token)

    return user


@router.post(
    "/invitations/preview",
    response_model=InvitationPreview,
)
def preview_invitation(
    payload: InvitationTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> InvitationPreview:
    enforce_auth_rate_limit(
        scope="invitation-preview",
        request=request,
        identity=payload.token,
        policy=token_rate_limit_policy(),
    )

    invitation = find_valid_invitation(
        db=db,
        raw_token=payload.token,
    )

    if invitation is None or invitation.email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation is invalid or expired.",
        )

    return InvitationPreview(
        email=normalize_email(invitation.email),
        expires_at=invitation.expires_at,
    )


@router.post(
    "/password-reset/request",
    response_model=PasswordResetRequestRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> PasswordResetRequestRead:
    normalized_email = normalize_email(str(payload.email))

    enforce_auth_rate_limit(
        scope="password-reset-request",
        request=request,
        identity=normalized_email,
        policy=password_reset_rate_limit_policy(),
    )

    user = find_user_by_email(
        db=db,
        email=normalized_email,
    )

    if (
        user is not None
        and user.is_active
        and user.email_verified_at is not None
        and user.password_hash is not None
    ):
        _, raw_token = create_password_reset_token(
            db=db,
            user=user,
        )
        db.commit()

        password_reset_url = build_password_reset_url(
            raw_token,
        )

        background_tasks.add_task(
            deliver_password_reset_safely,
            user.email,
            password_reset_url,
        )

    return PasswordResetRequestRead(
        message=PASSWORD_RESET_RESPONSE_MESSAGE,
    )


@router.post(
    "/password-reset/preview",
    response_model=PasswordResetPreview,
)
def preview_password_reset(
    payload: PasswordResetTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> PasswordResetPreview:
    enforce_auth_rate_limit(
        scope="password-reset-preview",
        request=request,
        identity=payload.token,
        policy=token_rate_limit_policy(),
    )

    password_reset = find_valid_password_reset(
        db=db,
        raw_token=payload.token,
    )

    if password_reset is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset link is invalid or expired.",
        )

    user = db.get(User, password_reset.user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset link is invalid or expired.",
        )

    return PasswordResetPreview(
        expires_at=password_reset.expires_at,
    )


@router.post(
    "/password-reset/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
)
def confirm_password_reset(
    payload: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    enforce_auth_rate_limit(
        scope="password-reset-confirm",
        request=request,
        identity=payload.token,
        policy=token_rate_limit_policy(),
    )

    password_reset = find_valid_password_reset(
        db=db,
        raw_token=payload.token,
    )

    if password_reset is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset link is invalid or expired.",
        )

    user = db.get(User, password_reset.user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset link is invalid or expired.",
        )

    user.password_hash = hash_password(payload.password)

    consume_password_reset_tokens(
        db=db,
        user_id=user.id,
    )

    db.commit()

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


@router.post(
    "/login",
    response_model=UserRead,
)
def login(
    payload: UserLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    normalized_email = normalize_email(str(payload.email))
    rate_limit_key = enforce_auth_rate_limit(
        scope="login",
        request=request,
        identity=normalized_email,
        policy=login_rate_limit_policy(),
    )

    user = find_user_by_email(
        db,
        normalized_email,
    )

    password_hash = (
        user.password_hash
        if user is not None and user.password_hash is not None
        else DUMMY_PASSWORD_HASH
    )
    password_is_valid = verify_password(
        payload.password,
        password_hash,
    )

    credentials_are_valid = (
        user is not None
        and user.password_hash is not None
        and password_is_valid
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

    if user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address is not verified.",
        )

    clear_auth_rate_limit(rate_limit_key)

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
