import uuid

from sqlalchemy.orm import Session

from app.models.user import User


DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def get_or_create_dev_user(db: Session) -> User:
    user = db.get(User, DEV_USER_ID)

    if user is not None:
        return user

    user = User(
        id=DEV_USER_ID,
        email="dev@example.com",
        full_name="Development User",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user