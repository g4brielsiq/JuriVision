"""
Saneamento de dados presumidos gravados por versões anteriores do JuriVision.

Versões antigas preenchiam o acervo com informações que não vieram de nenhuma fonte real:
1. Um "lote de contingência" do DataJud com processos fictícios, gravado sempre que a API do CNJ falhava;
2. Processos reais do DataJud completados com autor, réu e magistrado inventados e desfecho presumido;
3. Petições enviadas em PDF registradas como "Procedente" quando a previsão passava de 60%.

A rotina é idempotente e roda na inicialização: depois da primeira execução não encontra mais nada.
"""
from datetime import datetime
import logging
import re

from sqlalchemy.orm import Session

from app.core.datajud_client import NAO_INFORMADO, PREFIXOS_CNJ_CONTINGENCIA_FICTICIA, DataJudClient
from app.models.entities import Processo

logger = logging.getLogger("jurivision.saneamento")

# Autor fixo ("Carlos Eduardo Ferreira") que a conversão antiga do DataJud atribuía a todo processo
AUTOR_PRESUMIDO_DATAJUD = "Carlos E. ***"
TRECHO_PARTES_PRESUMIDAS = re.compile(r"\s*Parte autora:[^.]*\.(?:[^.]*S\.A\.)?")


def _data(valor) -> object:
    return valor.date() if isinstance(valor, datetime) else valor


def sanear_acervo(db: Session) -> dict[str, int]:
    resumo = {"ficticios_removidos": 0, "datajud_partes_corrigidas": 0, "pdf_desfecho_corrigido": 0}

    # 1. Processos do lote fictício (todos com dígito verificador CNJ inválido)
    candidatos = db.query(Processo).filter(Processo.origem_ingestao == "DATAJUD").all()
    for proc in candidatos:
        numero = proc.numero_processo or ""
        if numero.startswith(PREFIXOS_CNJ_CONTINGENCIA_FICTICIA) and not DataJudClient.cnj_digito_verificador_valido(
            numero
        ):
            db.delete(proc)
            resumo["ficticios_removidos"] += 1

    # 2. Processos reais do DataJud com partes/magistrado inventados e desfecho presumido
    for proc in candidatos:
        if proc in db.deleted or proc.autor_anonimizado != AUTOR_PRESUMIDO_DATAJUD:
            continue
        proc.autor_anonimizado = NAO_INFORMADO
        proc.reu_anonimizado = NAO_INFORMADO
        proc.magistrado = NAO_INFORMADO
        proc.resultado_historico = "Em Analise"
        proc.data_julgamento = None
        proc.resumo_nlp = TRECHO_PARTES_PRESUMIDAS.sub("", proc.resumo_nlp or "").strip()
        resumo["datajud_partes_corrigidas"] += 1

    # 3. Petições cujo "Procedente" era a própria previsão gravada na data do envio
    pdfs = (
        db.query(Processo)
        .filter(Processo.origem_ingestao == "PDF", Processo.resultado_historico == "Procedente")
        .all()
    )
    for proc in pdfs:
        # date.today() (horário local) x criado_em (UTC): tolera a virada de dia entre os dois
        criado = _data(proc.criado_em)
        if proc.data_julgamento is not None and criado and abs((proc.data_julgamento - criado).days) <= 1:
            proc.resultado_historico = "Em Analise"
            proc.data_julgamento = None
            resumo["pdf_desfecho_corrigido"] += 1

    if any(resumo.values()):
        db.commit()
        logger.warning("Saneamento do acervo aplicado: %s", resumo)
    return resumo
