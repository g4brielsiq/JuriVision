"""
Serviço de Segurança, Hash de Senhas e Emissão/Validação de Tokens JWT.
Rastreabilidade:
- EAP: 1.3.2 API REST
- Requisitos: RF-01 (Autenticação de Profissional do Direito), RNF-06 (Segurança / ISO 27001)
"""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from typing import Any, Dict, Optional

from fastapi import Depends, Header, HTTPException, status
import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.entities import Usuario


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """
    Gera hash seguro PBKDF2-HMAC-SHA256 determinístico e auditável (FIPS / ISO 27001),
    sem dependência de bibliotecas C externas vulneráveis a incompatibilidades de SO.
    """
    effective_salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        effective_salt.encode("utf-8"),
        120_000,
    )
    return f"pbkdf2_sha256${effective_salt}${dk.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Valida senha em texto plano contra o hash persistido em tempo constante."""
    try:
        algorithm, salt, _ = stored_hash.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate_hash = hash_password(plain_password, salt=salt)
        return hmac.compare_digest(candidate_hash, stored_hash)
    except ValueError:
        return False


def create_access_token(subject: str, extra_claims: Optional[Dict[str, Any]] = None) -> str:
    """Emite token JWT assinado (HS256) contendo identificação e registro OAB do advogado."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodifica e valida assinatura/expiração de um token JWT."""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def get_optional_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Optional[Usuario]:
    """
    Valida estritamente o cabeçalho Authorization Bearer quando enviado na requisição.
    - Sem cabeçalho Authorization: retorna None (preserva leitura inicial da interface e testes de contrato públicos).
    - Com cabeçalho inválido, malformado ou token expirado/adulterado: rejeita com HTTP 401 Unauthorized.
    """
    if not authorization or not authorization.strip():
        return None

    parts = authorization.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cabeçalho Authorization inválido. Utilize o formato 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = decode_access_token(parts[1].strip())
    subject = claims.get("sub") if claims else None
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token JWT inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario = db.query(Usuario).filter(Usuario.id == str(subject)).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário vinculado ao token não encontrado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario


def get_current_user(
    usuario: Optional[Usuario] = Depends(get_optional_current_user),
) -> Usuario:
    """Exige obrigatoriamente um token JWT válido, retornando HTTP 401 caso ausente."""
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação obrigatória. Envie um token Bearer válido.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario
