import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Union, Optional

import pyotp
import jwt
import bcrypt

from app.core.config import settings


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any]) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_temporary_token(subject: Union[str, Any]) -> str:
    # 5 minutes expiration for completing MFA
    expire = datetime.utcnow() + timedelta(minutes=5)
    to_encode = {"exp": expire, "sub": str(subject), "mfa": "pending"}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


# MFA / TOTP Logic
def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(secret: str, user_email: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=user_email, issuer_name="MiniBankSystem"
    )


def verify_totp(secret: str, token: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(token)


# OAuth 2.0 PKCE Helpers
def generate_code_verifier(length: int = 43) -> str:
    """Generate a random code verifier for PKCE (testing purposes mostly, clients generate this)."""
    import secrets
    import string
    # Length between 43 and 128 as per RFC 7636
    chars = string.ascii_letters + string.digits + "-._~"
    return "".join(secrets.choice(chars) for _ in range(length))

def generate_code_challenge(verifier: str, method: str = "S256") -> str:
    """Generate a code challenge from a verifier."""
    if method == "S256":
        hashed = hashlib.sha256(verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(hashed).decode("ascii").rstrip("=")
    elif method == "plain":
        return verifier
    else:
        raise ValueError("Unsupported code challenge method")

def verify_code_challenge(verifier: str, challenge: str, method: str) -> bool:
    """Verify that a code verifier matches the code challenge."""
    if method == "S256":
        expected_challenge = generate_code_challenge(verifier, method="S256")
        return secrets.compare_digest(expected_challenge, challenge)
    elif method == "plain":
        return secrets.compare_digest(verifier, challenge)
    return False
