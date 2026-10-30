"""
Ponto de entrada estrutural da API Core (FastAPI).
Scaffolding inicial (Sprint 1, Passo 0).
Sem rotas de negócio, autenticação ou persistência nesta etapa.
"""
from fastapi import FastAPI

app = FastAPI(
    title="Plataforma Jurimetria - API Core",
    version="0.1.0",
    description="API Gateway e serviços de negócio (Scaffolding Inicial)",
)

@app.get("/health", tags=["Healthcheck"])
def health_check():
    """Endpoint estritamente estrutural para verificação de saúde da aplicação."""
    return {"status": "ok", "service": "backend"}
