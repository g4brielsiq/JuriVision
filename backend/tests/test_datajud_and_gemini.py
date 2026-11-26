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


def test_datajud_endpoint_sem_resposta_do_cnj_nao_inventa_dados(client):
    """
    Se a API Pública não responder e o número não estiver no acervo, a consulta informa a falha
    (sucesso=False) e não completa classe, assunto ou movimentações com valores presumidos.
    """
    numero = "0710802-55.2018.8.02.0001"
    with patch("httpx.AsyncClient.post", side_effect=Exception("offline")):
        response = client.get(f"/api/v1/processos/datajud/{numero}")
    assert response.status_code == 200
    data = response.json()
    assert data["numero_processo"] == numero
    assert data["tribunal"] == "TJAL"
    assert data["fonte"] == "indisponivel"
    assert data["sucesso"] is False
    assert data["assuntos"] == []
    assert data["movimentos_recentes"] == []
    assert data["classe"] == "Não informado pelo DataJud"
    assert "Tente novamente" in data["mensagem"]


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
    """Com o DataJud fora do ar, o CNJ sem máscara localiza o processo no acervo e mostra só os dados do acervo."""
    # Processo cadastrado no seed com máscara: 0019283-44.2025.8.02.0001
    numero_sem_mascara = "00192834420258020001"
    with patch("httpx.AsyncClient.post", side_effect=Exception("offline")):
        response = client.get(f"/api/v1/processos/datajud/{numero_sem_mascara}")
    assert response.status_code == 200
    data = response.json()
    assert data["numero_processo"] == "0019283-44.2025.8.02.0001"
    assert data["sucesso"] is True
    assert data["fonte"] == "acervo_local"
    assert data["movimentos_recentes"] == []


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


# ==============================================================================
# 3. Testes de Coleta Automática em Lote e Sincronização DataJud (Card #27)
# ==============================================================================
def test_datajud_sincronizacao_offline_nao_grava_nada(client):
    """Sem resposta do CNJ a sincronização devolve 503 e não insere nenhum processo no acervo."""
    total_antes = client.get("/api/v1/processos?limite=1").json()["total"]
    with patch("httpx.AsyncClient.post", side_effect=Exception("Simulando modo offline")):
        res = client.post("/api/v1/processos/datajud/sincronizar", json={"tribunal": "TJAL", "limite": 2})
    assert res.status_code == 503
    assert "Nenhum processo foi gravado" in res.json()["detail"]
    assert client.get("/api/v1/processos?limite=1").json()["total"] == total_antes


@pytest.mark.parametrize(
    "status_code, trecho",
    [(401, "chave de acesso"), (429, "sobrecarregada"), (500, "HTTP 500")],
)
def test_datajud_sincronizacao_explica_erro_http(client, status_code, trecho):
    resposta = MagicMock()
    resposta.status_code = status_code
    with patch("httpx.AsyncClient.post", return_value=resposta), patch("asyncio.sleep"):
        res = client.post("/api/v1/processos/datajud/sincronizar", json={"tribunal": "TJAL", "limite": 1})
    assert res.status_code == 503
    assert trecho in res.json()["detail"]


def test_datajud_sincronizacao_idempotente_com_api(client):
    """A segunda coleta do mesmo lote atualiza os registros em vez de duplicar."""
    lote = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "numeroProcesso": "07000014020248020001",
                        "classe": {"codigo": 7, "nome": "Procedimento Comum Cível"},
                        "orgaoJulgador": {"nome": "5ª Vara Cível da Capital"},
                        "assuntos": [{"codigo": 7779, "nome": "Indenização por Dano Moral", "principal": True}],
                        "movimentos": [{"codigo": 220, "nome": "Improcedência", "dataHora": "2025-02-03T10:00:00"}],
                    }
                }
            ]
        }
    }
    resposta = MagicMock()
    resposta.status_code = 200
    resposta.json.return_value = lote
    with patch("httpx.AsyncClient.post", return_value=resposta):
        body1 = client.post("/api/v1/processos/datajud/sincronizar", json={"tribunal": "TJAL", "limite": 1}).json()
        body2 = client.post("/api/v1/processos/datajud/sincronizar", json={"tribunal": "TJAL", "limite": 1}).json()
    assert (body1["novos_inseridos"], body1["atualizados"]) == (1, 0)
    assert (body2["novos_inseridos"], body2["atualizados"]) == (0, 1)
    assert body2["itens"][0]["resultado"] == "Improcedente"


def test_datajud_sem_desfecho_fica_em_analise():
    """Processo sem movimento de decisão de mérito ou acordo não recebe desfecho presumido."""
    parsed = DataJudClient._parse_datajud_source(
        {
            "numeroProcesso": "07000014020248020001",
            "movimentos": [{"codigo": 51, "nome": "Conclusão", "dataHora": "2025-01-10T10:00:00"}],
        },
        "07000014020248020001",
    )
    assert parsed.desfecho is None
    assert parsed.classe == "Não informado pelo DataJud"
    assert parsed.assunto_principal == "Não informado pelo DataJud"
    assert parsed.orgao_julgador == "Não informado pelo DataJud"
    registro = DataJudClient.extrair_registro_para_acervo(parsed)
    assert registro["resultado"] == "Em Analise"
    assert registro["data_julgamento"] is None


def test_cnj_digito_verificador():
    assert DataJudClient.cnj_digito_verificador_valido("0710802-55.2018.8.02.0001")
    assert not DataJudClient.cnj_digito_verificador_valido("0804110-12.2026.8.02.0001")


def test_datajud_coleta_lote_com_mock_api_externa(client):
    """
    Simula retorno HTTP 200 da API Pública do DataJud (Elasticsearch DSL) em lote,
    verificando normalização do CNJ de 20 dígitos, inferência de desfecho e persistência.
    """
    fake_es_batch = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "numeroProcesso": "08099887720268020001",
                        "tribunal": "TJAL",
                        "classe": {"codigo": 436, "nome": "Procedimento do Juizado Especial Cível"},
                        "orgaoJulgador": {"codigo": 12, "nome": "2º Juizado Especial Cível de Maceió"},
                        "assuntos": [
                            {"codigo": 4829, "nome": "Atraso de Voo / Transporte Aéreo", "principal": True}
                        ],
                        "movimentos": [
                            {
                                "codigo": 219,
                                "nome": "Julgado Procedente o Pedido",
                                "dataHora": "2026-10-15T14:00:00",
                            }
                        ],
                        "dataAjuizamento": "2026-04-01T09:00:00.000Z",
                        "grau": "G1",
                    }
                }
            ]
        }
    }

    mock_http_res = MagicMock()
    mock_http_res.status_code = 200
    mock_http_res.json.return_value = fake_es_batch

    with patch("httpx.AsyncClient.post", return_value=mock_http_res):
        res = client.post(
            "/api/v1/processos/datajud/sincronizar",
            json={"tribunal": "TJAL", "tema": "Atraso de Voo", "limite": 1},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["fonte"] == "datajud_api"
        assert data["total_coletados"] == 1
        assert data["novos_inseridos"] == 1
        item = data["itens"][0]
        assert item["numero_processo"] == "0809988-77.2026.8.02.0001"
        assert item["tema"] == "Atraso de Voo"
        assert item["resultado"] == "Procedente"
        # A API Pública não publica partes nem magistrado: nada disso pode ser inventado
        assert item["magistrado"] == "Não informado pelo DataJud"
        assert "Não informado pelo DataJud" in item["partes_anonimizadas"]
        assert "***" not in item["partes_anonimizadas"]
        assert item["data_julgamento"] == "2026-10-15"
