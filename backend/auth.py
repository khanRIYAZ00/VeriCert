import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Membership, User

security = HTTPBearer(auto_error=False)
TOKEN_SECRET = os.getenv("VERICERT_TOKEN_SECRET", "change-this-before-production")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt, digest = stored.split("$", 1)
    return hmac.compare_digest(hash_password(password, salt), stored)


def create_token(user: User) -> str:
    expires = int((datetime.now(timezone.utc) + timedelta(hours=12)).timestamp())
    body = f"{user.id}:{expires}".encode()
    signature = hmac.new(TOKEN_SECRET.encode(), body, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(body + b":" + signature).decode()


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security), db: Session = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        raw = base64.urlsafe_b64decode(credentials.credentials.encode())
        body, signature = raw.rsplit(b":", 1)
        expected = hmac.new(TOKEN_SECRET.encode(), body, hashlib.sha256).digest()
        user_id, expires = body.decode().split(":")
        if not hmac.compare_digest(signature, expected) or int(expires) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user


def require_club_access(club_id: int, user: User, db: Session) -> None:
    if user.is_platform_admin:
        return
    member = db.query(Membership).filter_by(user_id=user.id, club_id=club_id).first()
    if not member:
        raise HTTPException(status_code=403, detail="You do not have access to this club")
