import argparse
from getpass import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import CandidateProfile, EmployerProfile, User


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a local Rohobot user account.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=("admin", "candidate", "employer"), required=True)
    parser.add_argument("--name", required=True, help="Candidate full name or employer organization name.")
    args = parser.parse_args()
    password = getpass("Password (at least 12 characters): ")
    if len(password) < 12:
        parser.error("Password must contain at least 12 characters.")

    email = args.email.strip().lower()
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email == email)):
            parser.error("An account with this email already exists.")
        user = User(email=email, password_hash=hash_password(password), role=args.role, is_active=True)
        db.add(user)
        db.flush()
        if args.role == "candidate":
            db.add(CandidateProfile(user_id=user.id, full_name=args.name.strip()))
        elif args.role == "employer":
            db.add(EmployerProfile(user_id=user.id, organization_name=args.name.strip(), status="Profile Incomplete"))
        db.commit()
    print(f"Created {args.role} account {email}.")


if __name__ == "__main__":
    main()
