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
from uuid import uuid4
from fastapi.testclient import TestClient
import pytest

from app.core.database import SessionLocal
from app.main import app, init_db_and_seed
from app.models.entities import Usuario
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


def test_cadastro_advogado_persiste_conta_e_permite_login(client: TestClient):
    registro = uuid4()
    email = f"advogada-{registro.hex}@example.com"
    oab = f"{registro.int}/AL"
    senha = "Senha de teste 123"
    payload = {
        "nome": "  Ana Pereira  ",
        "email": f" {email.upper()} ",
        "senha": senha,
        "numero_oab": f" {registro.int} / al ",
    }
    cadastro = client.post("/api/v1/auth/register", json=payload)
    assert cadastro.status_code == 201
    usuario = cadastro.json()
    assert usuario == {"id": usuario["id"], "nome": "Ana Pereira", "email": email, "oab": oab}

    with SessionLocal() as db:
        assert db.get(Usuario, usuario["id"]).senha_hash != senha

    login = client.post("/api/v1/auth/login", json={"email": email, "senha": senha})
    assert login.status_code == 200
    assert login.json()["access_token"]
    assert login.json()["usuario"]["id"] == usuario["id"]

    email_repetido = client.post("/api/v1/auth/register", json={**payload, "numero_oab": "77777/AL"})
    assert email_repetido.status_code == 409
    assert email_repetido.json()["detail"] == "E-mail já cadastrado."

    oab_repetida = client.post("/api/v1/auth/register", json={**payload, "email": f"outra-{email}"})
    assert oab_repetida.status_code == 409
    assert oab_repetida.json()["detail"] == "Número OAB já cadastrado."


def test_cadastro_advogado_valida_campos_sem_expor_senha(client: TestClient):
    senha_invalida = "abc1234"
    cadastro = client.post(
        "/api/v1/auth/register",
        json={"nome": "   ", "email": "sem-arroba", "senha": senha_invalida, "numero_oab": "12345/XX"},
    )
    assert cadastro.status_code == 422
    assert {erro["loc"][-1] for erro in cadastro.json()["detail"]} == {"nome", "email", "senha", "numero_oab"}
    assert senha_invalida not in cadastro.text


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


def test_ct02_upload_pdf_acima_limite_15mb_retorna_413(client: TestClient):
    """CT-02 / RN-04 / SEC-05: Upload de PDF superior a 15MB deve retornar HTTP 413 (Payload Too Large)."""
    oversized_bytes = b"%PDF-1.4\n" + b"0" * (15 * 1024 * 1024)
    resp = client.post(
        "/api/v1/processos/upload-pdf",
        files={"file": ("arquivo_gigante.pdf", io.BytesIO(oversized_bytes), "application/pdf")},
    )
    assert resp.status_code == 413
    assert "15MB" in resp.json()["detail"]


def test_ct03_upload_csv_acima_limite_10mb_retorna_413(client: TestClient):
    """CT-03 / RN-04 / SEC-05: Upload de CSV superior a 10MB deve retornar HTTP 413 (Payload Too Large)."""
    oversized_bytes = b"col1,col2\n" + b"x" * (10 * 1024 * 1024)
    resp = client.post(
        "/api/v1/processos/upload-csv",
        files={"file": ("planilha_gigante.csv", io.BytesIO(oversized_bytes), "text/csv")},
    )
    assert resp.status_code == 413
    assert "10MB" in resp.json()["detail"]


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


def test_ct07_dashboard_filtros_e_distribuicao_resultados(client: TestClient):
    """CT-07b (RF-07): Valida quebra por desfecho, métricas por tema e filtros dinâmicos no dashboard."""
    resp_full = client.get("/api/v1/dashboard/metricas")
    assert resp_full.status_code == 200
    full_body = resp_full.json()

    dist = full_body["distribuicao_resultados"]
    soma_dist = dist["procedentes"] + dist["acordos"] + dist["improcedentes"] + dist["em_analise"]
    assert soma_dist == full_body["total_processos_analisados"]
    assert dist["procedentes"] >= 1
    assert dist["acordos"] >= 1
    assert dist["improcedentes"] >= 1

    for tema_item in full_body["volume_por_tema"]:
        assert tema_item["total"] >= 1
        assert 0.0 <= tema_item["taxa_favoravel"] <= 100.0
        assert tema_item["tempo_medio_meses"] >= 1

    # Metodologia: a taxa favorável usa só decisões com desfecho; "Em análise" fica fora do denominador.
    decididos = dist["procedentes"] + dist["acordos"] + dist["improcedentes"]
    assert full_body["total_decididos"] == decididos
    assert full_body["taxa_exito_global"] == pytest.approx(
        round((dist["procedentes"] + dist["acordos"]) / decididos, 3)
    )
    soma_juizes = sum(j["procedentes"] + j["improcedentes"] for j in full_body["decisoes_por_juiz"])
    assert soma_juizes == decididos
    for tema_item in full_body["volume_por_tema"]:
        assert tema_item["favoraveis"] <= tema_item["decididos"] <= tema_item["total"]

    recorte = full_body["recorte"]
    assert recorte["total_orgaos_julgadores"] >= 1
    assert 1 <= len(recorte["orgaos_julgadores"]) <= 5
    assert recorte["ano_inicial"] is None or recorte["ano_inicial"] <= recorte["ano_final"]

    resp_tema = client.get("/api/v1/dashboard/metricas?tema=Dano+Moral")
    assert resp_tema.status_code == 200
    tema_body = resp_tema.json()
    assert 1 <= tema_body["total_processos_analisados"] < full_body["total_processos_analisados"]
    assert all("Dano Moral" in item["tema"] for item in tema_body["volume_por_tema"])

    resp_juiz = client.get("/api/v1/dashboard/metricas?juiz=Rafael")
    assert resp_juiz.status_code == 200
    juiz_body = resp_juiz.json()
    assert 1 <= juiz_body["total_processos_analisados"] < full_body["total_processos_analisados"]
    assert all("Rafael" in item["juiz"] for item in juiz_body["decisoes_por_juiz"])


def test_ct07c_dashboard_vazio_retorna_recorte_sem_valores_fixos(client: TestClient):
    """CT-07c: Recorte inexistente não inventa órgão julgador nem período."""
    resp = client.get("/api/v1/dashboard/metricas?tema=Tema+Inexistente+XYZ")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_processos_analisados"] == 0
    assert body["total_decididos"] == 0
    assert body["recorte"] == {
        "orgaos_julgadores": [],
        "total_orgaos_julgadores": 0,
        "ano_inicial": None,
        "ano_final": None,
    }


def test_seed_demo_desligado_por_padrao(monkeypatch: pytest.MonkeyPatch):
    """Dados fictícios são opt-in: sem SEED_DEMO_DATA a base inicia vazia."""
    import importlib.util

    import dotenv

    import app.core.config as config_mod
    import app.main as main_mod

    monkeypatch.delenv("SEED_DEMO_DATA", raising=False)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    spec = importlib.util.spec_from_file_location("config_isolado", config_mod.__file__)
    config_isolado = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_isolado)
    assert config_isolado.Settings().SEED_DEMO_DATA is False

    chamadas = []
    monkeypatch.setattr(main_mod, "seed_initial_data", lambda db: chamadas.append(db))
    main_mod.init_db_and_seed()
    assert chamadas == []
    main_mod.init_db_and_seed(seed_demo=True)
    assert len(chamadas) == 1


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


def test_ct01_perfil_autenticado_e_rejeicao_token_invalido(client: TestClient):
    """Valida GET /api/v1/auth/me com token válido e rejeição HTTP 401 para tokens inválidos nas rotas."""
    sem_token = client.get("/api/v1/auth/me")
    assert sem_token.status_code == 401

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "advogado@escritorio.com", "senha": "senhaSegura123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    perfil = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert perfil.status_code == 200
    assert perfil.json()["email"] == "advogado@escritorio.com"

    token_invalido = client.get(
        "/api/v1/processos",
        headers={"Authorization": "Bearer token-forjado-invalido"},
    )
    assert token_invalido.status_code == 401


def test_ct08_filtros_comarca_e_tribunal(client: TestClient):
    """Valida filtragem explícita por comarca e tribunal em GET /api/v1/processos."""
    resp_tjal = client.get("/api/v1/processos?comarca=Maceió&tribunal=TJAL")
    assert resp_tjal.status_code == 200
    body_tjal = resp_tjal.json()
    assert body_tjal["total"] >= 1
    for item in body_tjal["itens"]:
        assert "Macei" in item["comarca"]

    resp_outro = client.get("/api/v1/processos?tribunal=TJSP")
    assert resp_outro.status_code == 200
    assert resp_outro.json()["total"] == 0


def test_ct06_processos_similares_reais_sem_multiplicador_artificial(client: TestClient):
    """Valida GET /api/v1/processos/{id}/similares retornando precedentes reais existentes no banco."""
    resp = client.get("/api/v1/processos/proc-1001/similares?limite=50")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == len(body["itens"])
    assert body["total"] >= 1
    assert all(item["id_processo"] != "proc-1001" for item in body["itens"])

    resp_404 = client.get("/api/v1/processos/proc-inexistente-999/similares")
    assert resp_404.status_code == 404
