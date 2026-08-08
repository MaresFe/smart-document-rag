import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select


BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402


def normalize_email(email: str) -> str:
    return email.strip().lower()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage Smart Document RAG users.",
    )
    parser.add_argument(
        "action",
        choices=(
            "show",
            "promote",
            "demote",
            "verify-email",
        ),
    )
    parser.add_argument("email")
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    email = normalize_email(arguments.email)

    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(
                func.lower(User.email) == email,
            )
        )

        if user is None:
            print(f"User not found: {email}")
            return 1

        if arguments.action == "show":
            print(f"Email: {user.email}")
            print(f"Active: {user.is_active}")
            print(f"Verified: {user.email_verified_at is not None}")
            print(f"Admin: {user.is_admin}")
            return 0

        if arguments.action == "verify-email":
            user.email_verified_at = datetime.now(timezone.utc)

        elif arguments.action == "promote":
            if user.email_verified_at is None:
                print(
                    "Refusing to promote an unverified user. "
                    "Run verify-email first."
                )
                return 2

            user.is_admin = True

        elif arguments.action == "demote":
            user.is_admin = False

        db.commit()
        db.refresh(user)

        print(
            f"Updated {user.email}: "
            f"verified={user.email_verified_at is not None}, "
            f"admin={user.is_admin}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
