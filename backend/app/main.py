"""
Ponto de entrada da API Core & Gateway REST (FastAPI) — JuriVision.
Rastreabilidade:
- ARCHITECTURE.md: Seções 3, 6 e 8; ADR-001, ADR-002 e ADR-003
- MODELING.md: RF-01 a RF-09, RNF-01 a RNF-08
"""
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.seed import seed_initial_data
from app.routers import auth, dashboard, processos, relatorios

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("jurivision.main")


def init_db_and_seed() -> None:
    """Garante criação de tabelas relacionais e carga idempotente inicial no startup."""
    Base.metadata.create_all(bind=engine)
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


@app.get("/health", tags=["Healthcheck"])
def health_check():
    """Endpoint de verificação de integridade operacional e modo de provedor de IA."""
    return {
        "status": "ok",
        "service": "backend",
        "system": "JuriVision",
        "ai_provider_configured": settings.AI_PROVIDER,
    }
