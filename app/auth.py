from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt, JWTError
from passlib.context import CryptContext

# Constants (Consider loading from environment variables in production)
SECRET_KEY: str = "secret"  # ❗ Replace with a secure, environment-based secret
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------------------------
# Password Hashing
# ------------------------
def get_password_hash(password: str) -> str:
    """Hash a plain-text password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against the hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


# ------------------------
# JWT Token Creation
# ------------------------
def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.

    :param data: The payload data (usually includes user ID or email).
    :param expires_delta: Optional timedelta to override default expiry.
    :return: JWT token as string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ------------------------
# JWT Token Decoding
# ------------------------
def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    :param token: JWT token string.
    :return: Decoded token data (e.g. user ID/email).
    :raises JWTError: If token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise ValueError("Invalid or expired token") from e
