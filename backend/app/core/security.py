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

from fastapi import Depends, HTTPException, Query, Request, status
import jwt
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.entities import Processo, Usuario

PUBLIC_OWNER_ID = "usr-01"


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
    request: Request,
    token: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> Optional[Usuario]:
    """
    Valida o token JWT (via cabeçalho Authorization Bearer ou query ?token=) quando enviado.
    Se nenhum token for fornecido, retorna None (contexto de demonstração pública).
    Se um token inválido, malformado ou expirado for fornecido, retorna HTTP 401.
    """
    auth_header = request.headers.get("Authorization")
    raw_token: Optional[str] = None

    if auth_header is not None:
        parts = auth_header.strip().split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Formato de cabeçalho Authorization inválido. Use 'Bearer <token>'.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raw_token = parts[1].strip()
    elif token is not None:
        if not token.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token JWT inválido ou vazio.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raw_token = token.strip()
    else:
        return None

    payload = decode_access_token(raw_token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token JWT inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario = db.query(Usuario).filter(Usuario.id == payload.get("sub")).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário do token não encontrado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario


def get_current_user_strict(
    current_user: Optional[Usuario] = Depends(get_optional_current_user),
) -> Usuario:
    """Exige um usuário autenticado com JWT válido; caso contrário retorna HTTP 401."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação JWT obrigatória para acessar este recurso.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def get_effective_user_id(current_user: Optional[Usuario]) -> str:
    """Retorna o ID do advogado autenticado ou o ID institucional público padrão."""
    return current_user.id if current_user is not None else PUBLIC_OWNER_ID


def build_processo_visibility_filter(current_user: Optional[Usuario]):
    """
    Isolamento multi-usuário:
    - Visitantes ou conta institucional padrão (usr-01) enxergam apenas o acervo público base.
    - Advogados autenticados enxergam o acervo público base + seus próprios processos privados.
    """
    if current_user is None or current_user.id == PUBLIC_OWNER_ID:
        return or_(Processo.usuario_id == PUBLIC_OWNER_ID, Processo.usuario_id.is_(None))
    return or_(
        Processo.usuario_id == PUBLIC_OWNER_ID,
        Processo.usuario_id.is_(None),
        Processo.usuario_id == current_user.id,
    )


def can_read_processo(proc: Processo, current_user: Optional[Usuario]) -> bool:
    """Verifica se o usuário atual tem permissão para visualizar o processo."""
    if proc.usuario_id in (None, PUBLIC_OWNER_ID):
        return True
    return current_user is not None and proc.usuario_id == current_user.id


def ensure_can_modify_processo(proc: Processo, current_user: Optional[Usuario]) -> None:
    """
    Garante isolamento em alterações/exclusões:
    - Se o processo for privado de outro advogado -> HTTP 404 (não vaza existência).
    - Se for do acervo público base e o usuário for uma conta externa -> HTTP 403 Forbidden.
    """
    if not can_read_processo(proc, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processo '{proc.id_processo}' não encontrado na base de conhecimento.",
        )
    if (
        current_user is not None
        and current_user.id != PUBLIC_OWNER_ID
        and proc.usuario_id in (None, PUBLIC_OWNER_ID)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: o acervo público institucional não pode ser alterado ou excluído por contas externas.",
        )
