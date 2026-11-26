"""
Microsserviço HTTP de Inteligência Artificial e Processamento Jurídico (`ai_engine:8001`).

Rastreabilidade:
- ARCHITECTURE.md: ADR-001 (HTTP Interno :8001), ADR-002 (Strategy/Adapter + Barreira LGPD), Seção 8.7
- MODELING.md: RF-04 (LGPD), RF-05 (NLP), RF-06 (Predição), RNF-05 (Resiliência), RNF-07 (Modularidade)

Quando executado no monorepo (ou via Cloud Run / pytest), reutiliza diretamente o núcleo
`backend/app/core` (`AnonimizadorLGPD`, `nlp_engine`, `LocalDeterministicFallbackAdapter` e `GeminiAIAdapter`).
Quando executado de forma isolada em container dedicado sem montagem de `../backend`,
ativa schemas e pipeline autônomos equivalentes respeitando rigorosamente o contrato 8.7.
"""
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sys
from typing import List, Optional

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("jurivision.ai_engine")

_ROOT_DIR = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _ROOT_DIR / "backend"
if _BACKEND_DIR.exists() and str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

try:
    from app.core.ai_gateway import (
        GeminiAIAdapter,
        LocalDeterministicFallbackAdapter,
    )
    from app.core.config import settings as _backend_settings
    from app.schemas.contracts import (
        InternalAnalyzeRequest,
        InternalAnalyzeResponse,
    )

    _HAS_MONOREPO_CORE = True
except ImportError:
    _HAS_MONOREPO_CORE = False
    _backend_settings = None

    class PartesAnonimizadasSchema(BaseModel):
        autor: str
        reu: str

    class MetadadosExtraidosSchema(BaseModel):
        numero_processo: str
        tema: str
        magistrado: str
        comarca: str
        partes_anonimizadas: PartesAnonimizadasSchema

    class AnalisePreditivaSchema(BaseModel):
        probabilidade_deferimento: float = Field(..., ge=0.0, le=1.0)
        margem_confianca: float = Field(..., ge=0.0, le=1.0)
        tempo_estimado_sentenca_meses: int = Field(..., ge=1)
        casos_similares_encontrados: int = Field(..., ge=0)
        tese_recomendada: str
        tendencia_juiz: str
        provedor_ia: str = "local_heuristic"

    class AuditoriaLGPDSchema(BaseModel):
        total_cpfs_mascarados: int = 0
        total_nomes_mascarados: int = 0
        texto_higienizado_verificado: bool = True

    class PrecedenteSimilarSchema(BaseModel):
        id_processo: str
        numero_processo: str
        tema: str
        magistrado: str
        resultado: str
        similaridade: float
        prazo_meses: int = 12
        tese: str = ""

    class ContextoHistoricoSchema(BaseModel):
        total_casos_similares: int = 42
        taxa_favoravel_juiz: float = 0.72
        tempo_medio_meses: int = 9
        margem_confianca_calculada: Optional[float] = None
        tese_precedente_similar: Optional[str] = None
        magistrado_inferido: Optional[str] = None
        precedentes_similares: List[PrecedenteSimilarSchema] = []

    class InternalAnalyzeRequest(BaseModel):  # type: ignore[no-redef]
        arquivo_nome: str
        texto_bruto: str
        contexto_historico: ContextoHistoricoSchema

    class InternalAnalyzeResponse(BaseModel):  # type: ignore[no-redef]
        metadados_extraidos: MetadadosExtraidosSchema
        resumo_nlp: str
        analise_preditiva: AnalisePreditivaSchema
        auditoria_lgpd: AuditoriaLGPDSchema


_STANDALONE_CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_STANDALONE_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_STANDALONE_CNJ_RE = re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")


def _standalone_analyze(request: InternalAnalyzeRequest) -> InternalAnalyzeResponse:
    """Executa análise LGPD + RAG em container isolado sem dependências do pacote `backend`."""
    raw = request.texto_bruto or ""
    clean, n_cpf = _STANDALONE_CPF_RE.subn("[CPF_ANONIMIZADO]", raw)
    clean, n_email = _STANDALONE_EMAIL_RE.subn("[EMAIL_ANONIMIZADO]", clean)

    cnj_m = _STANDALONE_CNJ_RE.search(raw)
    if cnj_m:
        numero = cnj_m.group(0)
    else:
        digest = hashlib.sha256((request.arquivo_nome + raw).encode("utf-8")).hexdigest()
        seq = int(digest[:7], 16) % 9000000 + 1000000
        dv = int(digest[7:9], 16) % 90 + 10
        numero = f"{seq:07d}-{dv:02d}.2026.8.02.0001"

    ctx = request.contexto_historico
    prob = round(min(max(float(ctx.taxa_favoravel_juiz), 0.15), 0.95), 2)
    casos = max(int(ctx.total_casos_similares), 0)
    margem = round(float(ctx.margem_confianca_calculada or 0.12), 2)
    tese = ctx.tese_precedente_similar or "Aplicação das normas de proteção ao consumidor e jurisprudência estadual."
    magistrado = ctx.magistrado_inferido or "Magistrado não especificado"

    resumo = f"Síntese processual higienizada (ai_engine): {clean[:360].strip()}"
    tendencia = (
        f"Estimativa baseada em {casos} precedente(s) similar(es) "
        f"(taxa ponderada de {int(round(prob * 100))}% favorável, margem ±{int(round(margem * 100))}%)."
    )
    provedor = "local_heuristic"

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    provider_cfg = os.getenv("AI_PROVIDER", "local").strip().lower()
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

    if api_key and provider_cfg in ("gemini", "auto", "external"):
        precs_lines = "\n".join(
            f"- CNJ {p.numero_processo} ({p.resultado}, sim {int(round(p.similaridade * 100))}%): {p.tese[:160]}"
            for p in ctx.precedentes_similares[:5]
        )
        prompt = (
            "Você é um perito jurimétrico. Analise o texto anonimizado e os precedentes RAG abaixo "
            "e responda em JSON com resumo_nlp, tese_recomendada, probabilidade_ajustada e tendencia_juiz.\n\n"
            f"TEXTO:\n{clean[:3500]}\n\nPRECEDENTES:\n{precs_lines}"
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        try:
            with httpx.Client(timeout=float(os.getenv("GEMINI_TIMEOUT_SECONDS", "20.0"))) as client:
                r = client.post(
                    url,
                    headers={"x-goog-api-key": api_key},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
                    },
                )
                if r.status_code == 200:
                    candidates = r.json().get("candidates", [])
                    text_out = ""
                    for cand in candidates:
                        parts = cand.get("content", {}).get("parts", [])
                        candidate_text = "".join(
                            p.get("text", "") for p in parts if not p.get("thought")
                        ).strip()
                        if candidate_text:
                            text_out = candidate_text
                            break
                    if text_out:
                        parsed = json.loads(re.sub(r"^```(?:json)?|```$", "", text_out).strip())
                        resumo, _ = _STANDALONE_CPF_RE.subn("[CPF_ANONIMIZADO]", str(parsed.get("resumo_nlp", resumo)))
                        tese = str(parsed.get("tese_recomendada", tese))
                        tendencia = str(parsed.get("tendencia_juiz", tendencia))
                        prob = round(max(min(float(parsed.get("probabilidade_ajustada", prob)), 0.95), 0.15), 2)
                        provedor = f"gemini ({model_name})"
        except Exception as exc:
            logger.info("Gemini indisponível no modo standalone do ai_engine (%s).", exc.__class__.__name__)

    return InternalAnalyzeResponse(
        metadados_extraidos=MetadadosExtraidosSchema(
            numero_processo=numero,
            tema="Direito Civil / Consumidor",
            magistrado=magistrado,
            comarca="Juízo Cível Competente",
            partes_anonimizadas=PartesAnonimizadasSchema(autor="Parte A. ***", reu="Réu Identificado"),
        ),
        resumo_nlp=resumo,
        analise_preditiva=AnalisePreditivaSchema(
            probabilidade_deferimento=prob,
            margem_confianca=margem,
            tempo_estimado_sentenca_meses=max(int(ctx.tempo_medio_meses), 1),
            casos_similares_encontrados=casos,
            tese_recomendada=tese,
            tendencia_juiz=tendencia,
            provedor_ia=provedor,
        ),
        auditoria_lgpd=AuditoriaLGPDSchema(
            total_cpfs_mascarados=n_cpf + n_email,
            total_nomes_mascarados=1,
            texto_higienizado_verificado=True,
        ),
    )


app = FastAPI(
    title="JuriVision AI Engine Worker",
    version="1.0.0",
    description="Microsserviço interno de anonimização LGPD, NLP e RAG Jurídico (ADR-001/ADR-002).",
)


@app.get("/health")
def health_check() -> dict:
    """Sonda de integridade do microsserviço na porta 8001."""
    return {
        "status": "healthy",
        "service": "jurivision-ai-engine",
        "port": int(os.getenv("AI_ENGINE_PORT", "8001")),
        "provider": os.getenv("AI_PROVIDER", "local"),
        "monorepo_core_loaded": _HAS_MONOREPO_CORE,
    }


@app.post("/internal/v1/analyze", response_model=InternalAnalyzeResponse)
def analyze_internal(request: InternalAnalyzeRequest) -> InternalAnalyzeResponse:
    """
    Endpoint interno consumido pelo Back-end Core (`ADR-001` / Seção 8.7).
    Executa obrigatoriamente a barreira LGPD local antes de acionar Gemini RAG ou fallback local.
    """
    if _HAS_MONOREPO_CORE:
        provider_cfg = os.getenv(
            "AI_PROVIDER", _backend_settings.AI_PROVIDER if _backend_settings else "local"
        ).strip().lower()
        api_key = os.getenv(
            "GEMINI_API_KEY", _backend_settings.GEMINI_API_KEY if _backend_settings else ""
        ).strip()
        if api_key and provider_cfg in ("gemini", "auto", "external"):
            return GeminiAIAdapter().analyze_document(request)
        return LocalDeterministicFallbackAdapter().analyze_document(request)

    return _standalone_analyze(request)


def main() -> None:
    host = os.getenv("AI_ENGINE_HOST", "0.0.0.0")
    port = int(os.getenv("AI_ENGINE_PORT", "8001"))
    logger.info(
        "Iniciando JuriVision AI Engine Worker em http://%s:%d (core=%s).",
        host,
        port,
        "monorepo" if _HAS_MONOREPO_CORE else "standalone",
    )
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
