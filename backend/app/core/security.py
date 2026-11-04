import os
import secrets
from pathlib import Path
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from app.core.config import data_path


def load_secret():
    configured = os.getenv('JWT_SECRET')
    if configured: return configured
    directory = Path(data_path)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / '.jwt-secret'
    try:
        with path.open('x', encoding='utf-8') as stream:
            value = secrets.token_urlsafe(48)
            stream.write(value)
        return value
    except FileExistsError:
        return path.read_text(encoding='utf-8').strip()

SECRET_KEY = load_secret()
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
pwd_context = CryptContext(schemes=['argon2'], deprecated='auto')

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta=None):
    payload = {**data, 'purpose': data.get('purpose', 'access'), 'exp': datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
