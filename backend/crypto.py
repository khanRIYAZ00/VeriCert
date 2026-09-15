from pathlib import Path
import base64
import hashlib
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

KEYS_DIR = Path("keys")
PRIVATE_KEY_PATH = KEYS_DIR / "private_key.pem"
PUBLIC_KEY_PATH = KEYS_DIR / "public_key.pem"


def generate_keys():
    KEYS_DIR.mkdir(exist_ok=True)

    if PRIVATE_KEY_PATH.exists() and PUBLIC_KEY_PATH.exists():
        return

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    PRIVATE_KEY_PATH.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    PUBLIC_KEY_PATH.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


def load_private_key():
    return serialization.load_pem_private_key(
        PRIVATE_KEY_PATH.read_bytes(),
        password=None,
    )


def load_public_key():
    return serialization.load_pem_public_key(
        PUBLIC_KEY_PATH.read_bytes()
    )


def canonical_json(data: dict) -> bytes:
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def calculate_hash(data: dict) -> str:
    return hashlib.sha256(canonical_json(data)).hexdigest()


def sign_data(data: dict) -> str:
    private_key = load_private_key()
    signature = private_key.sign(canonical_json(data))

    return base64.b64encode(signature).decode("utf-8")


def verify_signature(data: dict, signature: str) -> bool:
    try:
        public_key = load_public_key()

        signature_bytes = base64.b64decode(signature)

        public_key.verify(
            signature_bytes,
            canonical_json(data),
        )

        return True

    except Exception:
        return False