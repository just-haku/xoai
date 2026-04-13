"""Auth service: password hashing, JWT tokens, email verification, encryption."""

import json
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from cryptography.fernet import Fernet

from xoai.config import settings

# Derive a Fernet key from SECRET_KEY (pad/hash to 32 bytes, base64)
import base64
import hashlib

_fernet_key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
_fernet = Fernet(_fernet_key)

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])


def create_email_verification_token(email: str) -> str:
    payload = {
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        "type": "email_verify",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


# --- Fernet encryption for settings/api_keys stored in DB ---

def encrypt_value(value: dict | str) -> str:
    """Encrypt a dict or string for storage in MongoDB."""
    raw = json.dumps(value) if isinstance(value, dict) else value
    return _fernet.encrypt(raw.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    """Decrypt a stored value."""
    return _fernet.decrypt(encrypted.encode()).decode()


def decrypt_json(encrypted: str) -> dict:
    """Decrypt and parse JSON."""
    return json.loads(decrypt_value(encrypted))
