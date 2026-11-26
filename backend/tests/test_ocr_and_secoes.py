"""
Suíte de Testes Automatizados para Segmentação de Seções de Petições e Fallback de OCR (ISO 29119).
Rastreabilidade:
- MODELING.md: RF-02 (Ingestão PDF), RF-04 / RN-01 (Barreira LGPD), RF-05 (Síntese Factual), RNF-05 (Tolerância a Falhas)
- ARCHITECTURE.md: ADR-002 (Port & Adapter + Fallback Local), Seção 8.3 e Seção 8.7
"""
from dataclasses import replace
import io
from unittest.mock import MagicMock, patch
import pytest

import app.core.ai_gateway as gateway_mod
from app.core.ai_gateway import (
    AnonimizadorLGPD,
    ExtratorDocumental,
    LocalDeterministicFallbackAdapter,
    SegmentadorPeticao,
)
from app.core.config import settings
from app.routers.relatorios import _build_pdf_document
from app.schemas.contracts import ContextoHistoricoSchema, InternalAnalyzeRequest, SecoesPeticaoSchema


def _build_scanned_image_pdf(metadata_subject: str = "") -> bytes:
    """Constrói um PDF sintético de imagem pura (sem operadores Tj/BT) para simular documento escaneado."""
    raw_img = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb"
    stream_ops = b"q 595 0 0 842 0 0 cm /Im1 Do Q\n"
    meta_part = f"<< /Title (Peticao Digitalizada) /Subject ({metadata_subject}) >>\n" if metadata_subject else ""

    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /XObject << /Im1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n",
        f"4 0 obj\n<< /Type /XObject /Subtype /Image /Width 10 /Height 10 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Length {len(raw_img)} >>\nstream\n".encode(
            "latin-1"
        )
        + raw_img
        + b"\nendstream\nendobj\n",
        f"5 0 obj\n<< /Length {len(stream_ops)} >>\nstream\n".encode("latin-1")
        + stream_ops
        + b"\nendstream\nendobj\n",
    ]
    if meta_part:
        objects.append(f"6 0 obj\n{meta_part}endobj\n".encode("latin-1"))

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1"))
    for off in offsets:
        pdf.extend(f"{off:010d} 00000 n \n".encode("latin-1"))

    info_ref = " /Info 6 0 R" if meta_part else ""
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R{info_ref} >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "latin-1"
        )
    )
    return bytes(pdf)


# ==============================================================================
# 1. Testes de Segmentação de Seções (SegmentadorPeticao)
# ==============================================================================
def test_segmentacao_secoes_formais_completa():
    """Valida a segmentação de uma petição com divisões formais: Preliminares, Fatos, Direito e Pedidos."""
    texto = """EXCELENTÍSSIMO SENHOR JUIZ DE DIREITO DA 1ª VARA CÍVEL DE MACEIÓ/AL
Processo nº 0801234-56.2026.8.02.0001
Autor: Lucas Gabriel
Réu: Banco do Brasil S.A.

I - DAS PRELIMINARES
Requer a concessão dos benefícios da gratuidade de justiça nos termos do art. 98 do CPC.

II - DOS FATOS
O Autor é correntista da instituição financeira ré desde 2020.
No dia 10 de fevereiro de 2026, foi surpreendido com descontos indevidos em sua conta corrente referentes a tarifas não contratadas.
Tais descontos totalizaram a quantia de R$ 3.500,00, gerando saldo negativo e restrição ao crédito.

III - DO DIREITO
Aplica-se ao caso a teoria do risco da atividade e o Código de Defesa do Consumidor (Súmula 297 do STJ).
A responsabilidade civil da instituição financeira é objetiva, conforme expressa o art. 14 do CDC.
A jurisprudência do TJAL pacificou que a cobrança fraudulenta gera dano moral in re ipsa.

IV - DOS PEDIDOS
Ante o exposto, requer a Vossa Excelência:
a) O deferimento da justiça gratuita;
b) A repetição do indébito em dobro, totalizando R$ 7.000,00;
c) A condenação da Ré em danos morais no valor de R$ 10.000,00.
Nestes termos, pede deferimento.
"""
    secoes = SegmentadorPeticao.segmentar(texto)

    assert "EXCELENTÍSSIMO SENHOR JUIZ" in (secoes.cabecalho or "")
    assert "gratuidade de justiça" in (secoes.preliminares or "")
    assert "descontos indevidos em sua conta corrente" in secoes.dos_fatos
    assert "Aplica-se ao caso a teoria do risco" in secoes.do_direito
    assert "repetição do indébito em dobro" in secoes.dos_pedidos


def test_segmentacao_variacoes_cabecalhos():
    """Testa a robustez do regex com diferentes grafias, números arábicos/romanos, markdown e pontuações."""
    # Variação com Markdown e numeração arábica
    texto_md = """Qualificação inicial
## 1. Dos Fatos:
O autor sofreu atraso de voo de 12 horas.
## 2. Do Direito:
Aplica-se o CDC e a jurisprudência sobre responsabilidade objetiva.
## 3. Dos Pedidos e Requerimentos:
Requer indenização de R$ 5.000,00."""

    secoes_md = SegmentadorPeticao.segmentar(texto_md)
    assert "atraso de voo" in secoes_md.dos_fatos
    assert "responsabilidade objetiva" in secoes_md.do_direito
    assert "Requer indenização" in secoes_md.dos_pedidos

    # Variação com títulos sem numeração em maiúsculas
    texto_upper = """Cabeçalho simples
DOS FATOS
O consumidor teve seu nome inserido no SPC indevidamente.
DO MÉRITO
Inexistência de débito e ato ilícito.
DOS PEDIDOS
A exclusão do apontamento restritivo."""

    secoes_upper = SegmentadorPeticao.segmentar(texto_upper)
    assert "inserido no SPC" in secoes_upper.dos_fatos
    assert "Inexistência de débito" in secoes_upper.do_direito
    assert "exclusão do apontamento" in secoes_upper.dos_pedidos


def test_segmentacao_heuristica_sem_titulos_formais():
    """Garante que petições informais ou sem títulos de seção sejam particionadas por heurística fática/jurídica."""
    texto_informal = """EXCELENTISSIMO SENHOR DOUTOR JUIZ DA 2a VARA CIVEL DE MACEIO
Autor: Joao Silva
Reu: Companhia Aerea Alfa

O passageiro adquiriu bilhete para trecho Maceio-Recife. No horario previsto, a aeronave nao decolou por manutencao nao programada.
Em razao do cancelamento injustificado, o autor perdeu consulta medica especializada.

O artigo 14 do Código de Defesa do Consumidor estipula a responsabilidade objetiva por danos causados na prestacao de servicos. A jurisprudencia do TJAL ampara o pleito.

Diante de todo o exposto, requer a citacao da re e a condenacao em indenizacao no valor de 8 mil reais. Pede deferimento."""

    secoes = SegmentadorPeticao.segmentar(texto_informal)
    assert "adquiriu bilhete para trecho" in secoes.dos_fatos
    assert "artigo 14 do Código de Defesa do Consumidor" in secoes.do_direito
    assert "requer a citacao da re" in secoes.dos_pedidos
    assert "EXCELENTISSIMO SENHOR" in (secoes.cabecalho or "")


def test_segmentacao_texto_vazio_ou_nulo():
    """Valida comportamento defensivo para texto vazio."""
    assert SegmentadorPeticao.segmentar("").dos_fatos == ""
    assert SegmentadorPeticao.segmentar("   \n\t  ").do_direito == ""
    d = SegmentadorPeticao.segmentar_dict("")
    assert isinstance(d, dict) and "dos_fatos" in d


# ==============================================================================
# 2. Testes de Extração de PDF e Fallback de OCR (ExtratorDocumental)
# ==============================================================================
def test_extrator_pdf_digital_legitimo():
    """Garante que documentos com camada digital continuem sendo lidos normalmente via pypdf."""
    linhas = [
        "EXCELENTISSIMO SENHOR JUIZ DA 1a VARA CIVEL DE MACEIO",
        "Processo: 0011223-44.2026.8.02.0001",
        "Autor: Carlos Eduardo",
        "Reu: Concessionaria de Energia S.A.",
        "Trata-se de acao indenizatoria por interrupcao indevida de fornecimento eletrico.",
    ]
    pdf_bytes = _build_pdf_document(linhas)
    extraido = ExtratorDocumental.extract_text_from_pdf_bytes(pdf_bytes)

    assert "0011223-44.2026.8.02.0001" in extraido
    assert "interrupcao indevida de fornecimento" in extraido


def test_extrator_pdf_escaneado_fallback_ocr_customizado():
    """Verifica se um PDF composto por imagens ativa com sucesso o provedor customizado de OCR."""
    scanned_pdf = _build_scanned_image_pdf()

    texto_transcrito_esperado = (
        "Processo 0809999-12.2026.8.02.0001\n"
        "Autor: Mariana Costa\n"
        "Réu: Hospital Unimed Maceió\n"
        "DOS FATOS\n"
        "A paciente teve cirurgia emergencial negada indevidamente pelo plano.\n"
        "DO DIREITO\n"
        "Aplicação do CDC e da Súmula 102 do Tribunal de Justiça.\n"
        "DOS PEDIDOS\n"
        "Requer o custeio integral do procedimento cirúrgico."
    )

    mock_ocr = MagicMock(return_value=texto_transcrito_esperado)
    ExtratorDocumental.register_ocr_provider(mock_ocr)

    try:
        resultado = ExtratorDocumental.extract_text_from_pdf_bytes(scanned_pdf)
        assert mock_ocr.called
        assert "Mariana Costa" in resultado
        assert "DOS FATOS" in resultado
    finally:
        ExtratorDocumental.reset_ocr_provider()


def test_extrator_pdf_escaneado_fallback_ocr_local_heuristico():
    """Testa recuperação determinística de texto em PDF escaneado através de metadados embutidos de OCR."""
    metadados_ocr = (
        "Processo: 0805555-88.2026.8.02.0001. "
        "Autor: Jose dos Santos. "
        "DOS FATOS: Passageiro sofreu overbooking. "
        "DO DIREITO: CDC artigo 14. "
        "DOS PEDIDOS: Requer danos morais."
    )
    scanned_pdf = _build_scanned_image_pdf(metadata_subject=metadados_ocr)

    ExtratorDocumental.reset_ocr_provider()
    resultado = ExtratorDocumental.extract_text_from_pdf_bytes(scanned_pdf)

    assert "0805555-88.2026.8.02.0001" in resultado
    assert "overbooking" in resultado


def test_extrator_pdf_escaneado_fallback_gemini_multimodal():
    """Simula chamada de OCR multimodal com Gemini API sobre documento escaneado."""
    scanned_pdf = _build_scanned_image_pdf()

    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                "Processo 0801111-22.2026.8.02.0001\n"
                                "Autor: Fernando Ramos\n"
                                "DOS FATOS\nVoo cancelado.\n"
                                "DO DIREITO\nArt. 14 CDC.\n"
                                "DOS PEDIDOS\nRequer R$ 10.000,00."
                            )
                        }
                    ]
                }
            }
        ]
    }

    custom_settings = replace(settings, GEMINI_API_KEY="test_key_gemini", AI_PROVIDER="gemini")
    with patch.object(gateway_mod, "settings", custom_settings):
        with patch("httpx.Client.post", return_value=mock_res):
            with patch.object(ExtratorDocumental, "_is_scanned_pdf", return_value=True):
                texto_gemini = ExtratorDocumental._ocr_via_gemini(scanned_pdf)
                assert texto_gemini is not None
                assert "Fernando Ramos" in texto_gemini
                assert "Voo cancelado" in texto_gemini


def test_extrator_pdf_escaneado_sem_texto_lanca_falha_ocr():
    """Garante que um PDF de imagem completamente ilegível e sem metadados acione o erro esperado de FalhaOCR."""
    scanned_pdf_mudo = _build_scanned_image_pdf()  # sem metadata_subject

    ExtratorDocumental.reset_ocr_provider()
    with pytest.raises(ValueError) as excinfo:
        ExtratorDocumental.extract_text_from_pdf_bytes(scanned_pdf_mudo)

    assert "FalhaOCR" in str(excinfo.value)


def test_extrator_documento_invalido_rejeita():
    """Garante que arquivos corrompidos ou não-PDF sejam prontamente rejeitados."""
    with pytest.raises(ValueError) as exc:
        ExtratorDocumental.extract_text_from_pdf_bytes(b"")
    assert "Arquivo vazio" in str(exc.value)

    with pytest.raises(ValueError) as exc2:
        ExtratorDocumental.extract_text_from_pdf_bytes(b"NOT_A_PDF_FILE_HEADER")
    assert "Assinatura binária inválida" in str(exc2.value)


def test_extrator_extract_text_and_sections_helper():
    """Testa a operação atômica de extrair texto e segmentar seções."""
    linhas = [
        "Processo: 0807777-33.2026.8.02.0001",
        "DOS FATOS",
        "Houve extravio definitivo de bagagem em voo doméstico.",
        "DO DIREITO",
        "A responsabilidade da transportadora aérea é objetiva.",
        "DOS PEDIDOS",
        "Requer o pagamento de indenização por dano material e moral.",
    ]
    pdf = _build_pdf_document(linhas)
    texto, secoes = ExtratorDocumental.extract_text_and_sections(pdf)

    assert "0807777-33.2026.8.02.0001" in texto
    assert "extravio definitivo de bagagem" in secoes.dos_fatos
    assert "responsabilidade da transportadora" in secoes.do_direito
    assert "Requer o pagamento" in secoes.dos_pedidos


# ==============================================================================
# 3. Testes de Integração com o AI Gateway e Barreira LGPD (RN-01 / RF-04)
# ==============================================================================
def test_ai_gateway_fallback_com_secoes_e_lgpd():
    """
    Valida a integração completa entre segmentação de seções, sumarização factual (RF-05)
    e a barreira determinística LGPD (RN-01) no LocalDeterministicFallbackAdapter.
    """
    texto_peticao = """EXCELENTÍSSIMO SENHOR JUIZ DA 1ª VARA CÍVEL DE MACEIÓ
Processo nº 0801234-56.2026.8.02.0001
Autor: Lucas Gabriel Rodrigues, CPF: 111.222.333-44, RG: 12.345.678-9
Réu: Companhia Aérea Linhas Brasil S.A.

I - DOS FATOS
No dia 12 de janeiro de 2026, o Autor Lucas Gabriel Rodrigues compareceu ao aeroporto de Maceió com antecedência.
Ocorre que a ré cancelou o voo sem prestar alimentação ou hospedagem adequada.
O cancelamento causou a perda de uma reunião profissional decisiva.

II - DO DIREITO
Aplica-se o Código de Defesa do Consumidor (art. 14 do CDC).
O atraso e cancelamento injustificado sem assistência material configura dano moral in re ipsa.

III - DOS PEDIDOS
Diante do exposto, requer a condenação da Ré ao pagamento de R$ 15.000,00 a título de indenização por danos morais.
"""
    adapter = LocalDeterministicFallbackAdapter()
    req = InternalAnalyzeRequest(
        arquivo_nome="peticao_completa.pdf",
        texto_bruto=texto_peticao,
        contexto_historico=ContextoHistoricoSchema(),
    )

    resp = adapter.analyze_document(req)

    # 1. Metadados e Seções presentes
    meta = resp.metadados_extraidos
    assert meta.secoes is not None
    assert isinstance(meta.secoes, SecoesPeticaoSchema)

    # 2. Invariante Crítico LGPD: Nenhum CPF, RG ou nome real nas seções segmentadas
    assert "111.222.333-44" not in meta.secoes.dos_fatos
    assert "12.345.678-9" not in meta.secoes.dos_fatos
    assert "Lucas Gabriel Rodrigues" not in meta.secoes.dos_fatos
    assert "Lucas Gabriel Rodrigues" not in meta.secoes.cabecalho
    assert "111.222.333-44" not in resp.resumo_nlp

    # 3. Sumarização factual extraída especificamente da seção Dos Fatos (RF-05)
    assert "cancelou o voo sem prestar" in resp.resumo_nlp or "compareceu ao aeroporto" in resp.resumo_nlp
    assert meta.tema == "Atraso de Voo / Indenização"
    assert meta.secoes.do_direito != ""
    assert meta.secoes.dos_pedidos != ""
