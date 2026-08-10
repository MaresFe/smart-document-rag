"""add image document types

Revision ID: a1f8d4c2e6b9
Revises: 35c6a245f832
Create Date: 2026-08-09

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1f8d4c2e6b9"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "35c6a245f832"
branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None
depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    """Allow OCR-supported image documents."""
    op.drop_constraint(
        "check_documents_file_type",
        "documents",
        type_="check",
    )

    op.create_check_constraint(
        "check_documents_file_type",
        "documents",
        (
            "file_type IN ('pdf', 'docx', 'txt', "
            "'csv', 'xlsx', 'png', 'jpg', 'jpeg')"
        ),
    )


def downgrade() -> None:
    """Remove image document types."""
    op.drop_constraint(
        "check_documents_file_type",
        "documents",
        type_="check",
    )

    op.create_check_constraint(
        "check_documents_file_type",
        "documents",
        (
            "file_type IN ('pdf', 'docx', 'txt', "
            "'csv', 'xlsx')"
        ),
    )
