"""
Suíte de Verificação Exaustiva da Etapa 2 — Segurança JWT, /auth/me e Isolamento Multi-usuário.
"""
from datetime import datetime, timedelta, timezone
import io
from pathlib import Path
from typing import Iterator
import uuid

from fastapi.testclient import TestClient
import jwt
import pytest

from app.core.config import settings
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


def _numero_cnj_unico() -> str:
    seq = uuid.uuid4().int % 10_000_000
    dv = uuid.uuid4().int % 100
    return f"{seq:07d}-{dv:02d}.2026.8.02.0001"


def _registrar_e_logar(client: TestClient, nome_prefixo: str) -> tuple[dict, str]:
    uid = uuid.uuid4()
    email = f"{nome_prefixo.lower()}-{uid.hex[:10]}@example.com"
    oab = f"{(uid.int % 899_999) + 100_000}/AL"
    senha = "SenhaForte2026!"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "nome": f"{nome_prefixo} Teste",
            "email": email,
            "senha": senha,
            "numero_oab": oab,
        },
    )
    assert reg.status_code == 201, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "senha": senha})
    assert login.status_code == 200, login.text
    return reg.json(), login.json()["access_token"]


def _payload_processo(**overrides) -> dict:
    base = {
        "numero_processo": _numero_cnj_unico(),
        "tema": "Dano Moral",
        "magistrado": "Dr. Rafael De Amorim",
        "comarca": "1ª Vara Cível de Maceió",
        "autor": "Mariana Santos Costa",
        "reu": "Banco Exemplo S.A.",
        "resumo": "Autora: Mariana Santos Costa, CPF 123.456.789-00, requer reparação civil.",
        "resultado": "Procedente",
        "data_julgamento": "2026-06-15",
    }
    base.update(overrides)
    return base


def _limpar_processos_e_usuarios(proc_ids: list[str], user_ids: list[str]) -> None:
    with SessionLocal() as db:
        for pid in proc_ids:
            proc = db.query(Processo).filter(Processo.id_processo == pid).first()
            if proc:
                db.delete(proc)
        db.flush()
        for uid in user_ids:
            usr = db.query(Usuario).filter(Usuario.id == uid).first()
            if usr:
                db.delete(usr)
        db.commit()


def test_etapa2_auth_me_exige_token_valido_e_retorna_perfil(client: TestClient):
    """GET /api/v1/auth/me deve exigir Bearer JWT válido e rejeitar ausente, malformado ou expirado."""
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Basic abc"}).status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer "}).status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer token.invalido.aqui"}).status_code == 401

    usuario, token = _registrar_e_logar(client, "MeTester")
    try:
        exp_payload = {
            "sub": usuario["id"],
            "iat": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
            "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
        }
        expired_token = jwt.encode(exp_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"}).status_code == 401

        resp_ok = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp_ok.status_code == 200
        assert resp_ok.json() == usuario
    finally:
        _limpar_processos_e_usuarios([], [usuario["id"]])


def test_etapa2_rotas_rejeitam_token_jwt_invalido_com_401(client: TestClient):
    """Rotas principais devem rejeitar com HTTP 401 qualquer token JWT inválido quando enviado."""
    bad_headers = {"Authorization": "Bearer token.falso.invalido"}

    assert client.get("/api/v1/processos", headers=bad_headers).status_code == 401
    assert client.post("/api/v1/processos", json=_payload_processo(), headers=bad_headers).status_code == 401
    assert client.get("/api/v1/processos/filtros", headers=bad_headers).status_code == 401
    assert client.get("/api/v1/dashboard/metricas", headers=bad_headers).status_code == 401
    assert client.get("/api/v1/relatorios/processo/proc-1001/pdf", headers=bad_headers).status_code == 401


def test_etapa2_isolamento_estrito_entre_advogados_distintos(client: TestClient):
    """Processos criados por Advogado A ficam invisíveis e inacessíveis para Advogado B e visitantes."""
    user_a, token_a = _registrar_e_logar(client, "AdvogadoA")
    user_b, token_b = _registrar_e_logar(client, "AdvogadoB")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    created_ids: list[str] = []

    try:
        payload = _payload_processo()
        resp_create = client.post("/api/v1/processos", json=payload, headers=headers_a)
        assert resp_create.status_code == 201, resp_create.text
        proc_id = resp_create.json()["id_processo"]
        created_ids.append(proc_id)
        cnj = payload["numero_processo"]

        with SessionLocal() as db:
            proc_db = db.query(Processo).filter(Processo.id_processo == proc_id).first()
            assert proc_db is not None
            assert proc_db.usuario_id == user_a["id"]

        # Advogado A enxerga, lê, edita e exporta PDF
        assert client.get("/api/v1/processos", params={"busca": cnj}, headers=headers_a).json()["total"] == 1
        assert client.get(f"/api/v1/processos/{proc_id}", headers=headers_a).status_code == 200
        assert client.put(
            f"/api/v1/processos/{proc_id}",
            json={**payload, "tema": "Direito Digital"},
            headers=headers_a,
        ).status_code == 200
        assert client.get(f"/api/v1/relatorios/processo/{proc_id}/pdf", headers=headers_a).status_code == 200

        # Advogado B e visitante anônimo NÃO veem o processo privado de A
        assert client.get("/api/v1/processos", params={"busca": cnj}, headers=headers_b).json()["total"] == 0
        assert client.get("/api/v1/processos", params={"busca": cnj}).json()["total"] == 0

        for target_headers in (headers_b, {}):
            assert client.get(f"/api/v1/processos/{proc_id}", headers=target_headers).status_code == 404
            assert client.put(
                f"/api/v1/processos/{proc_id}",
                json=payload,
                headers=target_headers,
            ).status_code == 404
            assert client.delete(f"/api/v1/processos/{proc_id}", headers=target_headers).status_code == 404
            assert client.get(
                f"/api/v1/relatorios/processo/{proc_id}/pdf",
                headers=target_headers,
            ).status_code == 404
    finally:
        _limpar_processos_e_usuarios(created_ids, [user_a["id"], user_b["id"]])


def test_etapa2_acervo_publico_protegido_contra_alteracao_por_terceiros(client: TestClient):
    """Contas externas leem o acervo público base (proc-1001), mas recebem 403 ao editar ou excluir."""
    user_a, token_a = _registrar_e_logar(client, "Externo")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    try:
        det = client.get("/api/v1/processos/proc-1001", headers=headers_a)
        assert det.status_code == 200
        meta = det.json()["metadados_extraidos"]

        put_resp = client.put(
            "/api/v1/processos/proc-1001",
            json={
                "numero_processo": meta["numero_processo"],
                "tema": meta["tema"],
                "magistrado": meta["magistrado"],
                "comarca": meta["comarca"],
                "autor": meta["partes_anonimizadas"]["autor"],
                "reu": meta["partes_anonimizadas"]["reu"],
                "resumo": det.json()["resumo_nlp"],
                "resultado": det.json()["resultado"],
                "data_julgamento": det.json()["data_julgamento"],
            },
            headers=headers_a,
        )
        assert put_resp.status_code == 403

        del_resp = client.delete("/api/v1/processos/proc-1001", headers=headers_a)
        assert del_resp.status_code == 403
    finally:
        _limpar_processos_e_usuarios([], [user_a["id"]])


def test_etapa2_isolamento_upload_pdf_filtros_e_dashboard(client: TestClient):
    """Upload de PDF, métricas do Dashboard e seletores dinâmicos de filtros isolam processos privados."""
    user_a, token_a = _registrar_e_logar(client, "UploadA")
    user_b, token_b = _registrar_e_logar(client, "UploadB")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    created_ids: list[str] = []

    try:
        dash_b_antes = client.get("/api/v1/dashboard/metricas", headers=headers_b).json()

        cnj_pdf = _numero_cnj_unico()
        pdf_bytes = _build_pdf_document(
            [
                "1a VARA CIVEL DE MACEIO",
                f"Processo: {cnj_pdf}",
                "Autor: Joao Pedro Rocha, CPF 111.222.333-44.",
                "Reu: Companhia Aerea Teste S.A.",
                "Cancelamento abusivo de voo sem assistencia material.",
            ]
        )
        up = client.post(
            "/api/v1/processos/upload-pdf",
            files={"file": ("peticao_privada_a.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            headers=headers_a,
        )
        assert up.status_code == 200, up.text
        created_ids.append(up.json()["id_processo"])

        tema_exclusivo = f"Tema Privado {uuid.uuid4().hex[:6]}"
        juiz_exclusivo = f"Dra. Privada {uuid.uuid4().hex[:6]}"
        manual_a = client.post(
            "/api/v1/processos",
            json=_payload_processo(tema=tema_exclusivo, magistrado=juiz_exclusivo),
            headers=headers_a,
        )
        assert manual_a.status_code == 201
        created_ids.append(manual_a.json()["id_processo"])

        dash_a = client.get("/api/v1/dashboard/metricas", headers=headers_a).json()
        dash_b_depois = client.get("/api/v1/dashboard/metricas", headers=headers_b).json()

        assert dash_b_depois["total_processos_analisados"] == dash_b_antes["total_processos_analisados"]
        assert dash_a["total_processos_analisados"] == dash_b_antes["total_processos_analisados"] + 2

        filtros_a = client.get("/api/v1/processos/filtros", headers=headers_a).json()
        filtros_b = client.get("/api/v1/processos/filtros", headers=headers_b).json()
        assert tema_exclusivo in filtros_a["temas"]
        assert juiz_exclusivo in filtros_a["magistrados"]
        assert tema_exclusivo not in filtros_b["temas"]
        assert juiz_exclusivo not in filtros_b["magistrados"]
    finally:
        _limpar_processos_e_usuarios(created_ids, [user_a["id"], user_b["id"]])


def test_etapa2_exportacao_pdf_privado_via_query_token(client: TestClient):
    """Exportação de PDF aceita ?token=<jwt> para abertura em nova aba mantendo o isolamento."""
    user_a, token_a = _registrar_e_logar(client, "PdfA")
    user_b, token_b = _registrar_e_logar(client, "PdfB")
    created_ids: list[str] = []

    try:
        resp_create = client.post(
            "/api/v1/processos",
            json=_payload_processo(),
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp_create.status_code == 201
        proc_id = resp_create.json()["id_processo"]
        created_ids.append(proc_id)

        pdf_ok = client.get(f"/api/v1/relatorios/processo/{proc_id}/pdf", params={"token": token_a})
        assert pdf_ok.status_code == 200
        assert pdf_ok.content.startswith(b"%PDF-1.4")

        assert client.get(f"/api/v1/relatorios/processo/{proc_id}/pdf", params={"token": token_b}).status_code == 404
        assert client.get(f"/api/v1/relatorios/processo/{proc_id}/pdf", params={"token": "invalido"}).status_code == 401
    finally:
        _limpar_processos_e_usuarios(created_ids, [user_a["id"], user_b["id"]])


def test_etapa2_integracao_frontend_sessao_e_logout():
    """Front-end deve restaurar sessão via /auth/me, propagar ?token no PDF e expor logout."""
    api_js = (REPO_ROOT / "frontend" / "src" / "services" / "api.js").read_text(encoding="utf-8")
    app_js = (REPO_ROOT / "frontend" / "src" / "app.js").read_text(encoding="utf-8")
    index_html = (REPO_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "/api/v1/auth/me" in api_js
    assert "fetchUsuarioAtual" in api_js
    assert "logoutAdvogado" in api_js
    assert "?token=" in api_js
    assert "restaurarSessaoAutenticada" in app_js
    assert "logoutAdvogado" in app_js
    assert 'id="btn-logout-account"' in index_html


def test_etapa2_escrita_anonima_sem_seed_respeita_foreign_keys_ativas(monkeypatch):
    """
    Com SEED_DEMO_DATA=false (usr-01 inexistente) e integridade referencial ativa (FK ON),
    visitantes anônimos gravam processos com usuario_id=None sem violar FK em POST/PDF/CSV/DataJud.
    """
    from dataclasses import replace

    from sqlalchemy import create_engine, event
    from sqlalchemy.pool import StaticPool

    import app.core.database as db_mod
    import app.core.datajud_client as datajud_mod
    import app.main as main_mod
    from app.schemas.contracts import DataJudAssuntoSchema, DataJudProcessoResponse

    monkeypatch.setattr(main_mod, "settings", replace(settings, SEED_DEMO_DATA=False))

    fk_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(fk_engine, "connect")
    def _enable_fk(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    original_db_engine = db_mod.engine
    original_main_engine = main_mod.engine
    monkeypatch.setattr(db_mod, "engine", fk_engine)
    monkeypatch.setattr(main_mod, "engine", fk_engine)
    SessionLocal.configure(bind=fk_engine)

    async def _fake_coletar_lote(*, tribunal="TJAL", tema=None, limite=3):
        item = DataJudProcessoResponse(
            numero_processo=_numero_cnj_unico(),
            tribunal=tribunal,
            classe="Procedimento Comum Cível",
            assuntos=[DataJudAssuntoSchema(codigo=10433, nome="Dano Moral", principal=True)],
            assunto_principal="Dano Moral",
            orgao_julgador="1ª Vara Cível de Maceió",
            data_ajuizamento="2025-02-10T10:00:00.000Z",
            grau="G1",
            movimentos_recentes=[],
            desfecho="Procedente",
            fonte="datajud_api",
            sucesso=True,
            mensagem="Coleta mockada.",
        )
        return [item], "datajud_api", None

    monkeypatch.setattr(datajud_mod.DataJudClient, "coletar_lote_jurisprudencia", _fake_coletar_lote)

    try:
        init_db_and_seed(seed_demo=False)
        with SessionLocal() as db:
            assert db.query(Usuario).count() == 0

        with TestClient(app) as anon_client:
            manual = anon_client.post("/api/v1/processos", json=_payload_processo())
            assert manual.status_code == 201, manual.text
            manual_id = manual.json()["id_processo"]

            cnj_pdf = _numero_cnj_unico()
            pdf_bytes = _build_pdf_document(
                [
                    "1a VARA CIVEL DE MACEIO",
                    f"Processo: {cnj_pdf}",
                    "Autor: Helena Lima Costa, CPF 111.222.333-44.",
                    "Reu: Empresa Aerea S.A.",
                    "Atraso de voo internacional sem assistencia material.",
                ]
            )
            pdf_resp = anon_client.post(
                "/api/v1/processos/upload-pdf",
                files={"file": ("peticao_anon.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            )
            assert pdf_resp.status_code == 200, pdf_resp.text
            pdf_id = pdf_resp.json()["id_processo"]

            cnj_csv = _numero_cnj_unico()
            csv_bytes = (
                "numero_processo,tema,magistrado,comarca,autor,reu,texto_resumo,resultado,data_julgamento\n"
                f"{cnj_csv},Dano Moral,Dr. Teste,1a Vara,Maria Souza,Banco X S.A.,Resumo valido importado,Procedente,2026-08-10\n"
            ).encode("utf-8")
            csv_resp = anon_client.post(
                "/api/v1/processos/upload-csv",
                files={"file": ("lote_anon.csv", io.BytesIO(csv_bytes), "text/csv")},
            )
            assert csv_resp.status_code == 200, csv_resp.text

            sync_resp = anon_client.post(
                "/api/v1/processos/datajud/sincronizar",
                json={"tribunal": "TJAL", "limite": 1},
            )
            assert sync_resp.status_code == 200, sync_resp.text
            assert sync_resp.json()["novos_inseridos"] == 1

            list_resp = anon_client.get("/api/v1/processos")
            assert list_resp.status_code == 200
            assert list_resp.json()["total"] == 4

            with SessionLocal() as db:
                for pid in (manual_id, pdf_id):
                    row = db.query(Processo).filter(Processo.id_processo == pid).first()
                    assert row is not None and row.usuario_id is None
                csv_row = db.query(Processo).filter(Processo.numero_processo == cnj_csv).first()
                assert csv_row is not None and csv_row.usuario_id is None

            # Conta externa autenticada lê o processo público (usuario_id=None), mas não pode alterá-lo
            _, token_ext = _registrar_e_logar(anon_client, "ExternoSemSeed")
            del_ext = anon_client.delete(
                f"/api/v1/processos/{manual_id}",
                headers={"Authorization": f"Bearer {token_ext}"},
            )
            assert del_ext.status_code == 403
    finally:
        fk_engine.dispose()
        monkeypatch.setattr(db_mod, "engine", original_db_engine)
        monkeypatch.setattr(main_mod, "engine", original_main_engine)
        SessionLocal.configure(bind=original_db_engine)
