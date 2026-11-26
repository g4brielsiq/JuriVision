"""
Testes Exaustivos da Etapa 5:
- RAG Jurídico com Gemini (injeção de precedentes reais do banco e métricas estatísticas)
- Cache SHA-256 no GeminiAIAdapter
- Sintetizador local de tendência citando precedentes similares (CNJ)
- Microsserviço HTTP ai_engine:8001 (/health e /internal/v1/analyze) + ResilientAIGateway external
- ExtratorDocumental para operadores TJ em array e streams FlateDecode comprimidos
- Fluxo E2E POST /api/v1/processos/upload-pdf com RAG Gemini e barreira LGPD
"""
from dataclasses import replace
import io
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch
import zlib

from fastapi.testclient import TestClient
import httpx
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai_engine.worker import app as ai_engine_app  # noqa: E402
import app.core.ai_gateway as gateway_mod  # noqa: E402
from app.core.ai_gateway import (  # noqa: E402
    ExtratorDocumental,
    GeminiAIAdapter,
    LocalDeterministicFallbackAdapter,
    ResilientAIGateway,
)
from app.core.config import settings  # noqa: E402
from app.main import app, init_db_and_seed  # noqa: E402
from app.routers.relatorios import _build_pdf_document  # noqa: E402
from app.schemas.contracts import (  # noqa: E402
    ContextoHistoricoSchema,
    InternalAnalyzeRequest,
    PrecedenteSimilarSchema,
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    init_db_and_seed()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_gemini_rag_cache():
    GeminiAIAdapter.clear_cache()
    yield
    GeminiAIAdapter.clear_cache()


def _sample_precedents() -> list[PrecedenteSimilarSchema]:
    return [
        PrecedenteSimilarSchema(
            id_processo="proc-rag-1",
            numero_processo="0710802-55.2018.8.02.0001",
            tema="Atraso de Voo / Indenização",
            magistrado="Dr. Rafael De Amorim",
            resultado="Procedente",
            similaridade=0.89,
            prazo_meses=7,
            tese="Responsabilidade objetiva da transportadora aérea (art. 14 CDC e Resolução 400 ANAC).",
        ),
        PrecedenteSimilarSchema(
            id_processo="proc-rag-2",
            numero_processo="0804321-10.2022.8.02.0001",
            tema="Atraso de Voo / Indenização",
            magistrado="Dr. Rafael De Amorim",
            resultado="Acordo",
            similaridade=0.76,
            prazo_meses=5,
            tese="Dano moral in re ipsa configurado por ausência de assistência material no aeroporto.",
        ),
    ]


def test_etapa5_gemini_rag_injeta_precedentes_reais_no_prompt():
    """Garante que o prompt enviado ao Gemini inclui os precedentes reais (RAG), Wilson e texto higienizado."""
    captured_payloads: list[dict] = []

    def _fake_post(url, json=None, **kwargs):
        captured_payloads.append({"url": url, "json": json})
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    '{"resumo_nlp": "Síntese RAG de cancelamento de voo sem assistência.", '
                                    '"tese_recomendada": "Art. 14 do CDC e Resolução 400/ANAC conforme CNJ 0710802-55.2018.8.02.0001.", '
                                    '"probabilidade_ajustada": 0.86, '
                                    '"tendencia_juiz": "Alta aderência aos precedentes CNJ 0710802-55.2018.8.02.0001 e 0804321-10.2022.8.02.0001."}'
                                )
                            }
                        ]
                    }
                }
            ]
        }
        return mock_res

    req = InternalAnalyzeRequest(
        arquivo_nome="peticao_rag_voo.pdf",
        texto_bruto=(
            "Autor: Carlos Henrique Pontes, CPF 111.222.333-44, e-mail carlos.pontes@exemplo.com.br.\n"
            "Reu: Companhia Aerea Linhas Brasil S.A.\n"
            "Cancelamento injustificado de voo internacional sem reacomodacao ou hospedagem."
        ),
        contexto_historico=ContextoHistoricoSchema(
            total_casos_similares=2,
            taxa_favoravel_juiz=0.84,
            tempo_medio_meses=6,
            margem_confianca_calculada=0.14,
            tese_precedente_similar="Responsabilidade objetiva (art. 14 CDC).",
            magistrado_inferido="Dr. Rafael De Amorim",
            precedentes_similares=_sample_precedents(),
        ),
    )

    custom_settings = replace(settings, GEMINI_API_KEY="fake_rag_key", GEMINI_MODEL="gemini-2.5-flash")
    adapter = GeminiAIAdapter()
    with patch.object(gateway_mod, "settings", custom_settings):
        with patch("httpx.Client.post", side_effect=_fake_post):
            resp = adapter.analyze_document(req)

    assert len(captured_payloads) == 1
    sent_prompt = captured_payloads[0]["json"]["contents"][0]["parts"][0]["text"]

    # Valida injeção RAG dos precedentes reais e métricas estatísticas no prompt
    assert "CONTEXTO JURIMÉTRICO E PRECEDENTES SIMILARES DO ACERVO (RAG)" in sent_prompt
    assert "0710802-55.2018.8.02.0001" in sent_prompt
    assert "0804321-10.2022.8.02.0001" in sent_prompt
    assert "84%" in sent_prompt
    assert "±14%" in sent_prompt

    # Barreira LGPD: nenhum dado pessoal bruto vaza para o Gemini
    assert "111.222.333-44" not in sent_prompt
    assert "carlos.pontes@exemplo.com.br" not in sent_prompt
    assert "Carlos Henrique Pontes" not in sent_prompt
    assert "[CPF_ANONIMIZADO]" in sent_prompt
    assert "[EMAIL_ANONIMIZADO]" in sent_prompt

    assert resp.analise_preditiva.provedor_ia == "gemini (gemini-2.5-flash)"
    assert resp.analise_preditiva.probabilidade_deferimento == 0.86


def test_etapa5_gemini_rag_cache_evita_chamadas_duplicadas():
    """Duas análises idênticas consomem o cache SHA-256 sem repetir chamadas HTTP ao Gemini."""
    fake_reply = MagicMock()
    fake_reply.status_code = 200
    fake_reply.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                '{"resumo_nlp": "Demanda por negativação indevida no Serasa.", '
                                '"tese_recomendada": "Súmula 479 e art. 14 CDC.", '
                                '"probabilidade_ajustada": 0.79, '
                                '"tendencia_juiz": "Favorável conforme precedentes de Dano Moral."}'
                            )
                        }
                    ]
                }
            }
        ]
    }

    req = InternalAnalyzeRequest(
        arquivo_nome="cache_teste.pdf",
        texto_bruto="Ação de indenização por negativação indevida no Serasa sem contratação prévia.",
        contexto_historico=ContextoHistoricoSchema(
            total_casos_similares=1,
            taxa_favoravel_juiz=0.75,
            tempo_medio_meses=8,
            margem_confianca_calculada=0.22,
            precedentes_similares=[_sample_precedents()[0]],
        ),
    )

    custom_settings = replace(settings, GEMINI_API_KEY="fake_cache_key", GEMINI_MODEL="gemini-2.5-flash")
    adapter = GeminiAIAdapter()
    with patch.object(gateway_mod, "settings", custom_settings):
        with patch("httpx.Client.post", return_value=fake_reply) as mock_post:
            res1 = adapter.analyze_document(req)
            res2 = adapter.analyze_document(req)

    assert mock_post.call_count == 1
    assert res1.analise_preditiva.provedor_ia == "gemini (gemini-2.5-flash)"
    assert res2.analise_preditiva.provedor_ia == "gemini (gemini-2.5-flash)"
    assert res1.resumo_nlp == res2.resumo_nlp
    assert res1.analise_preditiva.probabilidade_deferimento == 0.79
    assert res2.analise_preditiva.probabilidade_deferimento == 0.79


def test_etapa5_fallback_local_sintetiza_precedentes_similares():
    """Quando offline/local, o fallback referencia diretamente os CNJs dos precedentes mais similares."""
    adapter = LocalDeterministicFallbackAdapter()
    req = InternalAnalyzeRequest(
        arquivo_nome="local_rag_teste.pdf",
        texto_bruto="Autora: Fernanda Costa Lima. Reclamação por atraso de voo e extravio de bagagem.",
        contexto_historico=ContextoHistoricoSchema(
            total_casos_similares=2,
            taxa_favoravel_juiz=0.81,
            tempo_medio_meses=7,
            margem_confianca_calculada=0.14,
            magistrado_inferido="Dr. Rafael De Amorim",
            precedentes_similares=_sample_precedents(),
        ),
    )

    resp = adapter.analyze_document(req)
    assert resp.analise_preditiva.provedor_ia == "local_heuristic"
    assert "Estimativa baseada em 2 precedente(s) similar(es)" in resp.analise_preditiva.tendencia_juiz
    assert "0710802-55.2018.8.02.0001" in resp.analise_preditiva.tendencia_juiz
    assert "0804321-10.2022.8.02.0001" in resp.analise_preditiva.tendencia_juiz
    assert "89% sim." in resp.analise_preditiva.tendencia_juiz


def test_etapa5_ai_engine_microservice_endpoints_e_integracao_gateway():
    """
    Valida os endpoints HTTP do microsserviço `ai_engine:8001` (/health e /internal/v1/analyze)
    e o roteamento via ResilientAIGateway com AI_PROVIDER='external' + sanitização de saída LGPD.
    """
    ai_client = TestClient(ai_engine_app)

    health_resp = ai_client.get("/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "healthy"
    assert health_data["service"] == "jurivision-ai-engine"
    assert health_data["port"] == 8001

    req = InternalAnalyzeRequest(
        arquivo_nome="microsservico_teste.pdf",
        texto_bruto=(
            "Processo: 0811223-44.2026.8.02.0001\n"
            "Autor: Juliana Tavares Mello, CPF 444.555.666-77.\n"
            "Reu: Operadora Unimed Saude S.A.\n"
            "Negativa indevida de cobertura de cirurgia oncologica urgente."
        ),
        contexto_historico=ContextoHistoricoSchema(
            total_casos_similares=2,
            taxa_favoravel_juiz=0.88,
            tempo_medio_meses=5,
            margem_confianca_calculada=0.11,
            precedentes_similares=_sample_precedents(),
        ),
    )

    direct_resp = ai_client.post("/internal/v1/analyze", json=req.model_dump())
    assert direct_resp.status_code == 200
    direct_body = direct_resp.json()
    assert direct_body["metadados_extraidos"]["tema"] == "Plano de Saúde"
    assert "444.555.666-77" not in direct_body["resumo_nlp"]
    assert "Tavares" not in direct_body["metadados_extraidos"]["partes_anonimizadas"]["autor"]

    original_post = httpx.Client.post
    bridged_calls: list[str] = []

    def _bridge_to_ai_engine(self_client, url, *args, **kwargs):
        url_str = str(url)
        if url_str.startswith("http://ai_engine:8001"):
            bridged_calls.append(url_str)
            inner = ai_client.post("/internal/v1/analyze", json=kwargs.get("json"))
            proxy_res = MagicMock()
            proxy_res.status_code = inner.status_code
            proxy_res.json.return_value = inner.json()
            return proxy_res
        return original_post(self_client, url, *args, **kwargs)

    custom_settings = replace(
        settings,
        AI_PROVIDER="external",
        GEMINI_API_KEY="",
        AI_ENGINE_URL="http://ai_engine:8001",
    )
    gw = ResilientAIGateway()
    with patch.object(gateway_mod, "settings", custom_settings):
        with patch.object(httpx.Client, "post", autospec=True, side_effect=_bridge_to_ai_engine):
            routed_resp = gw.analyze_document(req)

    assert bridged_calls == ["http://ai_engine:8001/internal/v1/analyze"]
    assert routed_resp.metadados_extraidos.tema == "Plano de Saúde"
    assert routed_resp.analise_preditiva.probabilidade_deferimento == 0.88
    assert routed_resp.auditoria_lgpd.texto_higienizado_verificado is True
    assert "444.555.666-77" not in routed_resp.resumo_nlp


def test_etapa5_extrator_documental_operadores_tj_array_e_streams():
    """Valida extração de texto em PDFs sintéticos com array `TJ` e streams `FlateDecode`."""
    pdf_tj_array = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Length 96 >>\nstream\n"
        b"BT /F1 12 Tf 50 750 Td\n"
        b"[(Acao ) -12 (indenizatoria ) (por atraso de voo internacional)] TJ\n"
        b"ET\nendstream\nendobj\n%%EOF"
    )
    extracted_tj = ExtratorDocumental.extract_text_from_pdf_bytes(pdf_tj_array)
    assert "Acao indenizatoria por atraso de voo internacional" in extracted_tj

    compressed_payload = zlib.compress(
        b"BT /F1 12 Tf 50 720 Td (Peticao comprimida em FlateDecode sobre plano de saude urgente) Tj ET"
    )
    pdf_flate = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Filter /FlateDecode >>\nstream\n"
        + compressed_payload
        + b"\nendstream\nendobj\n%%EOF"
    )
    extracted_flate = ExtratorDocumental.extract_text_from_pdf_bytes(pdf_flate)
    assert "Peticao comprimida em FlateDecode sobre plano de saude urgente" in extracted_flate


def test_etapa5_upload_pdf_end_to_end_com_rag_gemini(client: TestClient):
    """
    Fluxo E2E POST /api/v1/processos/upload-pdf:
    Verifica que o backend ranqueia os precedentes reais do banco via TF-IDF/BM25,
    envia-os ao Gemini RAG após a barreira LGPD e persiste a análise retornada.
    """
    captured_prompts: list[str] = []
    original_post = httpx.Client.post

    def _fake_gemini_post(self_client, url, *args, **kwargs):
        if "generativelanguage.googleapis.com" in str(url):
            json_body = kwargs.get("json") or {}
            captured_prompts.append(json_body["contents"][0]["parts"][0]["text"])
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.json.return_value = {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        '{"resumo_nlp": "Síntese RAG E2E de ação aérea por atraso e extravio.", '
                                        '"tese_recomendada": "Aplicação consolidada do art. 14 do CDC e Resolução 400 da ANAC.", '
                                        '"probabilidade_ajustada": 0.91, '
                                        '"tendencia_juiz": "Posicionamento favorável corroborado pelos precedentes do acervo."}'
                                    )
                                }
                            ]
                        }
                    }
                ]
            }
            return mock_res
        return original_post(self_client, url, *args, **kwargs)

    sample_lines = [
        "EXCELENTISSIMO SENHOR JUIZ DA 1a VARA CIVEL DE MACEIO",
        "Processo: 0895511-22.2026.8.02.0001",
        "Magistrado: Dr. Rafael De Amorim",
        "Autor: Beatriz Oliveira Lima, CPF 321.654.987-00, e-mail beatriz.lima@teste.com.",
        "Reu: Companhia Aerea Linhas Brasil S.A.",
        "Acao de indenizacao por atraso de voo internacional e extravio de bagagem sem assistencia.",
    ]
    pdf_bytes = _build_pdf_document(sample_lines)

    custom_settings = replace(
        settings,
        AI_PROVIDER="gemini",
        GEMINI_API_KEY="fake_e2e_rag_key",
        GEMINI_MODEL="gemini-2.5-flash",
    )
    with patch.object(gateway_mod, "settings", custom_settings):
        with patch.object(httpx.Client, "post", autospec=True, side_effect=_fake_gemini_post):
            resp = client.post(
                "/api/v1/processos/upload-pdf",
                files={"file": ("peticao_e2e_rag.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert len(captured_prompts) == 1
    prompt_text = captured_prompts[0]

    assert "CONTEXTO JURIMÉTRICO E PRECEDENTES SIMILARES DO ACERVO (RAG)" in prompt_text
    assert "Top Precedentes Similares Recuperados do Banco:" in prompt_text
    assert "321.654.987-00" not in prompt_text
    assert "beatriz.lima@teste.com" not in prompt_text
    assert "Beatriz Oliveira Lima" not in prompt_text

    assert body["analise_preditiva"]["provedor_ia"] == "gemini (gemini-2.5-flash)"
    assert body["analise_preditiva"]["probabilidade_deferimento"] == 0.91
    assert body["analise_preditiva"]["casos_similares_encontrados"] >= 1
    assert "321.654.987-00" not in body["resumo_nlp"]
    assert "Oliveira" not in body["metadados_extraidos"]["partes_anonimizadas"]["autor"]
