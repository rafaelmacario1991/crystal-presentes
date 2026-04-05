"""
Autenticação do painel admin.
- 1 único usuário: credenciais em .env
- Sessão via JWT em cookie httpOnly
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Cookie, HTTPException, status
import bcrypt as _bcrypt
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()

ALGORITHM = "HS256"


# ============================================================
# Verificação de senha
# ============================================================

def verify_password(plain: str) -> bool:
    """Verifica a senha do admin contra o hash em .env."""
    return _bcrypt.checkpw(plain.encode(), settings.admin_password_hash.encode())


def verify_admin_credentials(email: str, password: str) -> bool:
    if email.lower() != settings.admin_email.lower():
        return False
    return verify_password(password)


# ============================================================
# JWT
# ============================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


# ============================================================
# Dependência FastAPI — protege rotas do admin
# ============================================================

def require_admin(crystal_session: Optional[str] = Cookie(default=None)):
    """Dependência que exige sessão admin válida. Redireciona para login se inválida."""
    if not crystal_session:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )
    try:
        payload = decode_token(crystal_session)
        email: str = payload.get("sub")
        if not email or email.lower() != settings.admin_email.lower():
            raise HTTPException(
                status_code=status.HTTP_303_SEE_OTHER,
                headers={"Location": "/admin/login"},
            )
        return email
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )
