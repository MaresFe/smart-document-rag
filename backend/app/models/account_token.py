import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AccountToken(Base):
    __tablename__ = "account_tokens"

    __table_args__ = (
        CheckConstraint(
            (
                "purpose IN "
                "('invitation', 'email_verification', 'password_reset')"
            ),
            name="check_account_tokens_purpose",
        ),
        CheckConstraint(
            (
                "(purpose = 'invitation' "
                "AND email IS NOT NULL "
                "AND user_id IS NULL) "
                "OR "
                "(purpose IN ('email_verification', 'password_reset') "
                "AND user_id IS NOT NULL)"
            ),
            name="check_account_tokens_target",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    purpose: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="action_tokens",
    )

    created_by_user = relationship(
        "User",
        foreign_keys=[created_by_user_id],
        back_populates="issued_tokens",
    )
