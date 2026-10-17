import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Membership, User

security = HTTPBearer(auto_error=False)
password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def get_token_secret() -> bytes:
    value = os.getenv("VERICERT_TOKEN_SECRET", "")
    secret = value.encode("utf-8")
    if len(secret) < 32:
        raise RuntimeError("VERICERT_TOKEN_SECRET must contain at least 32 bytes")
    return secret


def validate_auth_configuration() -> None:
    get_token_secret()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, stored: str) -> bool:
    if not stored.startswith("$argon2id$"):
        return False
    try:
        return password_hasher.verify(stored, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def _encode_urlsafe(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_urlsafe(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_token(user: User) -> str:
    payload = json.dumps(
        {
            "sub": user.id,
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=12)).timestamp()),
            "ver": user.token_version,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    encoded_payload = _encode_urlsafe(payload)
    signature = hmac.new(get_token_secret(), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded_payload}.{_encode_urlsafe(signature)}"


def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        encoded_payload, encoded_signature = credentials.credentials.split(".", 1)
        signature = _decode_urlsafe(encoded_signature)
        expected = hmac.new(
            get_token_secret(),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid token signature")
        payload = json.loads(_decode_urlsafe(encoded_payload))
        user_id = int(payload["sub"])
        expires_at = int(payload["exp"])
        token_version = int(payload["ver"])
        if expires_at <= int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("Token expired")
    except (ValueError, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is inactive")
    if token_version != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has been revoked")
    return user


def get_current_user(user: User = Depends(get_authenticated_user)) -> User:
    if user.must_change_password:
        raise HTTPException(status_code=403, detail="Password change required")
    return user


def get_platform_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_platform_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user


def require_club_access(club_id: int, user: User, db: Session) -> None:
    if user.is_platform_admin:
        return
    member = db.query(Membership).filter_by(user_id=user.id, club_id=club_id).first()
    if not member:
        raise HTTPException(status_code=403, detail="You do not have access to this club")
