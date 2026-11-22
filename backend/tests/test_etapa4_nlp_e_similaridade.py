"""
Suíte de Verificação Exaustiva da Etapa 4 — Motor NLP Local Real (TF-IDF / BM25),
Extração Dinâmica de Magistrado/Vara, Sumarização por Centralidade e Intervalo de Wilson.
"""
import io
from types import SimpleNamespace
from typing import Iterator
import uuid

from fastapi.testclient import TestClient
import pytest

from app.core.nlp_engine import (
    classify_legal_theme,
    compute_wilson_margin,
    extract_court_and_judge,
    rank_similar_precedents,
    summarize_legal_text,
)
from app.main import app, init_db_and_seed
from app.routers.relatorios import _build_pdf_document


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    init_db_and_seed()
    with TestClient(app) as test_client:
        yield test_client


def _numero_cnj_unico() -> str:
    seq = uuid.uuid4().int % 10_000_000
    dv = uuid.uuid4().int % 100
    return f"{seq:07d}-{dv:02d}.2026.8.02.0001"


def test_etapa4_similaridade_tfidf_bm25_ranqueia_precedentes_corretos():
    """TF-IDF + BM25 deve ranquear precedentes tematicamente idênticos acima de áreas distintas."""
    processos_simulados = [
        SimpleNamespace(
            id_processo="sim-trib",
            numero_processo="0000001-11.2026.8.02.0001",
            tema="Tributário",
            magistrado="Dr. Carlos Souza",
            comarca="Vara da Fazenda Pública",
            resumo_nlp="Embargos à execução fiscal discutindo base de cálculo de ICMS e IPTU.",
            resultado_historico="Improcedente",
            analise_preditiva=SimpleNamespace(
                tempo_estimado_sentenca_meses=18,
                tese_recomendada="Legalidade tributária e art. 150 da Constituição Federal.",
                probabilidade_deferimento=0.40,
            ),
        ),
        SimpleNamespace(
            id_processo="sim-voo-1",
            numero_processo="0000002-22.2026.8.02.0001",
            tema="Atraso de Voo / Indenização",
            magistrado="Dra. Amanda Cavalcante",
            comarca="1ª Vara Cível de Maceió",
            resumo_nlp="Cancelamento de voo internacional e extravio de bagagem sem assistência ao passageiro no aeroporto.",
            resultado_historico="Procedente",
            analise_preditiva=SimpleNamespace(
                tempo_estimado_sentenca_meses=8,
                tese_recomendada="Dano moral in re ipsa por falha no transporte aéreo (art. 14 do CDC).",
                probabilidade_deferimento=0.85,
            ),
        ),
        SimpleNamespace(
            id_processo="sim-trab",
            numero_processo="0000003-33.2026.8.02.0001",
            tema="Direito Trabalhista",
            magistrado="Dr. Marcelo Lins",
            comarca="2ª Vara do Trabalho de Maceió",
            resumo_nlp="Reclamação trabalhista pleiteando horas extras, adicional noturno e depósitos de FGTS.",
            resultado_historico="Acordo",
            analise_preditiva=SimpleNamespace(
                tempo_estimado_sentenca_meses=10,
                tese_recomendada="Inversão do ônus probatório pelos cartões de ponto (Súmula 338/TST).",
                probabilidade_deferimento=0.72,
            ),
        ),
    ]

    consulta = "Ação indenizatória contra companhia aérea por atraso de voo, cancelamento de embarque e extravio de bagagem no aeroporto."
    ranked = rank_similar_precedents(consulta, processos_simulados, min_similarity=0.05)

    assert len(ranked) >= 1
    assert ranked[0]["id_processo"] == "sim-voo-1"
    if len(ranked) > 1:
        assert ranked[0]["similaridade"] > ranked[1]["similaridade"]


def test_etapa4_extracao_real_de_qualquer_magistrado_e_vara():
    """Extrator dinâmico deve identificar quaisquer magistrados e comarcas sem lista hardcoded."""
    j1, c1 = extract_court_and_judge(
        "Magistrada: Dra. Amanda Cavalcante\n3ª Vara da Fazenda Pública de Arapiraca\nAutos conclusos."
    )
    assert j1 == "Dra. Amanda Cavalcante"
    assert c1 == "3ª Vara da Fazenda Pública de Arapiraca"

    j2, c2 = extract_court_and_judge(
        "Juiz de Direito: Dr. Roberto Tavares\n2ª Vara do Trabalho de Maceió\nReclamação trabalhista."
    )
    assert j2 == "Dr. Roberto Tavares"
    assert c2 == "2ª Vara do Trabalho de Maceió"

    j3, c3 = extract_court_and_judge(
        "EXCELENTISSIMO SENHOR JUIZ DA 1a VARA CIVEL DE MACEIO\nSem nome de juiz citado."
    )
    assert j3 is None
    assert c3 == "1a VARA CIVEL DE MACEIO"


def test_etapa4_sumarizacao_tfidf_ignora_cabecalho_formal_e_prioriza_fatos():
    """Sumarizador deve ignorar endereçamento formal inicial e destacar sentenças fáticas."""
    texto = (
        "EXCELENTISSIMO SENHOR JUIZ DA 1a VARA CIVEL DE MACEIO\n"
        "Processo: 0011223-44.2026.8.02.0001\n"
        "Magistrado: Dra. Helena Costa\n"
        "O consumidor adquiriu passagem aérea internacional com conexão programada e sofreu cancelamento abrupto sem reacomodação ou hospedagem.\n"
        "Requer indenização por danos morais e materiais com fundamento no artigo 14 do Código de Defesa do Consumidor e Resolução 400 da ANAC."
    )
    tema, _, _ = classify_legal_theme(texto)
    resumo = summarize_legal_text(texto, tema, "Fallback")

    assert "EXCELENTISSIMO" not in resumo
    assert "0011223-44.2026.8.02.0001" not in resumo
    assert "cancelamento" in resumo.lower() or "indeniza" in resumo.lower()


def test_etapa4_margem_confianca_wilson_varia_com_tamanho_da_amostra():
    """Margem estatística de Wilson deve estreitar monotonicamente à medida que n cresce."""
    m_3 = compute_wilson_margin(0.75, 3)
    m_15 = compute_wilson_margin(0.75, 15)
    m_50 = compute_wilson_margin(0.75, 50)
    m_200 = compute_wilson_margin(0.75, 200)

    assert m_3 > m_15 > m_50 > m_200
    assert m_3 >= 0.15
    assert m_200 <= 0.05


def test_etapa4_upload_pdf_calcula_precedentes_reais_sem_multiplicador_artificial(client: TestClient):
    """Upload de PDF deve extrair juiz/vara reais e usar contagem real de similares (sem * 7)."""
    total_antes = client.get("/api/v1/dashboard/metricas").json()["total_processos_analisados"]
    cnj = _numero_cnj_unico()
    pdf_bytes = _build_pdf_document(
        [
            "EXCELENTISSIMO SENHOR JUIZ DA 5a VARA CIVEL DE SAO PAULO",
            f"Processo: {cnj}",
            "Juiz de Direito: Dr. Roberto Tavares",
            "Autor: Fernanda Oliveira Souza, CPF 123.456.789-00.",
            "Reu: Companhia Aerea Linhas Brasil S.A.",
            "Demanda reparatoria por atraso de voo, cancelamento de embarque e extravio de bagagem no aeroporto sem assistencia.",
        ]
    )
    resp = client.post(
        "/api/v1/processos/upload-pdf",
        files={"file": ("peticao_etapa4.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    proc_id = body["id_processo"]
    try:
        meta = body["metadados_extraidos"]
        pred = body["analise_preditiva"]
        assert meta["magistrado"] == "Dr. Roberto Tavares"
        assert "5a VARA CIVEL DE SAO PAULO" in meta["comarca"]
        assert "Voo" in meta["tema"]
        assert pred["casos_similares_encontrados"] <= total_antes
        assert pred["casos_similares_encontrados"] >= 1
        assert pred["margem_confianca"] == compute_wilson_margin(
            pred["probabilidade_deferimento"], pred["casos_similares_encontrados"]
        )
    finally:
        client.delete(f"/api/v1/processos/{proc_id}")


def test_etapa4_cadastro_manual_e_csv_usam_motor_estatistico_real(client: TestClient):
    """Cadastro manual e importação CSV devem calcular casos similares e margem de Wilson reais."""
    total_antes = client.get("/api/v1/dashboard/metricas").json()["total_processos_analisados"]
    cnj_manual = _numero_cnj_unico()
    cnj_csv = _numero_cnj_unico()

    resp_manual = client.post(
        "/api/v1/processos",
        json={
            "numero_processo": cnj_manual,
            "tema": "Plano de Saúde",
            "magistrado": "Dra. Amanda Cavalcante",
            "comarca": "3ª Vara Cível de Maceió",
            "autor": "Ricardo Mendes Alves",
            "reu": "Operadora Unimed S.A.",
            "resumo": "Negativa abusiva de cirurgia oncológica e tratamento prescrito pelo médico assistente.",
            "resultado": "Em Analise",
            "data_julgamento": "2026-10-01",
        },
    )
    assert resp_manual.status_code == 201, resp_manual.text
    manual_body = resp_manual.json()
    manual_id = manual_body["id_processo"]

    csv_id = None
    try:
        pred_m = manual_body["analise_preditiva"]
        assert pred_m["casos_similares_encontrados"] <= total_antes
        assert pred_m["margem_confianca"] == compute_wilson_margin(
            pred_m["probabilidade_deferimento"], pred_m["casos_similares_encontrados"]
        )

        csv_bytes = (
            "numero_processo,tema,magistrado,comarca,autor,reu,texto_resumo,resultado,data_julgamento\n"
            f"{cnj_csv},Tributário,Dr. Marcelo Lins,Vara da Fazenda Pública,Empresa Alfa LTDA,Fazenda Pública Estadual,"
            "Repetição de indébito tributário de ICMS sobre base de cálculo indevida.,Procedente,2026-10-15\n"
        ).encode("utf-8")

        resp_csv = client.post(
            "/api/v1/processos/upload-csv",
            files={"file": ("etapa4_lote.csv", io.BytesIO(csv_bytes), "text/csv")},
        )
        assert resp_csv.status_code == 200, resp_csv.text

        lista = client.get("/api/v1/processos", params={"busca": cnj_csv}).json()
        assert lista["total"] == 1
        csv_id = lista["itens"][0]["id_processo"]
        det_csv = client.get(f"/api/v1/processos/{csv_id}").json()
        pred_c = det_csv["analise_preditiva"]
        assert pred_c["casos_similares_encontrados"] <= (total_antes + 1)
        assert pred_c["margem_confianca"] == compute_wilson_margin(
            pred_c["probabilidade_deferimento"], pred_c["casos_similares_encontrados"]
        )
    finally:
        client.delete(f"/api/v1/processos/{manual_id}")
        if csv_id:
            client.delete(f"/api/v1/processos/{csv_id}")
