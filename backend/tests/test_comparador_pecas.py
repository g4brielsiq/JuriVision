"""
Suíte de Testes Automatizados: Visualizador Comparativo de Peças Jurídicas (Petição Inicial vs. Contestação).
Rastreabilidade:
- Art. 357 do CPC (Saneamento Processual)
- RN-01: Invariante de Anonimização LGPD
- RN-02: Jurimetria Granular por Ponto Controvertido
- RN-04 / SEC-05: Validação de Entrada e Limites de Payload
"""
import io
import pytest
from fastapi.testclient import TestClient

from app.core.ai_gateway import ExtratorDocumental
from app.main import app, init_db_and_seed
from app.routers.relatorios import _build_pdf_document
from app.schemas.comparacao import ResultadoComparacaoPecas, StatusTese, TipoTese


@pytest.fixture(scope="module")
def client() -> TestClient:
    init_db_and_seed()
    with TestClient(app) as test_client:
        yield test_client


def _make_pdf(lines: list[str]) -> bytes:
    return _build_pdf_document(lines)


def test_extrator_documental_page_markers_e_macro_secoes():
    """Valida a injeção determinística de tags [PÁG XX] e a segmentação estrutural por macro-seções."""
    lines_p1 = [
        "EXCELENTISSIMO SENHOR JUIZ DA 1a VARA CIVEL DE MACEIO",
        "Processo: 0077889-11.2026.8.02.0001",
        "DOS FATOS",
        "O autor celebrou contrato de prestacao de servicos em 10/01/2026.",
        "O servico restou inadimplido em 15/02/2026 gerando prejuizo de R$ 25.000,00.",
    ]
    pdf_bytes = _make_pdf(lines_p1)
    text, pages = ExtratorDocumental.extract_text_with_page_markers(pdf_bytes)

    assert "[PÁG 01]" in text
    assert len(pages) >= 1
    assert "DOS FATOS" in text

    sections = ExtratorDocumental.segment_macro_sections(text)
    assert "fatos" in sections
    assert len(sections["fatos"]) > 0


def test_comparador_upload_arquivos_validos_retorna_200_e_schema(client: TestClient):
    """Valida o endpoint POST /api/v1/processos/comparar-pecas com dois PDFs válidos."""
    linhas_inicial = [
        "EXCELENTISSIMO SENHOR JUIZ DA 1a VARA CIVEL DE MACEIO",
        "Processo: 0088990-22.2026.8.02.0001",
        "Autor: Carlos Eduardo Santos, inscrito no CPF 111.222.333-44.",
        "DOS FATOS",
        "Em 10/05/2026 ocorreu o descumprimento contratual no valor de R$ 50.000,00.",
        "DOS PEDIDOS",
        "Requer a condenação da ré ao pagamento da indenização cabível.",
    ]
    linhas_contestacao = [
        "EXCELENTISSIMO SENHOR JUIZ DA 1a VARA CIVEL DE MACEIO",
        "Processo: 0088990-22.2026.8.02.0001",
        "Reu: Companhia Comercial Alfa S.A.",
        "DAS PRELIMINARES",
        "Argui preliminar de ilegitimidade passiva ad causam.",
        "DO MERITO",
        "Impugna expressamente a data de 10/05/2026 e o valor pleiteado de R$ 50.000,00.",
    ]

    pdf_inicial = _make_pdf(linhas_inicial)
    pdf_contestacao = _make_pdf(linhas_contestacao)

    resp = client.post(
        "/api/v1/processos/comparar-pecas",
        files={
            "peticao_inicial": ("peticao_inicial.pdf", io.BytesIO(pdf_inicial), "application/pdf"),
            "contestacao": ("contestacao.pdf", io.BytesIO(pdf_contestacao), "application/pdf"),
        },
    )
    assert resp.status_code == 200
    data = resp.json()

    # Validação do contrato Pydantic
    parsed = ResultadoComparacaoPecas.model_validate(data)
    assert parsed.id_comparacao.startswith("comp-")
    assert parsed.numero_processo == "0088990-22.2026.8.02.0001"
    assert parsed.total_teses >= 1
    assert parsed.score_geral_favorabilidade_autor_pct >= 0.0
    assert len(parsed.teses) >= 1

    tese = parsed.teses[0]
    assert tese.tipo in TipoTese
    assert tese.status in StatusTese
    assert 0.0 <= tese.probabilidade_procedencia_pct <= 100.0
    assert len(tese.impacto_processual) > 10


def test_comparador_formato_invalido_retorna_422(client: TestClient):
    """Arquivos que não sejam PDF devem ser rejeitados com HTTP 422."""
    resp = client.post(
        "/api/v1/processos/comparar-pecas",
        files={
            "peticao_inicial": ("inicial.txt", io.BytesIO(b"conteudo texto"), "text/plain"),
            "contestacao": ("contestacao.pdf", io.BytesIO(b"%PDF-1.4 valido"), "application/pdf"),
        },
    )
    assert resp.status_code == 422
    assert "extensão .pdf" in resp.json()["detail"]


def test_comparador_bytes_corrompidos_retorna_422(client: TestClient):
    """PDF sem assinatura %PDF- ou corrompido deve retornar HTTP 422."""
    resp = client.post(
        "/api/v1/processos/comparar-pecas",
        files={
            "peticao_inicial": ("inicial.pdf", io.BytesIO(b"cabecalho corrompido sem pdf"), "application/pdf"),
            "contestacao": ("contestacao.pdf", io.BytesIO(b"%PDF-1.4 conteudo minimo"), "application/pdf"),
        },
    )
    assert resp.status_code == 422
    assert "ErroProcessamento" in resp.json()["detail"]


def test_comparador_arquivo_acima_limite_15mb_retorna_413(client: TestClient):
    """Upload acima do teto de 15MB deve retornar HTTP 413 (RN-04 / SEC-05)."""
    oversized = b"%PDF-1.4\n" + b"0" * (15 * 1024 * 1024)
    valid_pdf = _make_pdf(["Linha de teste"])

    resp = client.post(
        "/api/v1/processos/comparar-pecas",
        files={
            "peticao_inicial": ("gigante.pdf", io.BytesIO(oversized), "application/pdf"),
            "contestacao": ("contestacao.pdf", io.BytesIO(valid_pdf), "application/pdf"),
        },
    )
    assert resp.status_code == 413
    assert "15MB" in resp.json()["detail"]


def test_comparador_barreira_lgpd_em_ambas_as_pecas(client: TestClient):
    """Garante que nenhum CPF, RG ou nome de pessoa física transponha a barreira para ambas as peças (RN-01)."""
    linhas_inicial = [
        "Autor: Marcos Vinicius Albuquerque, inscrito no CPF 987.654.321-99 e RG: 11.222.333-4.",
        "Reu: Banco Financeiro S.A.",
        "DOS FATOS",
        "A cobranca indevida gerou dano moral de R$ 10.000,00.",
    ]
    linhas_contestacao = [
        "Reu: Banco Financeiro S.A.",
        "Autor: Marcos Vinicius Albuquerque.",
        "DO MERITO",
        "O titular CPF 987.654.321-99 estava ciente das taxas administrativas.",
    ]

    pdf_inicial = _make_pdf(linhas_inicial)
    pdf_contestacao = _make_pdf(linhas_contestacao)

    resp = client.post(
        "/api/v1/processos/comparar-pecas",
        files={
            "peticao_inicial": ("peticao_inicial.pdf", io.BytesIO(pdf_inicial), "application/pdf"),
            "contestacao": ("contestacao.pdf", io.BytesIO(pdf_contestacao), "application/pdf"),
        },
    )
    assert resp.status_code == 200
    data = resp.json()

    # Invariante RN-01: zero vazamento de PII nos textos higienizados
    assert "987.654.321-99" not in data["texto_higienizado_autor"]
    assert "987.654.321-99" not in data["texto_higienizado_reu"]
    assert "11.222.333-4" not in data["texto_higienizado_autor"]
    assert "Albuquerque" not in data["texto_higienizado_autor"]
    assert "Albuquerque" not in data["texto_higienizado_reu"]
    assert "[CPF_ANONIMIZADO]" in data["texto_higienizado_autor"]
    assert "[CPF_ANONIMIZADO]" in data["texto_higienizado_reu"]


def test_comparador_varredura_bidirecional_e_eixos_juridicos(client: TestClient):
    """
    Etapa 2: Testa a varredura bidirecional completa:
    - Varredura Direta (Autor -> Réu): divergências em fatos/valores, omissões (art. 341 CPC).
    - Varredura Reversa (Réu -> Autor): defesas indiretas inéditas (art. 350 CPC / fato_novo_ou_extintivo_reu).
    """
    linhas_inicial = [
        "EXCELENTISSIMO SENHOR JUIZ DE DIREITO DA 1a VARA CIVEL",
        "Processo: 0099334-15.2026.8.02.0001",
        "DOS FATOS",
        "O autor contratou o servico e o inadimplemento ocorreu em 15/04/2026 gerando dano de R$ 30.000,00.",
        "DO DIREITO E DANO MORAL",
        "Houve grave falha na prestacao de servicos ensejando dever de indenizar pelos transtornos sofridos.",
        "DA INVERSAO DO ONUS DA PROVA",
        "Requer a inversao do onus da prova nos termos do art. 6, VIII, do CDC.",
        "DOS PEDIDOS",
        "Requer a condenação da ré ao pagamento de R$ 30.000,00.",
    ]

    linhas_contestacao = [
        "EXCELENTISSIMO SENHOR JUIZ DE DIREITO DA 1a VARA CIVEL",
        "Processo: 0099334-15.2026.8.02.0001",
        "DAS PREJUDICIAIS DE MERITO",
        "Argui expressamente a prescrição quinquenal da pretensão autoral nos termos da lei.",
        "DO MERITO",
        "Impugna a data de 15/04/2026 e sustenta mero dissabor cotidiano sem dever de indenizar.",
        "A re impugna expressamente o valor pleiteado aduzindo excesso manifesto.",
    ]

    pdf_inicial = _make_pdf(linhas_inicial)
    pdf_contestacao = _make_pdf(linhas_contestacao)

    resp = client.post(
        "/api/v1/processos/comparar-pecas",
        files={
            "peticao_inicial": ("peticao_inicial.pdf", io.BytesIO(pdf_inicial), "application/pdf"),
            "contestacao": ("contestacao.pdf", io.BytesIO(pdf_contestacao), "application/pdf"),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    parsed = ResultadoComparacaoPecas.model_validate(data)

    assert parsed.total_teses >= 3
    statuses = {t.status for t in parsed.teses}
    tipos = {t.tipo for t in parsed.teses}

    # Deve conter divergência e fato novo da defesa
    assert StatusTese.DIVERGENTE in statuses
    assert StatusTese.FATO_NOVO_DEFESA in statuses

    # Varredura reversa: Fato novo da defesa (prescrição) não tem trecho do autor
    tese_prescricao = next((t for t in parsed.teses if t.status == StatusTese.FATO_NOVO_DEFESA), None)
    assert tese_prescricao is not None
    assert tese_prescricao.trecho_autor is None
    assert tese_prescricao.pagina_autor is None
    assert tese_prescricao.trecho_reu is not None
    assert "prescri" in tese_prescricao.trecho_reu.lower()
    assert tese_prescricao.tipo == TipoTese.PREJUDICIAL_MERITO

    # Varredura direta: Omissão (inversão do ônus da prova não impugnada especificamente)
    tese_omissao = next((t for t in parsed.teses if t.status == StatusTese.INCONTROVERSO_POR_OMISSAO), None)
    if tese_omissao:
        assert tese_omissao.trecho_autor is not None
        assert tese_omissao.trecho_reu is None
        assert tese_omissao.pagina_reu is None


def test_gemini_adapter_fallback_local_resiliente():
    """Valida o funcionamento do GeminiAIAdapter com fallback determinístico local imediato."""
    from app.core.ai_gateway import GeminiAIAdapter
    adapter = GeminiAIAdapter()
    resultado = adapter.comparar_pecas(
        texto_inicial="Petição inicial alegando inadimplemento em 12/03/2026 com dano de R$ 15.000,00.",
        texto_contestacao="Contestação impugnando a data de 12/03/2026 e o dano moral por mero dissabor.",
        numero_processo="0011223-44.2026.8.02.0001",
    )
    assert isinstance(resultado, ResultadoComparacaoPecas)
    assert resultado.numero_processo == "0011223-44.2026.8.02.0001"
    assert resultado.total_teses >= 1
    assert resultado.total_divergencias >= 1


def test_comparador_jurimetria_granular_por_tese(client: TestClient):
    """
    Etapa 3: Testa a jurimetria granular por tese (RN-02):
    - Probabilidade calibrada no intervalo [0.0, 100.0]
    - Omissão (Art. 341 CPC) com probabilidade elevada (>= 85%) por presunção relativa de veracidade
    - Presença de fundamentação preditiva e impacto processual estratégico
    """
    linhas_inicial = [
        "Processo: 0044556-77.2026.8.02.0001",
        "Magistrado: Dr. Rafael De Amorim",
        "DOS FATOS",
        "O inadimplemento ocorreu em 01/06/2026 gerando prejuizo de R$ 20.000,00.",
        "DO DIREITO",
        "Requer indenizacao por danos morais e materiais decorrentes do descumprimento.",
    ]
    linhas_contestacao = [
        "Processo: 0044556-77.2026.8.02.0001",
        "DO MERITO",
        "A ré impugna a data de 01/06/2026.",
        # Não impugna o valor de R$ 20.000,00 nem os danos morais
    ]

    pdf_inicial = _make_pdf(linhas_inicial)
    pdf_contestacao = _make_pdf(linhas_contestacao)

    resp = client.post(
        "/api/v1/processos/comparar-pecas",
        files={
            "peticao_inicial": ("inicial.pdf", io.BytesIO(pdf_inicial), "application/pdf"),
            "contestacao": ("contestacao.pdf", io.BytesIO(pdf_contestacao), "application/pdf"),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    parsed = ResultadoComparacaoPecas.model_validate(data)

    for t in parsed.teses:
        assert 0.0 <= t.probabilidade_procedencia_pct <= 100.0
        assert len(t.fundamentacao_preditiva) > 15
        assert len(t.impacto_processual) > 10

    # Ponto de omissão deve ter probabilidade >= 85%
    omissao = next((t for t in parsed.teses if t.status == StatusTese.INCONTROVERSO_POR_OMISSAO), None)
    if omissao:
        assert omissao.probabilidade_procedencia_pct >= 85.0
        assert "341" in omissao.fundamentacao_preditiva or "341" in omissao.impacto_processual


