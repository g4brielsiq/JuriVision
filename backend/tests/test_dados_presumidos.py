"""
Regressão: o acervo só recebe dados que vieram de uma fonte real.
- Petição enviada em PDF não vira decisão "Procedente" (a previsão fica em analise_preditiva);
- Cadastro manual sem órgão julgador não recebe uma vara presumida;
- Importação CSV sem resultado/data não presume desfecho nem data;
- O saneamento remove o antigo lote fictício do DataJud e corrige registros afetados.
"""
from datetime import date, datetime, timezone
import io
import uuid

from fastapi.testclient import TestClient
import pytest

from app.core.database import SessionLocal
from app.core.saneamento_acervo import sanear_acervo
from app.main import app
from app.models.entities import AnalisePreditiva, Processo


@pytest.fixture
def client():
    return TestClient(app)


def _cnj_valido(sequencial: int, ano: int = 2025) -> str:
    seq = f"{sequencial:07d}"
    restante = f"{ano}8020001"
    dv = 98 - int(f"{seq}{restante}00") % 97
    return f"{seq}-{dv:02d}.{ano}.8.02.0001"


def _pdf(linhas: list[str]) -> bytes:
    conteudo = "BT /F1 12 Tf 72 720 Td " + " ".join(f"({linha}) Tj 0 -16 Td" for linha in linhas) + " ET"
    stream = conteudo.encode("latin-1")
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    saida = io.BytesIO()
    saida.write(b"%PDF-1.4\n")
    for i, obj in enumerate(objetos, start=1):
        saida.write(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    saida.write(b"trailer << /Root 1 0 R >>\n%%EOF")
    return saida.getvalue()


def test_upload_pdf_nao_registra_previsao_como_desfecho(client):
    cnj = _cnj_valido(int(uuid.uuid4().int % 9_000_000) + 100)
    pdf = _pdf(
        [
            "EXCELENTISSIMO SENHOR JUIZ DA 2a VARA CIVEL DE MACEIO",
            f"Processo: {cnj}",
            "Autor: Fernanda Oliveira Souza",
            "Reu: Banco Exemplo S.A.",
            "Negativacao indevida do nome da autora com pedido de indenizacao por dano moral.",
        ]
    )
    resp = client.post("/api/v1/processos/upload-pdf", files={"file": ("p.pdf", io.BytesIO(pdf), "application/pdf")})
    assert resp.status_code == 200, resp.text
    proc_id = resp.json()["id_processo"]
    try:
        detalhe = client.get(f"/api/v1/processos/{proc_id}").json()
        assert detalhe["resultado"] == "Em Analise"
        assert detalhe["data_julgamento"] is None
    finally:
        client.delete(f"/api/v1/processos/{proc_id}")


def test_cadastro_sem_orgao_julgador_nao_presume_vara(client):
    payload = {
        "numero_processo": _cnj_valido(int(uuid.uuid4().int % 9_000_000) + 100),
        "tema": "Dano Moral",
        "magistrado": "Dr. Teste",
        "autor": "Maria Souza",
        "reu": "Banco X S.A.",
        "resumo": "Resumo de teste com mais de dez caracteres.",
    }
    resp = client.post("/api/v1/processos", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    try:
        assert body["metadados_extraidos"]["comarca"] == "Não informado"
    finally:
        client.delete(f"/api/v1/processos/{body['id_processo']}")


def test_csv_sem_resultado_nem_data_nao_presume(client):
    cnj = _cnj_valido(int(uuid.uuid4().int % 9_000_000) + 100)
    csv_bytes = (
        "numero_processo,tema,magistrado,comarca,autor,reu,texto_resumo,resultado,data_julgamento\n"
        f"{cnj},Dano Moral,Dr. Teste,1a Vara,Maria Souza,Banco X S.A.,Resumo importado para teste,,\n"
    ).encode("utf-8")
    resp = client.post("/api/v1/processos/upload-csv", files={"file": ("l.csv", io.BytesIO(csv_bytes), "text/csv")})
    assert resp.status_code == 200, resp.text
    with SessionLocal() as db:
        proc = db.query(Processo).filter(Processo.numero_processo == cnj).first()
        assert proc is not None
        assert proc.resultado_historico == "Em Analise"
        assert proc.data_julgamento is None
        db.delete(proc)
        db.commit()


def test_saneamento_remove_lote_ficticio_e_corrige_registros():
    hoje = date.today()
    agora = datetime.now(timezone.utc)
    real_cnj = _cnj_valido(int(uuid.uuid4().int % 9_000_000) + 100)
    pdf_cnj = _cnj_valido(int(uuid.uuid4().int % 9_000_000) + 100)
    sufixo = uuid.uuid4().hex[:6]

    def novo(id_proc, numero, origem, **extra):
        base = dict(
            id_processo=id_proc,
            numero_processo=numero,
            origem_ingestao=origem,
            arquivo_nome="teste_saneamento",
            tema="Dano Moral",
            magistrado="Dr. Rafael De Amorim",
            comarca="1ª Vara Cível de Maceió",
            autor_anonimizado="Parte A. ***",
            reu_anonimizado="Banco X S.A.",
            resumo_nlp="Resumo.",
            resultado_historico="Procedente",
            data_julgamento=hoje,
            criado_em=agora,
        )
        base.update(extra)
        return Processo(**base)

    with SessionLocal() as db:
        db.add_all(
            [
                novo(f"proc-fic-{sufixo}", "0804110-12.2026.8.02.0001", "DATAJUD"),
                novo(
                    f"proc-dj-{sufixo}",
                    real_cnj,
                    "DATAJUD",
                    autor_anonimizado="Carlos E. ***",
                    reu_anonimizado="Instituição Financeira S.A.",
                    resumo_nlp="Jurisprudência coletada via DataJud (TJAL). Parte autora: Carlos E. *** em face de Instituição Financeira S.A.. Síntese.",
                ),
                novo(f"proc-pdf-{sufixo}", pdf_cnj, "PDF"),
            ]
        )
        db.add(AnalisePreditiva(id_processo=f"proc-pdf-{sufixo}", probabilidade_deferimento=0.8, margem_confianca=0.1,
                                tempo_estimado_sentenca_meses=8, casos_similares_encontrados=3,
                                tese_recomendada="t", tendencia_juiz="t", provedor_ia_utilizado="local_heuristic"))
        db.commit()

        resumo = sanear_acervo(db)
        assert resumo["ficticios_removidos"] >= 1
        assert resumo["datajud_partes_corrigidas"] >= 1
        assert resumo["pdf_desfecho_corrigido"] >= 1

        assert db.get(Processo, f"proc-fic-{sufixo}") is None
        dj = db.get(Processo, f"proc-dj-{sufixo}")
        assert dj.autor_anonimizado == "Não informado pelo DataJud"
        assert dj.magistrado == "Não informado pelo DataJud"
        assert dj.resultado_historico == "Em Analise"
        assert "Carlos" not in dj.resumo_nlp
        pdf = db.get(Processo, f"proc-pdf-{sufixo}")
        assert pdf.resultado_historico == "Em Analise"
        assert pdf.data_julgamento is None

        # Idempotente: a segunda execução não encontra mais nada
        assert sanear_acervo(db) == {"ficticios_removidos": 0, "datajud_partes_corrigidas": 0, "pdf_desfecho_corrigido": 0}
        db.delete(dj)
        db.delete(pdf)
        db.commit()
