"""
Suíte de Verificação Exaustiva da Etapa 1 — Consistência, Filtros/Ordenação no Servidor,
Exclusão Integrada (DELETE) e Relatórios PDF Multi-página.
"""
import io
from pathlib import Path
from typing import Iterator
import uuid

from fastapi.testclient import TestClient
from pypdf import PdfReader
import pytest

from app.core.database import SessionLocal
from app.main import app, init_db_and_seed
from app.models.entities import AnalisePreditiva, LogAuditoriaLGPD, Processo

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


def _criar_processo(client: TestClient, **overrides) -> dict:
    payload = {
        "numero_processo": _numero_cnj_unico(),
        "tema": "Dano Moral",
        "magistrado": "Dr. Rafael De Amorim",
        "comarca": "1ª Vara Cível de Maceió",
        "autor": "Carlos Alberto Silva",
        "reu": "Banco Teste S.A.",
        "resumo": "Autor Carlos Alberto Silva, CPF 111.222.333-44, ingressou com ação de reparação civil.",
        "resultado": "Procedente",
        "data_julgamento": "2026-05-10",
    }
    payload.update(overrides)
    resp = client.post("/api/v1/processos", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_etapa1_listagem_inclui_resumo_curto_real(client: TestClient):
    """GET /api/v1/processos deve retornar resumo_curto idêntico ao resumo_nlp persistido."""
    criado = _criar_processo(
        client,
        autor="Maria Clara Dias",
        resumo="Autora: Maria Clara Dias, CPF 111.222.333-44, questiona cobrança de tarifa bancária indevida em conta corrente.",
    )
    id_proc = criado["id_processo"]
    try:
        cnj = criado["metadados_extraidos"]["numero_processo"]
        resp = client.get("/api/v1/processos", params={"busca": cnj})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        item = body["itens"][0]
        assert item["resumo_curto"] == criado["resumo_nlp"]
        assert "Maria Clara Dias" not in item["resumo_curto"]
        assert "111.222.333-44" not in item["resumo_curto"]
    finally:
        client.delete(f"/api/v1/processos/{id_proc}")


def test_etapa1_ordenacao_no_servidor_recentes_antigas_assunto(client: TestClient):
    """?ordenacao=recentes|antigas|assunto deve ordenar corretamente no banco através das páginas."""
    juiz_isolado = f"Dr. Juiz Ordenacao {uuid.uuid4().hex[:6]}"
    criados = [
        _criar_processo(
            client,
            magistrado=juiz_isolado,
            tema="Zebra Juridica",
            data_julgamento="2021-03-10",
        ),
        _criar_processo(
            client,
            magistrado=juiz_isolado,
            tema="Alfa Direito",
            data_julgamento="2026-11-01",
        ),
        _criar_processo(
            client,
            magistrado=juiz_isolado,
            tema="Meio Consumo",
            data_julgamento="2023-07-20",
        ),
    ]
    try:
        # 1. Mais recentes primeiro (página 1 com limite=2, página 2 com limite=2)
        p1_rec = client.get(
            "/api/v1/processos",
            params={"juiz": juiz_isolado, "ordenacao": "recentes", "pagina": 1, "limite": 2},
        ).json()
        p2_rec = client.get(
            "/api/v1/processos",
            params={"juiz": juiz_isolado, "ordenacao": "recentes", "pagina": 2, "limite": 2},
        ).json()
        datas_rec = [i["data_julgamento"] for i in p1_rec["itens"] + p2_rec["itens"]]
        assert datas_rec == ["2026-11-01", "2023-07-20", "2021-03-10"]

        # 2. Mais antigas primeiro
        p1_ant = client.get(
            "/api/v1/processos",
            params={"juiz": juiz_isolado, "ordenacao": "antigas", "pagina": 1, "limite": 2},
        ).json()
        p2_ant = client.get(
            "/api/v1/processos",
            params={"juiz": juiz_isolado, "ordenacao": "antigas", "pagina": 2, "limite": 2},
        ).json()
        datas_ant = [i["data_julgamento"] for i in p1_ant["itens"] + p2_ant["itens"]]
        assert datas_ant == ["2021-03-10", "2023-07-20", "2026-11-01"]

        # 3. Por assunto (A-Z)
        p1_ass = client.get(
            "/api/v1/processos",
            params={"juiz": juiz_isolado, "ordenacao": "assunto", "pagina": 1, "limite": 2},
        ).json()
        p2_ass = client.get(
            "/api/v1/processos",
            params={"juiz": juiz_isolado, "ordenacao": "assunto", "pagina": 2, "limite": 2},
        ).json()
        temas_ass = [i["tema"] for i in p1_ass["itens"] + p2_ass["itens"]]
        assert temas_ass == ["Alfa Direito", "Meio Consumo", "Zebra Juridica"]
    finally:
        for item in criados:
            client.delete(f"/api/v1/processos/{item['id_processo']}")


def test_etapa1_filtro_ids_decisoes_salvas_no_servidor(client: TestClient):
    """?ids=proc-1001,proc-1004 deve filtrar no servidor mesmo com muitos registros mais novos."""
    extras = [
        _criar_processo(client, data_julgamento="2026-12-15")
        for _ in range(10)
    ]
    try:
        resp = client.get(
            "/api/v1/processos",
            params={"ids": "proc-1001,proc-1004", "pagina": 1, "limite": 8},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        returned_ids = {item["id_processo"] for item in body["itens"]}
        assert returned_ids == {"proc-1001", "proc-1004"}
    finally:
        for item in extras:
            client.delete(f"/api/v1/processos/{item['id_processo']}")


def test_etapa1_filtro_ids_vazio_retorna_zero(client: TestClient):
    """?ids= vazio (nenhuma decisão salva) deve retornar total=0 e lista vazia."""
    resp = client.get("/api/v1/processos", params={"ids": ""})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["itens"] == []


def test_etapa1_endpoint_filtros_dinamicos_atualiza_com_novos_julgados(client: TestClient):
    """GET /api/v1/processos/filtros deve listar temas, magistrados e comarcas distintos atualizados."""
    criado = _criar_processo(
        client,
        tema="Direito Ambiental",
        magistrado="Dra. Helena Costa",
        comarca="Vara Ambiental de Maceió",
    )
    id_proc = criado["id_processo"]
    try:
        resp = client.get("/api/v1/processos/filtros")
        assert resp.status_code == 200
        body = resp.json()
        assert "Direito Ambiental" in body["temas"]
        assert "Dra. Helena Costa" in body["magistrados"]
        assert "Vara Ambiental de Maceió" in body["comarcas"]
        assert body["temas"] == sorted(body["temas"])
        assert body["magistrados"] == sorted(body["magistrados"])
        assert body["comarcas"] == sorted(body["comarcas"])
    finally:
        client.delete(f"/api/v1/processos/{id_proc}")


def test_etapa1_delete_processo_remove_em_cascata_e_retorna_404(client: TestClient):
    """DELETE /api/v1/processos/{id} deve apagar processo + análise + logs LGPD em cascata."""
    criado = _criar_processo(client)
    id_proc = criado["id_processo"]

    resp_del = client.delete(f"/api/v1/processos/{id_proc}")
    assert resp_del.status_code == 204

    assert client.get(f"/api/v1/processos/{id_proc}").status_code == 404
    assert client.delete(f"/api/v1/processos/{id_proc}").status_code == 404

    with SessionLocal() as db:
        assert db.query(Processo).filter(Processo.id_processo == id_proc).first() is None
        assert db.query(AnalisePreditiva).filter(AnalisePreditiva.id_processo == id_proc).first() is None
        assert db.query(LogAuditoriaLGPD).filter(LogAuditoriaLGPD.id_processo == id_proc).first() is None


def test_etapa1_relatorio_pdf_multipagina_para_texto_longo(client: TestClient):
    """Relatório PDF com síntese extensa (> 3.500 chars) deve paginar automaticamente em PDF 1.4 válido."""
    resumo_longo = " ".join(
        f"Paragrafo {idx}: fatos processuais relevantes sobre falha na prestacao de servicos bancarios e consumidor."
        for idx in range(1, 45)
    )
    assert len(resumo_longo) > 3500
    criado = _criar_processo(client, resumo=resumo_longo)
    id_proc = criado["id_processo"]
    try:
        resp = client.get(f"/api/v1/relatorios/processo/{id_proc}/pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content.startswith(b"%PDF-1.4")
        assert b"/Count 2" in resp.content or b"/Count 3" in resp.content

        reader = PdfReader(io.BytesIO(resp.content))
        assert len(reader.pages) >= 2
        texto_p1 = reader.pages[0].extract_text() or ""
        texto_p2 = reader.pages[1].extract_text() or ""
        assert "JURIVISION" in texto_p1
        assert "Pagina 1 de" in texto_p1
        assert "Pagina 2 de" in texto_p2
    finally:
        client.delete(f"/api/v1/processos/{id_proc}")


def test_etapa1_integracao_frontend_novos_contratos():
    """Front-end deve expor e consumir filtros dinâmicos, ordenação/ids no servidor e botão de exclusão."""
    api_js = (REPO_ROOT / "frontend" / "src" / "services" / "api.js").read_text(encoding="utf-8")
    app_js = (REPO_ROOT / "frontend" / "src" / "app.js").read_text(encoding="utf-8")
    index_html = (REPO_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "/api/v1/processos/filtros" in api_js
    assert "excluirProcesso" in api_js
    assert "ordenacao" in api_js
    assert "ids" in api_js
    assert "carregarFiltrosDinamicos" in app_js
    assert "excluirProcesso" in app_js
    assert 'id="btn-excluir-julgado"' in index_html
