"""
Testes Exaustivos da Etapa 6:
- Modelo Freemium (FREE vs PRO) persistido no banco (Usuario.plano / Usuario.analises_realizadas)
- Endpoints GET /api/v1/auth/plano e POST /api/v1/auth/plano/upgrade
- Bloqueio HTTP 402 Payment Required na 4a análise PDF no plano FREE e no upload CSV em lote
- Desbloqueio completo após upgrade para PRO (Cortesia CONAD2026)
- Usuário institucional padrão (usr-01) no plano PRO
- Integração Front-end Freemium e artefatos de deploy Cloud (Dockerfile / render.yaml)
"""
import io
from pathlib import Path
from typing import Iterator
import uuid

from fastapi.testclient import TestClient
import pytest

from app.core.database import SessionLocal
from app.main import app, init_db_and_seed
from app.models.entities import Processo, Usuario
from app.routers.relatorios import _build_pdf_document

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    init_db_and_seed()
    with TestClient(app) as test_client:
        yield test_client


def _cnj_unico() -> str:
    seq = uuid.uuid4().int % 10_000_000
    dv = uuid.uuid4().int % 100
    return f"{seq:07d}-{dv:02d}.2026.8.02.0001"


def _registrar_e_logar(client: TestClient, prefixo: str) -> tuple[dict, str]:
    uid = uuid.uuid4()
    email = f"{prefixo.lower()}-{uid.hex[:10]}@example.com"
    oab = f"{(uid.int % 899_999) + 100_000}/AL"
    senha = "SenhaFreemium2026!"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "nome": f"{prefixo} Advogado",
            "email": email,
            "senha": senha,
            "numero_oab": oab,
        },
    )
    assert reg.status_code == 201, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "senha": senha})
    assert login.status_code == 200, login.text
    return reg.json(), login.json()["access_token"]


def _pdf_peticao_unica(cnj: str) -> bytes:
    return _build_pdf_document(
        [
            "EXCELENTISSIMO SENHOR JUIZ DA 1a VARA CIVEL DE MACEIO",
            f"Processo: {cnj}",
            "Magistrado: Dr. Rafael De Amorim",
            "Autor: Rodrigo Barbosa Almeida, CPF 555.666.777-88.",
            "Reu: Companhia Aerea Linhas Brasil S.A.",
            "Acao de indenizacao por atraso de voo e ausencia de assistencia material.",
        ]
    )


def _limpar_dados_teste(proc_ids: list[str], cnjs: list[str], user_ids: list[str]) -> None:
    with SessionLocal() as db:
        for pid in proc_ids:
            proc = db.query(Processo).filter(Processo.id_processo == pid).first()
            if proc:
                db.delete(proc)
        for cnj in cnjs:
            proc = db.query(Processo).filter(Processo.numero_processo == cnj).first()
            if proc:
                db.delete(proc)
        db.flush()
        for uid in user_ids:
            usr = db.query(Usuario).filter(Usuario.id == uid).first()
            if usr:
                db.delete(usr)
        db.commit()


def test_etapa6_novo_advogado_inicia_no_plano_free_e_consulta_status(client: TestClient):
    """Advogado recém-cadastrado inicia no plano FREE com cota zerada e recursos PRO bloqueados."""
    usuario, token = _registrar_e_logar(client, "FreeStart")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = client.get("/api/v1/auth/plano", headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["usuario_id"] == usuario["id"]
        assert data["plano"] == "FREE"
        assert data["analises_realizadas"] == 0
        assert data["limite_analises_free"] == 3
        assert data["analises_restantes"] == 3
        assert data["recursos_pro_liberados"] is False
        assert data["lote_csv_liberado"] is False
        assert data["tese_aprofundada_liberada"] is False
    finally:
        _limpar_dados_teste([], [], [usuario["id"]])


def test_etapa6_cota_free_permite_3_pdfs_e_bloqueia_quarto_com_402(client: TestClient):
    """Usuário FREE consegue enviar até 3 PDFs e é bloqueado com HTTP 402 no 4o envio."""
    usuario, token = _registrar_e_logar(client, "FreeQuota")
    headers = {"Authorization": f"Bearer {token}"}
    created_ids: list[str] = []

    try:
        for expected_used in range(1, 4):
            pdf_bytes = _pdf_peticao_unica(_cnj_unico())
            up = client.post(
                "/api/v1/processos/upload-pdf",
                files={"file": (f"peticao_{expected_used}.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
                headers=headers,
            )
            assert up.status_code == 200, up.text
            created_ids.append(up.json()["id_processo"])

            st = client.get("/api/v1/auth/plano", headers=headers).json()
            assert st["analises_realizadas"] == expected_used
            assert st["analises_restantes"] == 3 - expected_used

        pdf_quarto = _pdf_peticao_unica(_cnj_unico())
        blocked = client.post(
            "/api/v1/processos/upload-pdf",
            files={"file": ("peticao_4_bloqueada.pdf", io.BytesIO(pdf_quarto), "application/pdf")},
            headers=headers,
        )
        assert blocked.status_code == 402
        assert "LimitePlanoFree" in blocked.json()["detail"]
    finally:
        _limpar_dados_teste(created_ids, [], [usuario["id"]])


def test_etapa6_lote_csv_bloqueado_no_plano_free_com_402(client: TestClient):
    """Importação em lote CSV deve retornar HTTP 402 para assinantes do plano FREE."""
    usuario, token = _registrar_e_logar(client, "FreeCsvBlock")
    headers = {"Authorization": f"Bearer {token}"}
    csv_payload = (
        "numero_processo,tema,magistrado,comarca,autor,reu,texto_resumo,resultado,data_julgamento\n"
        f"{_cnj_unico()},Dano Moral,Dr. Rafael De Amorim,1a Vara,Autor Teste,Banco S.A.,Resumo valido teste,Procedente,2026-10-01\n"
    ).encode("utf-8")

    try:
        resp = client.post(
            "/api/v1/processos/upload-csv",
            files={"file": ("lote_free.csv", io.BytesIO(csv_payload), "text/csv")},
            headers=headers,
        )
        assert resp.status_code == 402
        assert "RecursoExclusivoPro" in resp.json()["detail"]
    finally:
        _limpar_dados_teste([], [], [usuario["id"]])


def test_etapa6_upgrade_para_pro_desbloqueia_analises_ilimitadas_e_csv(client: TestClient):
    """Após esgotar cota FREE, upgrade para PRO libera imediatamente o 4o PDF e a importação CSV."""
    usuario, token = _registrar_e_logar(client, "UpgradePro")
    headers = {"Authorization": f"Bearer {token}"}
    created_ids: list[str] = []
    cnj_csv = _cnj_unico()

    try:
        for i in range(3):
            up = client.post(
                "/api/v1/processos/upload-pdf",
                files={"file": (f"free_{i}.pdf", io.BytesIO(_pdf_peticao_unica(_cnj_unico())), "application/pdf")},
                headers=headers,
            )
            assert up.status_code == 200
            created_ids.append(up.json()["id_processo"])

        blocked = client.post(
            "/api/v1/processos/upload-pdf",
            files={"file": ("free_blocked.pdf", io.BytesIO(_pdf_peticao_unica(_cnj_unico())), "application/pdf")},
            headers=headers,
        )
        assert blocked.status_code == 402

        up_resp = client.post(
            "/api/v1/auth/plano/upgrade",
            json={"plano": "PRO", "codigo_convite": "CONAD2026"},
            headers=headers,
        )
        assert up_resp.status_code == 200, up_resp.text
        up_data = up_resp.json()
        assert up_data["plano"] == "PRO"
        assert up_data["recursos_pro_liberados"] is True
        assert up_data["lote_csv_liberado"] is True
        assert up_data["tese_aprofundada_liberada"] is True

        status_get = client.get("/api/v1/auth/plano", headers=headers).json()
        assert status_get["plano"] == "PRO"
        assert status_get["recursos_pro_liberados"] is True

        fourth_pdf = client.post(
            "/api/v1/processos/upload-pdf",
            files={"file": ("pro_desbloqueado.pdf", io.BytesIO(_pdf_peticao_unica(_cnj_unico())), "application/pdf")},
            headers=headers,
        )
        assert fourth_pdf.status_code == 200, fourth_pdf.text
        created_ids.append(fourth_pdf.json()["id_processo"])

        csv_payload = (
            "numero_processo,tema,magistrado,comarca,autor,reu,texto_resumo,resultado,data_julgamento\n"
            f"{cnj_csv},Dano Moral,Dr. Rafael De Amorim,1a Vara,Autor PRO,Banco S.A.,Resumo valido lote PRO,Procedente,2026-10-01\n"
        ).encode("utf-8")
        csv_ok = client.post(
            "/api/v1/processos/upload-csv",
            files={"file": ("lote_pro.csv", io.BytesIO(csv_payload), "text/csv")},
            headers=headers,
        )
        assert csv_ok.status_code == 200, csv_ok.text
        assert csv_ok.json()["total_importados_com_sucesso"] == 1
    finally:
        _limpar_dados_teste(created_ids, [cnj_csv], [usuario["id"]])


def test_etapa6_usuario_institucional_padrao_possui_plano_pro(client: TestClient):
    """A conta institucional padrão (advogado@escritorio.com / usr-01) deve possuir plano PRO ativo."""
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "advogado@escritorio.com", "senha": "senhaSegura123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    plano_resp = client.get("/api/v1/auth/plano", headers={"Authorization": f"Bearer {token}"})
    assert plano_resp.status_code == 200
    data = plano_resp.json()
    assert data["plano"] == "PRO"
    assert data["recursos_pro_liberados"] is True


def test_etapa6_integracao_frontend_freemium_e_artefatos_cloud():
    """Valida contratos Freemium no front-end e artefatos de deploy cloud (Dockerfile + render.yaml)."""
    api_js = (REPO_ROOT / "frontend" / "src" / "services" / "api.js").read_text(encoding="utf-8")
    index_html = (REPO_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (REPO_ROOT / "frontend" / "src" / "app.js").read_text(encoding="utf-8")
    tokens_css = (REPO_ROOT / "frontend" / "src" / "components" / "design-tokens.css").read_text(encoding="utf-8")
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    render_yaml = (REPO_ROOT / "render.yaml").read_text(encoding="utf-8")

    assert "/api/v1/auth/plano" in api_js
    assert "/api/v1/auth/plano/upgrade" in api_js
    assert "VITE_API_BASE_URL" in api_js
    assert "fetchStatusPlano" in api_js
    assert "atualizarPlanoAssinatura" in api_js

    for html_id in (
        'id="btn-open-upgrade-modal"',
        'id="plan-status-badge"',
        'id="thesis-pro-lock-banner"',
        'id="btn-unlock-thesis-pro"',
        'id="upgrade-modal"',
        'id="btn-activate-pro"',
        'id="btn-simulate-free"',
    ):
        assert html_id in index_html

    assert "carregarStatusPlano" in app_js
    assert "atualizarUIPlano" in app_js
    assert "abrirModalUpgrade" in app_js
    assert ".thesis-card.is-free-locked" in tokens_css

    assert "SERVE_FRONTEND_STATIC=true" in dockerfile
    assert "uvicorn app.main:app" in dockerfile
    assert "jurivision-api" in render_yaml
    assert "jurivision-ai-engine" in render_yaml
