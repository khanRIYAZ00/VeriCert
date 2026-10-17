import argparse
import re
from datetime import datetime
from getpass import getpass

from dotenv import load_dotenv

load_dotenv()

from .auth import hash_password
from .database import SessionLocal, init_database
from .models import SecurityAuditLog, User


def normalized_email(value: str) -> str:
    email = value.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) or len(email) > 255:
        raise SystemExit("Enter a valid email address.")
    return email


def read_admin_password() -> str:
    password = getpass("New administrator password (minimum 16 characters): ")
    confirmation = getpass("Confirm password: ")
    if len(password) < 16 or len(password) > 128:
        raise SystemExit("Administrator password must be between 16 and 128 characters.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    return password


def bootstrap_admin() -> None:
    email = normalized_email(input("Administrator email: "))
    password = read_admin_password()
    db = SessionLocal()
    try:
        if db.query(User.id).filter(User.is_platform_admin.is_(True)).first():
            raise SystemExit("An administrator already exists; use set-password for recovery.")
        if db.query(User.id).filter_by(email=email).first():
            raise SystemExit("That email is already registered to another account.")
        user = User(
            email=email,
            password_hash=hash_password(password),
            is_platform_admin=True,
            role="platform_admin",
            is_active=True,
            must_change_password=False,
            password_changed_at=datetime.utcnow(),
        )
        db.add(user)
        db.flush()
        db.add(SecurityAuditLog(action="platform_admin_bootstrapped", subject_user_id=user.id))
        db.commit()
        print(f"Administrator account created for {email}.")
    finally:
        db.close()


def reset_admin_password() -> None:
    email = normalized_email(input("Existing administrator email: "))
    password = read_admin_password()
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email, is_platform_admin=True).first()
        if not user:
            raise SystemExit("No administrator account exists for that email.")
        user.password_hash = hash_password(password)
        user.password_changed_at = datetime.utcnow()
        user.must_change_password = False
        user.token_version += 1
        db.add(
            SecurityAuditLog(
                action="platform_admin_password_reset_by_operator",
                subject_user_id=user.id,
            )
        )
        db.commit()
        print(f"Administrator password reset for {email}; existing sessions were revoked.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="VeriCert administrator account maintenance")
    parser.add_argument("command", choices=("bootstrap", "set-password"))
    command = parser.parse_args().command

    init_database()
    if command == "bootstrap":
        bootstrap_admin()
    else:
        reset_admin_password()


if __name__ == "__main__":
    main()
