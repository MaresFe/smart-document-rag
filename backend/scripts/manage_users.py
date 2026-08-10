import argparse
import getpass
import sys
from datetime import datetime, timezone
from pathlib import Path

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError


BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402


def normalize_email(email: str) -> str:
    return validate_email(
        email.strip(),
        check_deliverability=False,
    ).normalized.lower()


def normalize_full_name(full_name: str | None) -> str | None:
    if full_name is None:
        return None

    normalized = " ".join(full_name.split())
    return normalized or None


def read_new_password() -> str | None:
    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Password again: ")

    if password != confirmation:
        print("Passwords do not match.")
        return None

    if not 10 <= len(password) <= 128:
        print("Password must contain between 10 and 128 characters.")
        return None

    return password


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage Smart Document RAG users.",
    )
    parser.add_argument(
        "action",
        choices=(
            "bootstrap-admin",
            "show",
            "promote",
            "demote",
            "verify-email",
        ),
    )
    parser.add_argument("email")
    parser.add_argument("--full-name")
    return parser


def main() -> int:
    arguments = build_parser().parse_args()

    try:
        email = normalize_email(arguments.email)
    except EmailNotValidError as error:
        print(f"Invalid email address: {error}")
        return 2

    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(
                func.lower(User.email) == email,
            )
        )

        if arguments.action == "bootstrap-admin":
            if user is not None:
                print(
                    "User already exists. Use verify-email and promote "
                    "instead of replacing the account."
                )
                return 1

            password = read_new_password()

            if password is None:
                return 2

            user = User(
                email=email,
                full_name=normalize_full_name(arguments.full_name),
                password_hash=hash_password(password),
                is_active=True,
                is_admin=True,
                email_verified_at=datetime.now(timezone.utc),
            )
            db.add(user)

            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                print(f"User already exists: {email}")
                return 1

            print(f"Bootstrap administrator created: {email}")
            return 0

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
