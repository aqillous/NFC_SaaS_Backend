"""
Create an administrator user.

Since there is no public registration endpoint (admins are the only
authenticated users, managed internally), the first admin(s) must be
created via this script.

Usage:
    python -m scripts.create_admin --email admin@mydomain.com --password "StrongPassword123!" --superuser
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an admin user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--superuser", action="store_true", help="Grant superuser privileges")
    args = parser.parse_args()

    email = args.email.strip().lower()

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"A user with email '{email}' already exists.")
            return

        user = User(
            email=email,
            password_hash=hash_password(args.password),
            is_active=True,
            is_superuser=args.superuser,
        )
        db.add(user)
        db.commit()
        print(f"Admin user created: {email} (superuser={args.superuser})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
