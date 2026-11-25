"""
Testes do Processamento de Documentos e NLP (Card #18).
- CT-NLP-01: limpeza remove ruídos de PDF sem perder conteúdo.
- CT-NLP-02: o motor NÃO inventa dados quando a informação não está no documento.
- CT-NLP-03: identificação de número CNJ (com e sem máscara), magistrado, vara e partes.
- CT-NLP-04: classificação por assunto com confiança e tema "Não classificado".
- CT-NLP-05: características processuais, valor da causa e pedidos.
- CT-NLP-06: qualidade mínima no conjunto de petições anotadas (tests/fixtures/peticoes_nlp.json).
- CT-NLP-07: o upload de PDF expõe os novos campos na API.
"""
import io

from fastapi.testclient import TestClient
import pytest

from app.core.ai_gateway import LocalDeterministicFallbackAdapter
from app.core.nlp_avaliacao import avaliar, relatorio
from app.core.nlp_processual import (
    NAO_CLASSIFICADO,
    NAO_IDENTIFICADA,
    NAO_IDENTIFICADO,
    PREFIXO_SEM_CNJ,
    ClassificadorAssunto,
    ExtratorCaracteristicas,
    ExtratorInformacoesProcessuais,
    LimpadorTexto,
)
from app.main import app
from app.routers.relatorios import _build_pdf_document
from app.schemas.contracts import ContextoHistoricoSchema, InternalAnalyzeRequest


def _analisar(texto: str):
    return LocalDeterministicFallbackAdapter().analyze_document(
        InternalAnalyzeRequest(arquivo_nome="teste.pdf", texto_bruto=texto, contexto_historico=ContextoHistoricoSchema())
    )


# CT-NLP-01 ---------------------------------------------------------------------
def test_limpeza_remove_paginacao_cabecalhos_repetidos_e_hifenizacao():
    texto = (
        "TRIBUNAL DE JUSTIÇA DE ALAGOAS\nPágina 1 de 3\nO autor sofreu uma cobrança indevi-\nda no mês de março.\n"
        "TRIBUNAL DE JUSTIÇA DE ALAGOAS\n2\nA cobrança foi feita sem contrato\nassinado pelo consumidor.\n"
        "TRIBUNAL DE JUSTIÇA DE ALAGOAS\nDocumento assinado digitalmente por fulano em 10/10/2025\n- 3 -\nFim."
    )
    limpo = LimpadorTexto.limpar(texto)
    assert "Página 1 de 3" not in limpo
    assert "TRIBUNAL DE JUSTIÇA DE ALAGOAS" not in limpo
    assert "assinado digitalmente" not in limpo
    assert "- 3 -" not in limpo
    assert "cobrança indevida no mês de março" in limpo
    assert "sem contrato assinado pelo consumidor" in limpo
    assert limpo.endswith("Fim.")


def test_limpeza_preserva_titulos_de_secao():
    texto = "DOS FATOS\nO autor comprou um produto.\nDOS PEDIDOS\na) a restituição do valor;"
    limpo = LimpadorTexto.limpar(texto)
    assert "DOS FATOS\nO autor" in limpo
    assert "\nDOS PEDIDOS\n" in limpo


def test_limpeza_texto_vazio():
    assert LimpadorTexto.limpar("") == ""
    assert LimpadorTexto.limpar(None) == ""


# CT-NLP-02 ---------------------------------------------------------------------
def test_nao_inventa_dados_quando_documento_nao_tem_informacoes():
    resp = _analisar("Segue em anexo a documentação solicitada para arquivamento.")
    meta = resp.metadados_extraidos
    assert meta.numero_processo.startswith(PREFIXO_SEM_CNJ)
    assert meta.magistrado == NAO_IDENTIFICADO
    assert meta.comarca == NAO_IDENTIFICADA
    assert meta.partes_anonimizadas.autor == NAO_IDENTIFICADO
    assert meta.partes_anonimizadas.reu == NAO_IDENTIFICADO
    assert meta.tema == NAO_CLASSIFICADO
    assert set(meta.campos_nao_identificados) == {"numero_processo", "magistrado", "comarca", "autor", "reu"}
    # Valores fictícios antigos não podem mais aparecer
    saida = resp.model_dump_json()
    for valor_inventado in ("Lucas Gabriel Rodrigues", "Dr. Rafael De Amorim", "Bradesco", ".2026.8.02.0001"):
        assert valor_inventado not in saida


def test_identificador_sem_cnj_e_deterministico():
    a, ok_a = ExtratorInformacoesProcessuais.numero_processo("texto sem número", "a.pdf")
    b, _ = ExtratorInformacoesProcessuais.numero_processo("texto sem número", "a.pdf")
    assert not ok_a and a == b and a.startswith(PREFIXO_SEM_CNJ)


# CT-NLP-03 ---------------------------------------------------------------------
def test_numero_cnj_com_e_sem_mascara():
    assert ExtratorInformacoesProcessuais.numero_processo("Processo 0801234-56.2025.8.02.0001")[0] == "0801234-56.2025.8.02.0001"
    assert ExtratorInformacoesProcessuais.numero_processo("Processo 08012345620258020001")[0] == "0801234-56.2025.8.02.0001"


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Magistrado: Dr. Rafael De Amorim", "Dr. Rafael De Amorim"),
        ("Juíza de Direito: DRA. ANA PAULA MENDES", "Dra. Ana Paula Mendes"),
        ("Sentença proferida pelo MM. Juiz Dr. Carlos Eduardo Lins", "Dr. Carlos Eduardo Lins"),
        ("EXCELENTÍSSIMO SENHOR JUIZ DE DIREITO DA 1ª VARA CÍVEL", None),
    ],
)
def test_identificacao_magistrado(texto, esperado):
    assert ExtratorInformacoesProcessuais.magistrado(texto) == esperado


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("JUIZ DE DIREITO DA 3ª VARA CÍVEL DA COMARCA DE ARAPIRACA/AL", "3ª Vara Cível da Comarca de Arapiraca"),
        ("SENHOR JUIZ DA 1a VARA CIVEL DE MACEIO", "1ª Vara Civel de Maceio"),
        ("JUIZ DO 2º JUIZADO ESPECIAL CÍVEL DE MACEIÓ", "2º Juizado Especial Cível de Maceió"),
        ("Tramita na Comarca de Penedo - AL", "Comarca de Penedo"),
        ("Sem nenhuma indicação de juízo", None),
    ],
)
def test_identificacao_vara_comarca(texto, esperado):
    assert ExtratorInformacoesProcessuais.comarca(texto) == esperado


def test_identificacao_partes_por_rotulo_e_em_face_de():
    info = ExtratorInformacoesProcessuais.extrair("Autora: Maria José dos Santos, brasileira\nRé: Banco Exemplo S.A., CNPJ 00")
    assert info.autor == "Maria José dos Santos"
    assert info.reu == "Banco Exemplo S.A."
    info2 = ExtratorInformacoesProcessuais.extrair("vem propor a presente ação em face de TELEFONIA BRASIL LTDA., pessoa jurídica")
    assert info2.reu == "TELEFONIA BRASIL LTDA."


# CT-NLP-04 ---------------------------------------------------------------------
@pytest.mark.parametrize(
    "texto, tema",
    [
        ("A companhia aérea cancelou o voo e extraviou a bagagem do passageiro.", "Atraso de Voo / Indenização"),
        ("Reclamação trabalhista: horas extras e FGTS não pagos pelo empregador.", "Direito Trabalhista"),
        ("O plano de saúde negou a cobertura da cirurgia prescrita.", "Plano de Saúde"),
        ("Execução fiscal de IPTU inscrito em dívida ativa.", "Tributário"),
        ("O INSS indeferiu a aposentadoria do segurado.", "Direito Previdenciário"),
        ("Ação de divórcio com pedido de pensão alimentícia e guarda.", "Direito de Família"),
        ("Empréstimo consignado com juros abusivos e capitalização de juros.", "Direito Bancário"),
        ("Cobrança indevida de serviço não contratado de telefonia.", "Direito do Consumidor"),
        ("Negativação indevida no SERASA e no SPC.", "Dano Moral"),
    ],
)
def test_classificacao_por_assunto(texto, tema):
    resultado = ClassificadorAssunto.classificar(texto)
    assert resultado.tema == tema
    assert 0 < resultado.confianca <= 1
    assert resultado.termos_encontrados


def test_classificacao_sem_termos_retorna_nao_classificado():
    resultado = ClassificadorAssunto.classificar("Texto genérico sem assunto jurídico definido.")
    assert resultado.tema == NAO_CLASSIFICADO
    assert resultado.confianca == 0.0


# CT-NLP-05 ---------------------------------------------------------------------
def test_caracteristicas_valor_da_causa_e_pedidos():
    texto = (
        "AÇÃO DE OBRIGAÇÃO DE FAZER COM PEDIDO DE TUTELA DE URGÊNCIA\n"
        "DOS PEDIDOS\nDiante do exposto, requer:\n"
        "a) a concessão da gratuidade da justiça;\n"
        "b) a tutela de urgência para fornecimento do medicamento;\n"
        "c) a condenação em danos morais.\n"
        "Dá-se à causa o valor de R$ 1.234.567,89.\nNestes termos, pede deferimento."
    )
    resp = _analisar(texto)
    car = resp.metadados_extraidos.caracteristicas
    assert car.classe_processual == "Ação de Obrigação de Fazer com Pedido de Tutela de Urgência"
    assert car.valor_causa == 1234567.89
    assert car.tutela_urgencia and car.justica_gratuita and car.danos_morais
    assert not car.prioridade_tramitacao
    assert car.pedidos == [
        "a concessão da gratuidade da justiça",
        "a tutela de urgência para fornecimento do medicamento",
        "a condenação em danos morais",
    ]


def test_pedidos_sem_enumeracao_sao_separados_por_ponto_e_virgula():
    pedidos = ExtratorCaracteristicas.pedidos("Requer a restituição em dobro dos valores; a condenação em danos morais; custas")
    assert pedidos == ["Requer a restituição em dobro dos valores", "a condenação em danos morais"]


def test_resumo_e_pedidos_respeitam_lgpd():
    texto = (
        "Autor: Joaquim Pereira Neto, CPF 987.654.321-00\nRéu: Loja Exemplo LTDA.\n"
        "DOS FATOS\nO autor Joaquim Pereira Neto comprou um produto defeituoso na loja ré em 02/01/2026.\n"
        "DOS PEDIDOS\na) a devolução do valor pago a Joaquim Pereira Neto;\nb) danos morais."
    )
    resp = _analisar(texto)
    saida = resp.resumo_nlp + " ".join(resp.metadados_extraidos.caracteristicas.pedidos)
    assert "Joaquim Pereira Neto" not in saida
    assert "987.654.321-00" not in saida
    assert "Joaquim P. ***" in resp.resumo_nlp


# CT-NLP-06 ---------------------------------------------------------------------
def test_qualidade_no_conjunto_de_peticoes_anotadas():
    campos = avaliar()
    falhas = {nome: r.taxa for nome, r in campos.items() if r.taxa < 0.9}
    assert not falhas, "\n" + relatorio(campos)
    assert campos["lgpd"].taxa == 1.0, "\n" + relatorio(campos)


# CT-NLP-07 ---------------------------------------------------------------------
def test_upload_pdf_retorna_caracteristicas_e_campos_nao_identificados():
    pdf = _build_pdf_document(
        [
            "AÇÃO DE INDENIZAÇÃO POR DANOS MORAIS",
            "Autor: Bruno Cesar Tavares",
            "O autor teve o nome negativado no SERASA por dívida já paga.",
            "Requer a justiça gratuita e a condenação em danos morais.",
        ]
    )
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/processos/upload-pdf",
            files={"file": ("nlp_teste.pdf", io.BytesIO(pdf), "application/pdf")},
        )
    assert resp.status_code == 200, resp.text
    meta = resp.json()["metadados_extraidos"]
    assert meta["tema"] == "Dano Moral"
    assert meta["caracteristicas"]["justica_gratuita"] is True
    assert meta["caracteristicas"]["danos_morais"] is True
    assert "magistrado" in meta["campos_nao_identificados"]
    assert meta["magistrado"] == NAO_IDENTIFICADO
    assert meta["confianca_classificacao"] > 0
