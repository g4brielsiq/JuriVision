"""
Gerenciamento de conexão e sessão ORM (SQLAlchemy 2.0).
Rastreabilidade:
- EAP: 1.3.1 Armazenamento
- ADR-003: Centralização da Persistência Relacional no Back-end (API Core)
- RNF-05 / RNF-08: Resiliência e Portabilidade entre Docker (PostgreSQL 16) e execução local/testes.
"""
import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger("jurivision.database")


class Base(DeclarativeBase):
    """Classe base declarativa para todas as entidades ORM do JuriVision."""
    pass


def _build_engine():
    """
    Inicializa a engine relacional priorizando PostgreSQL 16 (ADR-003).
    Caso executado fora da rede Docker sem servidor PostgreSQL ativo (ex.: suíte de testes locais),
    opera com fallback resiliente em SQLite local para garantir portabilidade e verificabilidade (ISO 29119).
    """
    primary_url = settings.postgres_url
    if primary_url.startswith("sqlite"):
        return create_engine(primary_url, connect_args={"check_same_thread": False})

    try:
        pg_engine = create_engine(
            primary_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 3},
        )
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Conectado com sucesso ao PostgreSQL em %s:%s", settings.POSTGRES_HOST, settings.POSTGRES_PORT)
        return pg_engine
    except Exception as exc:
        fallback_url = "sqlite:///./jurivision_local.sqlite3"
        logger.warning(
            "PostgreSQL indisponível no host '%s' (%s). Acionando banco relacional local SQLite (%s) para continuidade operacional.",
            settings.POSTGRES_HOST,
            exc.__class__.__name__,
            fallback_url,
        )
        return create_engine(fallback_url, connect_args={"check_same_thread": False})


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependência FastAPI para fornecimento de sessão transacional por requisição."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
