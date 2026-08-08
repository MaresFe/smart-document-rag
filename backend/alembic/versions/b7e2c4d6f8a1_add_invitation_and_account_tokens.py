"""add invitation and account tokens

Revision ID: b7e2c4d6f8a1
Revises: a1f8d4c2e6b9
Create Date: 2026-08-09 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b7e2c4d6f8a1"
down_revision: str | Sequence[str] | None = "a1f8d4c2e6b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "email_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Bu özellik eklenmeden önce oluşturulan hesapların erişimini korur.
    # Yeni hesaplar doğrulama akışından geçmeden bu alanı alamaz.
    op.execute(
        "UPDATE users "
        "SET email_verified_at = NOW() "
        "WHERE email_verified_at IS NULL"
    )

    op.create_table(
        "account_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "email",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "token_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "purpose",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "purpose IN "
                "('invitation', 'email_verification', 'password_reset')"
            ),
            name="check_account_tokens_purpose",
        ),
        sa.CheckConstraint(
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
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_account_tokens_created_by_user_id"),
        "account_tokens",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_account_tokens_email"),
        "account_tokens",
        ["email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_account_tokens_expires_at"),
        "account_tokens",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_account_tokens_purpose"),
        "account_tokens",
        ["purpose"],
        unique=False,
    )
    op.create_index(
        op.f("ix_account_tokens_token_hash"),
        "account_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_account_tokens_user_id"),
        "account_tokens",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_account_tokens_user_id"),
        table_name="account_tokens",
    )
    op.drop_index(
        op.f("ix_account_tokens_token_hash"),
        table_name="account_tokens",
    )
    op.drop_index(
        op.f("ix_account_tokens_purpose"),
        table_name="account_tokens",
    )
    op.drop_index(
        op.f("ix_account_tokens_expires_at"),
        table_name="account_tokens",
    )
    op.drop_index(
        op.f("ix_account_tokens_email"),
        table_name="account_tokens",
    )
    op.drop_index(
        op.f("ix_account_tokens_created_by_user_id"),
        table_name="account_tokens",
    )
    op.drop_table("account_tokens")

    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "is_admin")
