"""
Ponto de entrada da API Core & Gateway REST (FastAPI) — JuriVision.
Rastreabilidade:
- ARCHITECTURE.md: Seções 3, 6 e 8; ADR-001, ADR-002 e ADR-003
- MODELING.md: RF-01 a RF-09, RNF-01 a RNF-08
"""
from contextlib import asynccontextmanager
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.seed import seed_initial_data
from app.routers import auth, dashboard, processos, relatorios

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("jurivision.main")


def _ensure_usuario_freemium_columns() -> None:
    """Garante colunas do modelo Freemium em bancos SQLite/PostgreSQL já inicializados."""
    inspector = inspect(engine)
    if "usuarios" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("usuarios")}
    statements: list[str] = []
    if "plano" not in cols:
        statements.append("ALTER TABLE usuarios ADD COLUMN plano VARCHAR(20) NOT NULL DEFAULT 'FREE'")
    if "analises_realizadas" not in cols:
        statements.append("ALTER TABLE usuarios ADD COLUMN analises_realizadas INTEGER NOT NULL DEFAULT 0")
    if statements:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))


def init_db_and_seed() -> None:
    """Garante criação de tabelas relacionais, migração incremental e carga idempotente inicial."""
    Base.metadata.create_all(bind=engine)
    _ensure_usuario_freemium_columns()
    with SessionLocal() as db:
        seed_initial_data(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inicializando JuriVision API Core (%s)...", settings.APP_VERSION)
    init_db_and_seed()
    yield
    logger.info("Encerrando JuriVision API Core.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "API Gateway e serviços de negócio da Plataforma Analítica e Preditiva JuriVision "
        "(Equipe Epsilon - UFAL). Implementa isolamento de IA via Port & Adapter (ADR-002) "
        "e barreira determinística local LGPD (RN-01)."
    ),
    lifespan=lifespan,
)

# Interoperabilidade entre Front-end (:5173) e Back-end (:8000) — RNF-03
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro dos Routers Oficiais (Seção 8 de ARCHITECTURE.md)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(processos.router)
app.include_router(relatorios.router)


@app.exception_handler(RequestValidationError)
async def handle_request_validation(request: Request, exc: RequestValidationError):
    if request.scope.get("endpoint") is auth.register_advogado:
        # Os erros do Pydantic podem incluir a senha ou o corpo original.
        errors = [
            {key: error[key] for key in ("loc", "msg", "type")}
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errors})
    return await request_validation_exception_handler(request, exc)


@app.get("/health", tags=["Healthcheck"])
def health_check():
    """Endpoint de verificação de integridade operacional e modo de provedor de IA."""
    return {
        "status": "ok",
        "service": "backend",
        "system": "JuriVision",
        "ai_provider_configured": settings.AI_PROVIDER,
    }


_DIST_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if settings.SERVE_FRONTEND_STATIC and _DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_DIST_DIR), html=True), name="frontend_static")
