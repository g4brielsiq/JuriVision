"""
Testes Unitários e de Integração: Cliente DataJud (CNJ) e Adaptador Gemini AI Studio.
Rastreabilidade:
- EAP: 1.4.2 (Base de Conhecimento), 1.5.1 (Garantia de Qualidade - ISO 29119)
- Requisitos: RF-08 (Consulta Jurisprudencial), RNF-05 (Tolerância a Falhas), RNF-06 (LGPD), ADR-002
"""
from dataclasses import replace
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

import app.core.ai_gateway as gateway_mod
from app.core.ai_gateway import AnonimizadorLGPD, GeminiAIAdapter, ResilientAIGateway
from app.core.config import settings
from app.core.datajud_client import DataJudClient
from app.main import app
from app.schemas.contracts import ContextoHistoricoSchema, InternalAnalyzeRequest


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# 1. Testes do Cliente DataJud (CNJ)
# ==============================================================================
def test_datajud_alias_resolution():
    """Valida a resolução automática de alias de tribunal via número CNJ."""
    # TJAL (Alagoas - 8.02)
    alias_al = DataJudClient.resolve_alias_tribunal("0710802-55.2018.8.02.0001")
    assert alias_al == "api_publica_tjal"

    # TJSP (São Paulo - 8.26)
    alias_sp = DataJudClient.resolve_alias_tribunal("1001234-56.2020.8.26.0100")
    assert alias_sp == "api_publica_tjsp"

    # Formato genérico ou sem máscara
    alias_padrao = DataJudClient.resolve_alias_tribunal("12345")
    assert alias_padrao == settings.DATAJUD_DEFAULT_ALIAS


def test_datajud_endpoint_com_fallback_local(client):
    """
    Testa o endpoint GET /api/v1/processos/datajud/{numero}.
    Garante que em ambiente de teste ou timeout da API pública,
    o sistema responde com status 200 e aciona o fallback seguro (RNF-05).
    """
    numero = "0710802-55.2018.8.02.0001"
    response = client.get(f"/api/v1/processos/datajud/{numero}")
    assert response.status_code == 200
    data = response.json()

    assert data["numero_processo"] == numero
    assert data["tribunal"] == "TJAL"
    assert "fonte" in data
    assert data["fonte"] in ("datajud_api", "local_cache_fallback")
    assert "mensagem" in data
    assert len(data["assuntos"]) >= 1


def test_datajud_parsing_source():
    """Testa a transformação de payload bruto do Elasticsearch para o schema interno."""
    mock_source = {
        "numeroProcesso": "0800123-45.2023.8.02.0001",
        "tribunal": "TJAL",
        "classe": {"codigo": 7, "nome": "Procedimento do Juizado Especial Cível"},
        "orgaoJulgador": {"codigo": 12, "nome": "2º Juizado Cível de Maceió"},
        "assuntos": [
            {"codigo": 10433, "nome": "Indenização por Dano Moral", "principal": True}
        ],
        "movimentos": [
            {"codigo": 60, "nome": "Expedição de Termo", "dataHora": "2023-06-01T10:00:00"}
        ],
        "dataAjuizamento": "2023-01-10T08:00:00.000Z",
        "grau": "G1",
    }

    parsed = DataJudClient._parse_datajud_source(mock_source, "0800123-45.2023.8.02.0001")
    assert parsed.numero_processo == "0800123-45.2023.8.02.0001"
    assert parsed.classe == "Procedimento do Juizado Especial Cível"
    assert parsed.assunto_principal == "Indenização por Dano Moral"
    assert parsed.orgao_julgador == "2º Juizado Cível de Maceió"
    assert parsed.fonte == "datajud_api"
    assert parsed.sucesso is True


# ==============================================================================
# 2. Testes do Adaptador Gemini AI (Google AI Studio)
# ==============================================================================
def test_gemini_adapter_fallback_sem_chave():
    """Garante que sem chave de API o adaptador aciona fallback local imediatamente."""
    custom_settings = replace(settings, GEMINI_API_KEY="")
    with patch.object(gateway_mod, "settings", custom_settings):
        adapter = GeminiAIAdapter()
        req = InternalAnalyzeRequest(
            arquivo_nome="peticao_teste.pdf",
            texto_bruto="Autor: João Carlos da Silva (CPF: 123.456.789-00) contra Banco S.A.",
            contexto_historico=ContextoHistoricoSchema(),
        )
        res = adapter.analyze_document(req)
        assert res.analise_preditiva.provedor_ia == "local_heuristic"
        # Garante que a barreira LGPD funcionou no fallback
        assert "123.456.789-00" not in res.resumo_nlp


def test_gemini_adapter_com_mock_sucesso():
    """Simula resposta 200 da API do Gemini e valida sanitização de saída."""
    adapter = GeminiAIAdapter()
    req = InternalAnalyzeRequest(
        arquivo_nome="peticao_teste.pdf",
        texto_bruto="Autor: Maria Ferreira (CPF: 987.654.321-99) em face de Companhia Aérea Linhas Brasil S.A. Cancelamento de voo e perda de conexão.",
        contexto_historico=ContextoHistoricoSchema(),
    )

    fake_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                '{"resumo_nlp": "Ação indenizatória por cancelamento de voo sem assistência material.", '
                                '"tese_recomendada": "Art. 14 do CDC e responsabilidade objetiva da transportadora.", '
                                '"probabilidade_ajustada": 0.88, '
                                '"tendencia_juiz": "Jurisprudência amplamente favorável no TJAL para falha de serviço aéreo."}'
                            )
                        }
                    ]
                }
            }
        ]
    }

    mock_http_response = MagicMock()
    mock_http_response.status_code = 200
    mock_http_response.json.return_value = fake_gemini_response

    custom_settings = replace(settings, GEMINI_API_KEY="fake_test_key_ai_studio")
    with patch.object(gateway_mod, "settings", custom_settings):
        with patch("httpx.Client.post", return_value=mock_http_response):
            res = adapter.analyze_document(req)
            assert "gemini" in res.analise_preditiva.provedor_ia
            assert res.analise_preditiva.probabilidade_deferimento == 0.88
            assert "Art. 14 do CDC" in res.analise_preditiva.tese_recomendada
            assert "987.654.321-99" not in res.resumo_nlp


def test_gemini_adapter_resiliencia_em_falha_de_rede():
    """Garante que qualquer erro de conexão ou timeout do Gemini cai no fallback local seguro."""
    adapter = GeminiAIAdapter()
    req = InternalAnalyzeRequest(
        arquivo_nome="peticao_offline.pdf",
        texto_bruto="Ação trabalhista contra Empresa LTDA.",
        contexto_historico=ContextoHistoricoSchema(),
    )

    custom_settings = replace(settings, GEMINI_API_KEY="fake_test_key")
    with patch.object(gateway_mod, "settings", custom_settings):
        with patch("httpx.Client.post", side_effect=Exception("Timeout simulado da API externa")):
            res = adapter.analyze_document(req)
            # Sistema não quebra e retorna resposta válida do motor determinístico
            assert res.analise_preditiva.provedor_ia == "local_heuristic"
            assert res.metadados_extraidos.tema == "Direito Trabalhista"


def test_datajud_fallback_cnj_sem_mascara(client):
    """Garante que a busca por CNJ com 20 dígitos contínuos (sem máscara) localiza o processo no acervo."""
    # Processo cadastrado no seed com máscara: 0019283-44.2025.8.02.0001
    numero_sem_mascara = "00192834420258020001"
    response = client.get(f"/api/v1/processos/datajud/{numero_sem_mascara}")
    assert response.status_code == 200
    data = response.json()
    assert data["numero_processo"] == "0019283-44.2025.8.02.0001"
    assert data["sucesso"] is True


def test_gemini_adapter_com_markdown_codeblock():
    """Garante que respostas do Gemini envelopadas em markdown (```json ... ```) são tratadas defensivamente."""
    adapter = GeminiAIAdapter()
    req = InternalAnalyzeRequest(
        arquivo_nome="peticao_teste.pdf",
        texto_bruto="Ação de cobrança indevida de telefonia.",
        contexto_historico=ContextoHistoricoSchema(),
    )

    markdown_gemini_reply = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                "```json\n"
                                "{\n"
                                '  "resumo_nlp": "Cobrança de serviço de telefonia não contratado.",\n'
                                '  "tese_recomendada": "Repetição de indébito em dobro e art. 42 do CDC.",\n'
                                '  "probabilidade_ajustada": 0.82,\n'
                                '  "tendencia_juiz": "Jurisprudência dominante pelo cancelamento de débito."\n'
                                "}\n"
                                "```"
                            )
                        }
                    ]
                }
            }
        ]
    }

    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = markdown_gemini_reply

    custom_settings = replace(settings, GEMINI_API_KEY="test_key_markdown")
    with patch.object(gateway_mod, "settings", custom_settings):
        with patch("httpx.Client.post", return_value=mock_res):
            res = adapter.analyze_document(req)
            assert "gemini" in res.analise_preditiva.provedor_ia
            assert res.analise_preditiva.probabilidade_deferimento == 0.82
            assert "art. 42 do CDC" in res.analise_preditiva.tese_recomendada
