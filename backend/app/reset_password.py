import argparse
from getpass import getpass

from sqlalchemy import delete, select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User, UserSession


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset a local Rohobot administrator password.")
    parser.add_argument("--email", required=True, help="Email address of the existing admin account.")
    args = parser.parse_args()

    password = getpass("New password (at least 12 characters): ")
    confirmation = getpass("Confirm new password: ")
    if len(password) < 12 or len(password) > 128:
        parser.error("Password must be between 12 and 128 characters.")
    if password != confirmation:
        parser.error("The passwords do not match.")

    email = args.email.strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email, User.role == "admin"))
        if not user:
            parser.error(f"No administrator account exists for {email}.")

        user.password_hash = hash_password(password)
        db.execute(delete(UserSession).where(UserSession.user_id == user.id))
        db.commit()

    print(f"Password reset for administrator {email}. Sign in again with the new password.")


if __name__ == "__main__":
    main()
