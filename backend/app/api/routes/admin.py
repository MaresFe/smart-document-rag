from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import (
    AdminUserRead,
    AdminUserUpdate,
)


router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
)


def get_user_or_404(
    db: Session,
    user_id: UUID,
) -> User:
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return user


@router.get(
    "/users",
    response_model=list[AdminUserRead],
)
def list_users(
    db: Session = Depends(get_db),
    _current_admin: User = Depends(get_current_admin),
) -> list[User]:
    statement = select(User).order_by(
        User.created_at.desc(),
        User.email.asc(),
    )

    return list(db.scalars(statement).all())


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserRead,
)
def update_user(
    user_id: UUID,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> User:
    user = get_user_or_404(
        db=db,
        user_id=user_id,
    )

    if user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own account status.",
        )

    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Administrator accounts must be managed "
                "through the management command."
            ),
        )

    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)

    return user
