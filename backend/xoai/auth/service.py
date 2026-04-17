"""Auth service: password hashing, JWT tokens, email verification, encryption."""

import json
import base64
import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import aiosmtplib
from email.message import EmailMessage
from cryptography.fernet import Fernet

from xoai.config import settings

# Derive a Fernet key from SECRET_KEY (pad/hash to 32 bytes, base64)
_fernet_key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
_fernet = Fernet(_fernet_key)

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 365 * 100  # 100 years
REFRESH_TOKEN_EXPIRE_DAYS = 365 * 100  # 100 years


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


async def send_verification_email(to_email: str, code: str):
    """Send verification email using admin SMTP settings and Admin's profile email."""
    from xoai.db.mongo import db
    
    # 1. Fetch SMTP settings
    smtp_setting = await db.settings.find_one({"key": "smtp"})
    if not smtp_setting:
        return False
    
    # 2. Fetch Admin's email (Sender)
    # The user said: "Only when admin adds his email, use his email for smtp verification code sending!!"
    admin_user = await db.users.find_one({"role": "admin"})
    admin_email = admin_user.get("email") if admin_user else None
    
    if not admin_email:
        print("SMTP: Admin email not configured in profile. Skipping send.")
        return False
    
    try:
        settings_data = decrypt_json(smtp_setting["value_encrypted"])
        
        msg = EmailMessage()
        msg["Subject"] = "XOAI Verification Code"
        msg["From"] = admin_email
        msg["To"] = to_email
        
        if code.startswith(("http://", "https://")):
            msg.set_content(
                "Verify your XOAI email address using this link:\n\n"
                f"{code}\n\n"
                "If you did not request this, ignore this message."
            )
        else:
            msg.set_content(f"Your XOAI verification code is: {code}\n\nThis code will expire in 10 minutes.")
        
        await aiosmtplib.send(
            msg,
            hostname=settings_data.get("host", "smtp.gmail.com"),
            port=int(settings_data.get("port", 587)),
            username=settings_data.get("sender_email"), # Auth username (may be different from From)
            password=settings_data.get("password"),
            start_tls=True
        )
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False
