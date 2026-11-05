"""
Configuração centralizada da API Core (JuriVision).
Rastreabilidade:
- EAP: 1.3.1 Armazenamento / 1.3.2 API REST
- Requisitos: RNF-06 (Segurança), RNF-07 (Modularidade), RNF-08 (Portabilidade)
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Parâmetros de configuração carregados do ambiente com valores seguros de desenvolvimento."""

    APP_NAME: str = "JuriVision - API Core"
    APP_VERSION: str = "1.0.0"

    # Banco de Dados Relacional (ADR-003)
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "jurimetria_dev")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "change_me_locally")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "jurimetria")
    DATABASE_URL_OVERRIDE: str = os.getenv("DATABASE_URL", "")

    # Segurança e Autenticação JWT (RF-01 / ISO 27001)
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change_me_jwt_secret_local_jurivision_2026")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = int(os.getenv("JWT_EXPIRATION_MINUTES", "480"))

    # Isolamento do Motor de IA (ADR-001 / ADR-002)
    AI_ENGINE_URL: str = os.getenv("AI_ENGINE_URL", "http://ai_engine:8001")
    AI_ENGINE_TIMEOUT_SECONDS: float = float(os.getenv("AI_ENGINE_TIMEOUT_SECONDS", "2.5"))
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "local")

    @property
    def postgres_url(self) -> str:
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
