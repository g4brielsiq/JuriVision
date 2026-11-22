"""
Suíte de Verificação Exaustiva da Etapa 3 — Endurecimento da Barreira LGPD
(E-mails, Telefones, Endereços/CEP, Documentos Extras e Nomes em Prosa Contínua).
"""
import io
from typing import Iterator
import uuid

from fastapi.testclient import TestClient
import pytest

from app.core.ai_gateway import AnonimizadorLGPD
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


def test_etapa3_mascara_emails_e_telefones_preservando_cnj():
    """Deve mascarar e-mails e múltiplos formatos de telefone/WhatsApp sem corromper números CNJ."""
    cnj = "0088210-12.2026.8.02.0001"
    texto = (
        f"Autos do processo nº {cnj}. Contato da parte pelo e-mail maria.clara@escritorio.com.br, "
        "telefone (82) 99999-8888, WhatsApp +55 82 98877-6655 ou Tel: 11 3344-5566."
    )
    higienizado, docs_count, _ = AnonimizadorLGPD.sanitize_text(texto)

    assert cnj in higienizado
    assert "maria.clara@escritorio.com.br" not in higienizado
    assert "(82) 99999-8888" not in higienizado
    assert "98877-6655" not in higienizado
    assert "3344-5566" not in higienizado
    assert "[EMAIL_ANONIMIZADO]" in higienizado
    assert higienizado.count("[TELEFONE_ANONIMIZADO]") == 3
    assert docs_count == 4


def test_etapa3_mascara_enderecos_cep_e_documentos_extras():
    """Deve mascarar endereços residenciais, CEPs e documentos civis (CNH, CTPS, PIS, CNS)."""
    texto = (
        "O requerente, residente e domiciliado na Rua das Acácias, nº 245, Farol, CEP 57055-120, "
        "portador da CNH: 04567891230, CTPS 998877/0012 e PIS 123.45678.90-1, "
        "também recebeu correspondência na Avenida Fernandes Lima, 1200, apto 302."
    )
    higienizado, docs_count, _ = AnonimizadorLGPD.sanitize_text(texto)

    assert "Rua das Acácias" not in higienizado
    assert "245" not in higienizado
    assert "57055-120" not in higienizado
    assert "04567891230" not in higienizado
    assert "998877/0012" not in higienizado
    assert "123.45678.90-1" not in higienizado
    assert "Avenida Fernandes Lima" not in higienizado
    assert "1200" not in higienizado
    assert "[CEP_ANONIMIZADO]" in higienizado
    assert "[ENDERECO_ANONIMIZADO]" in higienizado
    assert higienizado.count("[DOC_ANONIMIZADO]") == 3
    assert docs_count >= 6


def test_etapa3_detecta_nomes_em_prosa_sem_dois_pontos_e_qualificacao_civil():
    """Deve detectar nomes sem dois-pontos, em locuções de propositura e em qualificação civil."""
    texto = (
        "Autora Maria Clara Dias questiona cobrança abusiva. "
        "A ação foi movida por Pedro Henrique Albuquerque em face de José Roberto Teixeira. "
        "Ainda na inicial, Fernando Augusto Magalhães, brasileiro, casado, inscrito no CPF 123.456.789-00, "
        "prestou declarações com a Testemunha Ana Paula Souza."
    )
    higienizado, docs_count, names_count = AnonimizadorLGPD.sanitize_text(texto)

    for nome in (
        "Maria Clara Dias",
        "Pedro Henrique Albuquerque",
        "José Roberto Teixeira",
        "Fernando Augusto Magalhães",
        "Ana Paula Souza",
    ):
        assert nome not in higienizado

    assert "123.456.789-00" not in higienizado
    assert "Maria C. ***" in higienizado
    assert "Pedro H. ***" in higienizado
    assert "José R. ***" in higienizado
    assert "Fernando A. ***" in higienizado
    assert "Ana P. ***" in higienizado
    assert docs_count >= 1
    assert names_count >= 5


def test_etapa3_mascara_variacoes_parciais_e_sobrenomes_de_partes_conhecidas():
    """Deve mascarar prenome composto, Sr./Sra. + sobrenome e sobrenome isolado de partes conhecidas."""
    texto = (
        "João Carlos Albuquerque firmou contrato bancário. Posteriormente, João Carlos contestou "
        "a cobrança e o Sr. Albuquerque notificou a instituição. Albuquerque juntou extratos. "
        "Processo julgado pela Dra. Maria Silva."
    )
    higienizado, _, names_count = AnonimizadorLGPD.sanitize_text(
        texto, known_natural_names=["João Carlos Albuquerque"]
    )

    assert "Albuquerque" not in higienizado
    assert "João Carlos" not in higienizado
    assert "Sr. Albuquerque" not in higienizado
    assert "João C. ***" in higienizado
    assert "Dra. Maria Silva" in higienizado
    assert names_count >= 3


def test_etapa3_zero_falso_positivo_em_empresas_magistrados_e_termos_juridicos():
    """Empresas, órgãos públicos, magistrados e institutos jurídicos devem permanecer intactos."""
    texto = (
        "Ação movida contra Banco Bradesco S.A. e Operadora Unimed Maceió S.A. perante a "
        "1ª Vara Cível de Maceió sob presidência do Dr. Rafael De Amorim e da Dra. Maria Silva, "
        "com aplicação do Código de Defesa do Consumidor e da Súmula 385 do Superior Tribunal de Justiça, "
        "bem como precedente da Construtora Horizonte LTDA."
    )
    higienizado, _, _ = AnonimizadorLGPD.sanitize_text(texto)

    for entidade in (
        "Banco Bradesco S.A.",
        "Operadora Unimed Maceió S.A.",
        "1ª Vara Cível de Maceió",
        "Dr. Rafael De Amorim",
        "Dra. Maria Silva",
        "Código de Defesa do Consumidor",
        "Superior Tribunal de Justiça",
        "Construtora Horizonte LTDA",
    ):
        assert entidade in higienizado


def test_etapa3_integracao_end_to_end_previa_e_upload_pdf(client: TestClient):
    """Prévia de anonimização e upload de PDF em prosa devem blindar todo o pacote de PII."""
    previa = client.post(
        "/api/v1/processos/anonimizacao/previa",
        json={
            "autor": "Beatriz Helena Moura",
            "reu": "José Carlos Pereira",
            "resumo": (
                "Beatriz Helena Moura, brasileira, solteira, residente e domiciliada na Rua do Sol, nº 50, "
                "CEP 57020-070, e-mail beatriz@cliente.com, celular (82) 99123-4567, move ação contra "
                "José Carlos Pereira com base na CNH 98765432100."
            ),
        },
    )
    assert previa.status_code == 200, previa.text
    prev_body = previa.json()
    assert prev_body["partes_anonimizadas"]["autor"] == "Beatriz H. ***"
    assert prev_body["partes_anonimizadas"]["reu"] == "José C. ***"
    for dado_sensivel in (
        "Beatriz Helena Moura",
        "José Carlos Pereira",
        "Rua do Sol",
        "57020-070",
        "beatriz@cliente.com",
        "99123-4567",
        "98765432100",
    ):
        assert dado_sensivel not in prev_body["resumo"]
    assert prev_body["auditoria_lgpd"]["total_cpfs_mascarados"] >= 5

    cnj = _numero_cnj_unico()
    pdf_bytes = _build_pdf_document(
        [
            f"Processo {cnj}",
            "Acao indenizatoria ajuizada por Beatriz Helena Moura em face de Companhia Aerea Linhas Brasil S.A.",
            "Contato beatriz@cliente.com telefone (82) 99123-4567 residente na Rua do Sol, 50 CEP 57020-070.",
            "Cancelamento de voo internacional sem assistencia material.",
        ]
    )
    resp_pdf = client.post(
        "/api/v1/processos/upload-pdf",
        files={"file": ("peticao_prosa_lgpd.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp_pdf.status_code == 200, resp_pdf.text
    body = resp_pdf.json()
    proc_id = body["id_processo"]
    try:
        assert body["metadados_extraidos"]["partes_anonimizadas"]["autor"] == "Beatriz H. ***"
        assert body["metadados_extraidos"]["partes_anonimizadas"]["reu"] == "Companhia Aerea Linhas Brasil S.A."
        assert "Beatriz Helena Moura" not in body["resumo_nlp"]
        assert "beatriz@cliente.com" not in body["resumo_nlp"]
        assert "99123-4567" not in body["resumo_nlp"]
        assert "Rua do Sol" not in body["resumo_nlp"]
        assert "57020-070" not in body["resumo_nlp"]
        assert body["auditoria_lgpd"]["total_cpfs_mascarados"] >= 4
    finally:
        client.delete(f"/api/v1/processos/{proc_id}")
