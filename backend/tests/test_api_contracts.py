"""
Suíte de Verificação Automatizada de Contratos e Regras de Negócio (ISO/IEC/IEEE 29119).
Rastreabilidade Bidirecional (docs/MODELING.md — Seção 7):
- CT-01: RF-01 (Login JWT — 200 OK e 401 Unauthorized)
- CT-02: RF-02 (Upload PDF válido — 200 OK; Arquivo inválido — 422 Unprocessable Entity)
- CT-03: RF-03 (Upload CSV em lote — 200 OK; CSV malformado — 422)
- CT-04: RF-04 e RN-01 (Invariante de Anonimização LGPD de CPF, RG e Nomes de Pessoa Física)
- CT-05: RF-05 e RN-03 (Sumarização NLP via Adapter Local com fallback)
- CT-06: RF-06 e RN-02 (Predição Jurídica com probabilidade em [0.0, 1.0] e perfil de juiz)
- CT-07: RF-07 (Métricas de Jurimetria no Dashboard)
- CT-08: RF-08 (Consulta e Filtragem paginada na Base de Conhecimento)
- CT-09: RF-09 (Exportação de Relatório Estratégico em PDF binário %PDF-1.4)
"""
import io
from fastapi.testclient import TestClient
import pytest

from app.main import app, init_db_and_seed
from app.routers.relatorios import _build_pdf_document


@pytest.fixture(scope="module")
def client() -> TestClient:
    init_db_and_seed()
    with TestClient(app) as test_client:
        yield test_client


def test_ct01_autenticacao_jwt_sucesso_e_falha(client: TestClient):
    """CT-01 (RF-01): Validar emissão de token JWT e rejeição 401 para credenciais incorretas."""
    resp_ok = client.post(
        "/api/v1/auth/login",
        json={"email": "advogado@escritorio.com", "senha": "senhaSegura123"},
    )
    assert resp_ok.status_code == 200
    body = resp_ok.json()
    assert "access_token" in body and len(body["access_token"]) > 20
    assert body["token_type"] == "bearer"
    assert body["usuario"]["nome"] == "Lucas Gabriel"
    assert body["usuario"]["oab"] == "12345/AL"

    resp_fail = client.post(
        "/api/v1/auth/login",
        json={"email": "advogado@escritorio.com", "senha": "senhaIncorreta999"},
    )
    assert resp_fail.status_code == 401


def test_ct02_ct04_ct05_ct06_upload_pdf_barreira_lgpd_e_predicao(client: TestClient):
    """
    CT-02, CT-04, CT-05 e CT-06 (RF-02, RF-04, RF-05, RF-06, RN-01):
    Submete um PDF contendo CPF real, RG real e nome completo de pessoa física.
    Verifica extração, mascaramento total de PII (LGPD), resumo NLP e análise preditiva.
    """
    sample_lines = [
        "EXCELENTISSIMO SENHOR JUIZ DA 1a VARA CIVEL DE MACEIO",
        "Processo: 0077889-11.2026.8.02.0001",
        "Magistrado: Dr. Rafael De Amorim",
        "Autor: Joao Carlos Albuquerque, inscrito no CPF 123.456.789-00 e RG: 12.345.678-9.",
        "Reu: Companhia Aerea Linhas Brasil S.A.",
        "Trata-se de acao de indenizacao por atraso e cancelamento de voo internacional sem assistencia.",
    ]
    pdf_bytes = _build_pdf_document(sample_lines)

    resp = client.post(
        "/api/v1/processos/upload-pdf",
        files={"file": ("peticao_voo_teste.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Verifica contrato de saída (Seção 8.3 de ARCHITECTURE.md)
    assert data["status"] == "PROCESSADO"
    assert data["arquivo_nome"] == "peticao_voo_teste.pdf"
    meta = data["metadados_extraidos"]
    assert meta["numero_processo"] == "0077889-11.2026.8.02.0001"
    assert "Voo" in meta["tema"] or "Dano" in meta["tema"]
    assert meta["magistrado"] == "Dr. Rafael De Amorim"

    # CT-04 (RN-01 / RF-04): Invariante crítico LGPD — zero CPF, RG ou sobrenome completo exposto
    assert "123.456.789-00" not in data["resumo_nlp"]
    assert "12.345.678-9" not in data["resumo_nlp"]
    assert "Albuquerque" not in meta["partes_anonimizadas"]["autor"]
    assert "***" in meta["partes_anonimizadas"]["autor"]
    assert data["auditoria_lgpd"]["texto_higienizado_verificado"] is True
    assert data["auditoria_lgpd"]["total_cpfs_mascarados"] >= 1

    # CT-05 e CT-06 (RF-05 e RF-06): Resumo NLP e Análise Preditiva
    assert len(data["resumo_nlp"]) > 20
    pred = data["analise_preditiva"]
    assert 0.0 <= pred["probabilidade_deferimento"] <= 1.0
    assert pred["tempo_estimado_sentenca_meses"] >= 1
    assert pred["casos_similares_encontrados"] >= 1
    assert len(pred["tese_recomendada"]) > 10
    assert pred["provedor_ia"] == "local_heuristic"


def test_ct02_upload_pdf_invalido_retorna_422(client: TestClient):
    """CT-02 / RN-04: Arquivo corrompido ou com assinatura inválida deve retornar HTTP 422."""
    resp = client.post(
        "/api/v1/processos/upload-pdf",
        files={"file": ("falso.pdf", io.BytesIO(b"Isto nao e um arquivo PDF valido"), "application/pdf")},
    )
    assert resp.status_code == 422
    assert "ErroProcessamento" in resp.json()["detail"]


def test_ct03_upload_csv_em_lote_e_anonimizacao(client: TestClient):
    """CT-03 (RF-03, RF-04): Importação em lote de planilha CSV padronizada com higienização LGPD."""
    csv_content = (
        "numero_processo,tema,magistrado,comarca,autor,reu,texto_resumo,resultado,data_julgamento\n"
        "0099111-22.2026.8.02.0001,Dano Moral,Dr. Rafael De Amorim,1a Vara Civel de Maceio,"
        "Maria Fernanda Costa,Banco Bradesco S.A.,"
        "Cobranca indevida contra CPF 999.888.777-66 de Maria Fernanda Costa,Procedente,2026-10-01\n"
        "0099112-33.2026.8.02.0001,Plano de Saude,Dra. Maria Silva,2a Vara Civel de Maceio,"
        "Carlos Eduardo Lima,Operadora Unimed S.A.,"
        "Negativa indevida de exame de alta complexidade,Acordo,2026-10-10\n"
    ).encode("utf-8")

    resp = client.post(
        "/api/v1/processos/upload-csv",
        files={"file": ("lote_teste.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["lote_status"] == "PROCESSADO"
    assert body["total_registros_lidos"] == 2
    assert body["total_importados_com_sucesso"] == 2
    assert body["total_entidades_anonimizadas_lgpd"] == 2


def test_ct07_dashboard_metricas_jurimetria(client: TestClient):
    """CT-07 (RF-07): Valida contrato e agregações do endpoint GET /api/v1/dashboard/metricas."""
    resp = client.get("/api/v1/dashboard/metricas")
    assert resp.status_code == 200
    body = resp.json()
    assert 0.0 <= body["taxa_exito_global"] <= 1.0
    assert body["tempo_medio_tramitacao_meses"] >= 1
    assert body["total_processos_analisados"] >= 10
    assert len(body["decisoes_por_juiz"]) >= 2
    assert len(body["volume_por_tema"]) >= 2


def test_ct08_consulta_e_filtros_base_conhecimento(client: TestClient):
    """CT-08 (RF-08): Valida busca paginada e filtrada por tema e magistrado com partes anonimizadas."""
    resp = client.get("/api/v1/processos?tema=Dano+Moral&juiz=Rafael&pagina=1&limite=5")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert body["pagina"] == 1
    for item in body["itens"]:
        assert "Dano Moral" in item["tema"]
        assert "Rafael" in item["magistrado"]
        assert "***" in item["partes_anonimizadas"]


def test_ct09_exportacao_relatorio_pdf_binario(client: TestClient):
    """CT-09 (RF-09): Valida exportação de relatório estratégico em PDF válido (%PDF-1.4)."""
    resp = client.get("/api/v1/relatorios/processo/proc-1001/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF-1.4")

    resp_404 = client.get("/api/v1/relatorios/processo/proc-inexistente-999/pdf")
    assert resp_404.status_code == 404
