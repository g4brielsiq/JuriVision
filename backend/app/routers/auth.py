"""
Router de Autenticação (JWT) — JuriVision.
Rastreabilidade:
- ARCHITECTURE.md: Seção 8.1 (POST /api/v1/auth/login)
- MODELING.md: RF-01 (Autenticação de Profissional do Direito), UC-01, CT-01
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.entities import Usuario
from app.schemas.contracts import (
    LoginRequest, LoginResponse, RegisterRequest, RegisterResponse, UsuarioProfileSchema,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticação (RF-01)"])


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login_advogado(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """
    Autentica o profissional do direito mediante email e senha, emitindo token JWT assinado.
    Credenciais inválidas retornam HTTP 401 Unauthorized (RF-01 / CT-01).
    """
    usuario = db.query(Usuario).filter(Usuario.email == payload.email.strip().lower()).first()
    if not usuario or not verify_password(payload.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas. Verifique o e-mail e a senha informados.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        subject=usuario.id,
        extra_claims={"nome": usuario.nome, "oab": usuario.numero_oab, "email": usuario.email},
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        usuario=UsuarioProfileSchema(
            id=usuario.id,
            nome=usuario.nome,
            oab=usuario.numero_oab,
        ),
    )


def verificar_conflito_cadastro(db: Session, payload: RegisterRequest) -> None:
    if db.scalar(select(Usuario.id).where(Usuario.email == payload.email).limit(1)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado.")
    # Considera inscrições armazenadas antes da normalização.
    oab_normalizada = func.upper(func.replace(Usuario.numero_oab, " ", ""))
    if db.scalar(select(Usuario.id).where(oab_normalizada == payload.numero_oab).limit(1)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Número OAB já cadastrado.")


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register_advogado(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    """Cria a conta do advogado e retorna seus dados públicos."""
    verificar_conflito_cadastro(db, payload)
    novo_usuario = Usuario(
        nome=payload.nome,
        email=payload.email,
        senha_hash=hash_password(payload.senha),
        numero_oab=payload.numero_oab,
    )
    db.add(novo_usuario)
    try:
        db.flush()
        response = RegisterResponse(
            id=novo_usuario.id,
            nome=novo_usuario.nome,
            email=novo_usuario.email,
            oab=novo_usuario.numero_oab,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        verificar_conflito_cadastro(db, payload)
        raise

    return response
