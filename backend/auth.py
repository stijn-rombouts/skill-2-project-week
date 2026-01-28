from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union  # ← Make sure Dict and Any are here!

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import pyotp

from database import get_db, User

# --------------------
# Security configuration
# --------------------
SECRET_KEY = "your-secret-key-change-this-in-production"  # Change this in production!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")


# --------------------
# TOTP helpers
# --------------------
def generate_totp_secret() -> str:
    """Return a new base32 TOTP secret."""
    return pyotp.random_base32()


def get_totp_provisioning_uri(secret: str, username: str, issuer: str = "skillLab") -> str:
    """Return provisioning URI (for QR code) for authenticator apps."""
    return pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=issuer)


def verify_totp_code(secret: str, code: str, window: int = 1) -> bool:
    """Verify a TOTP code. `window` allows a small +/- window for clock skew."""
    try:
        return pyotp.TOTP(secret).verify(str(code), valid_window=window)
    except Exception:
        return False


# --------------------
# Password helpers
# --------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


# --------------------
# JWT helpers
# --------------------
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_2fa_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a short-lived JWT used to authorize the second step of 2FA.
    Adds a claim '2fa': True so it can be distinguished from a full access token.
    """
    to_encode = data.copy()
    to_encode.update({"2fa": True})
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=5))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_2fa_token(token: str) -> Dict[str, Any]:
    """Verify and decode the short-lived 2FA token. Raises JWTError on invalid/expired token."""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if not payload.get("2fa"):
        raise JWTError("Token is not a 2FA token")
    return payload


# --------------------
# Auth helpers
# --------------------
def authenticate_user(db: Session, username: str, password: str) -> Union[User, bool]:
    """Authenticate a user by username and password."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    return user  # fixed: Python comment uses #
