"""
Router de Gestão Processual, Ingestão (PDF/CSV) e Base de Conhecimento — JuriVision.
Rastreabilidade:
- ARCHITECTURE.md: Seções 8.3, 8.4 e 8.5; ADR-001, ADR-002 e ADR-003
- MODELING.md: RF-02, RF-03, RF-04, RF-05, RF-06, RF-08, RN-01 a RN-04, UC-02 a UC-07
"""
import csv
from collections import Counter
from datetime import date, datetime
import hashlib
import io
import re
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.ai_gateway import AnonimizadorLGPD, ExtratorDocumental, ai_gateway
from app.core.datajud_client import DataJudClient
from app.core.database import get_db
from app.core.security import get_optional_current_user
from app.models.entities import AnalisePreditiva, LogAuditoriaLGPD, Processo, Usuario
from app.schemas.comparacao import ResultadoComparacaoPecas
from app.schemas.contracts import (
    AnalisePreditivaSchema,
    AuditoriaLGPDSchema,
    ContextoHistoricoSchema,
    CSVUploadResponse,
    InternalAnalyzeRequest,
    MetadadosExtraidosSchema,
    PartesAnonimizadasSchema,
    ProcessoCadastroRequest,
    ProcessoDetalhesResponse,
    ProcessoAnonimizacaoRequest,
    ProcessoAnonimizacaoResponse,
    ProcessoListItemSchema,
    ProcessoListResponse,
    ProcessoUploadResponse,
    DataJudProcessoResponse,
    DataJudSincronizacaoRequest,
    DataJudSincronizacaoResponse,
)

router = APIRouter(prefix="/api/v1/processos", tags=["Processos e Base de Conhecimento (RF-02 a RF-08)"])

REQUIRED_CSV_COLUMNS = {
    "numero_processo",
    "tema",
    "magistrado",
    "comarca",
    "autor",
    "reu",
    "texto_resumo",
    "resultado",
    "data_julgamento",
}

MAX_PDF_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB (RN-04 / SEC-05)
MAX_CSV_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB (RN-04 / SEC-05)
MIN_JULGADOS_POR_TEMA = 5


_STOPWORDS_SIMILARIDADE = {
    "processo", "decisao", "judicial", "autos", "relatoria", "juizo", "envolvendo",
    "sintese", "processual", "higienizada", "acao", "tendo", "partes", "submetida",
    "analise", "preditiva", "vara", "civel", "maceio", "direito", "contra", "sobre",
}


def _extrair_palavras_chave(texto: Optional[str]) -> set[str]:
    if not texto:
        return set()
    tokens = re.findall(r"[a-zA-ZÀ-ÿ]{5,}", texto.lower())
    return {t for t in tokens if t not in _STOPWORDS_SIMILARIDADE}


def _temas_equivalentes(tema_a: Optional[str], tema_b: Optional[str]) -> bool:
    a = (tema_a or "").strip().lower()
    b = (tema_b or "").strip().lower()
    if not a or not b:
        return False
    return a == b or a in b or b in a


def _buscar_processos_similares_reais(
    db: Session,
    tema: Optional[str],
    magistrado: Optional[str],
    comarca: Optional[str] = None,
    resumo: Optional[str] = None,
    ignorar_id: Optional[str] = None,
    ignorar_numero: Optional[str] = None,
) -> list[Processo]:
    """
    Identifica e ordena processos reais semelhantes persistidos na base (RF-06 / Card #35),
    combinando correspondência de tema, magistrado, comarca e vocabulário factual da síntese.
    """
    query = db.query(Processo)
    if ignorar_id:
        query = query.filter(Processo.id_processo != ignorar_id)
    if ignorar_numero:
        query = query.filter(Processo.numero_processo != ignorar_numero)

    candidatos = query.all()
    if not candidatos:
        return []

    juiz_norm = (magistrado or "").strip().lower()
    comarca_norm = (comarca or "").strip().lower()
    palavras_base = _extrair_palavras_chave(resumo)

    pontuados: list[tuple[int, date, Processo]] = []
    for cand in candidatos:
        score = 0
        mesmo_tema = _temas_equivalentes(tema, cand.tema)
        if mesmo_tema:
            score += 4
        if juiz_norm and (cand.magistrado or "").strip().lower() == juiz_norm:
            score += 2
        if comarca_norm and (cand.comarca or "").strip().lower() == comarca_norm:
            score += 1
        if palavras_base:
            intersecao = len(palavras_base & _extrair_palavras_chave(cand.resumo_nlp))
            if intersecao >= 2:
                score += 2
            elif intersecao == 1:
                score += 1

        if mesmo_tema or score >= 3:
            pontuados.append((score, cand.data_julgamento or date.min, cand))

    pontuados.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in pontuados]


def _detectar_tema_preliminar(raw_text: str) -> Optional[str]:
    lower = raw_text.lower()
    if any(k in lower for k in ("voo", "aérea", "aerea", "bagagem", "passageiro", "aeroporto", "cancelamento")):
        return "Atraso de Voo"
    if any(k in lower for k in ("trabalh", "clt", "horas extras", "rescisa", "rescisão", "fgts", "empregad")):
        return "Direito Trabalhista"
    if any(k in lower for k in ("saúde", "saude", "unimed", "hospital", "cirurgia", "tratamento", "home care", "plano")):
        return "Plano de Saúde"
    if any(k in lower for k in ("tribut", "icms", "iss", "fisco", "execução fiscal", "imposto")):
        return "Tributário"
    if any(k in lower for k in ("dano moral", "indeniza", "consumidor", "cobrança", "cobranca", "negativa")):
        return "Dano Moral"
    return None


def _compute_historical_context(db: Session, raw_text: str) -> ContextoHistoricoSchema:
    """
    Consulta o histórico relacional (RN-02) para fornecer parâmetros estatísticos reais
    ao motor preditivo sobre o magistrado e tema correlatos, sem multiplicadores artificiais.
    """
    lower = raw_text.lower()
    if "maria silva" in lower:
        target_juiz = "Dra. Maria Silva"
    elif "carlos souza" in lower:
        target_juiz = "Dr. Carlos Souza"
    elif "rafael" in lower or "amorim" in lower:
        target_juiz = "Dr. Rafael De Amorim"
    else:
        target_juiz = None

    target_tema = _detectar_tema_preliminar(raw_text)
    similares = _buscar_processos_similares_reais(
        db,
        tema=target_tema,
        magistrado=target_juiz,
        resumo=raw_text,
    )

    pool_estatistico = similares or db.query(Processo).all()
    if not pool_estatistico:
        return ContextoHistoricoSchema(
            total_casos_similares=0,
            taxa_favoravel_juiz=0.5,
            tempo_medio_meses=12,
        )

    favoraveis = sum(
        1
        for p in pool_estatistico
        if (p.resultado_historico or "").lower() in ("procedente", "acordo")
        or (p.analise_preditiva and p.analise_preditiva.probabilidade_deferimento >= 0.5)
    )
    taxa = round(favoraveis / len(pool_estatistico), 2)
    prazos = [
        p.analise_preditiva.tempo_estimado_sentenca_meses
        for p in pool_estatistico
        if p.analise_preditiva is not None
    ]
    tempo_medio = int(round(sum(prazos) / len(prazos))) if prazos else 12

    return ContextoHistoricoSchema(
        total_casos_similares=len(similares),
        taxa_favoravel_juiz=max(min(taxa, 0.92), 0.15),
        tempo_medio_meses=max(tempo_medio, 1),
    )


@router.post("/upload-pdf", response_model=ProcessoUploadResponse, status_code=status.HTTP_200_OK)
async def upload_processo_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: Optional[Usuario] = Depends(get_optional_current_user),
) -> ProcessoUploadResponse:
    """
    Recebe uma petição inicial em PDF (RF-02), valida sua integridade binária (RN-04),
    aciona o pipeline isolado de IA com barreira LGPD obrigatória (RF-04, RF-05, RF-06)
    e persiste o processo higienizado no banco de dados (ADR-003).
    """
    filename = file.filename or "peticao_inicial.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ErroProcessamento (RN-04): Formato inválido. Envie exclusivamente arquivos com extensão .pdf.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_PDF_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="ErroProcessamento (RN-04 / SEC-05): Arquivo excede o limite máximo permitido de 15MB.",
        )
    try:
        raw_text = ExtratorDocumental.extract_text_from_pdf_bytes(file_bytes)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ErroProcessamento (RN-04): {str(exc)}",
        ) from exc

    contexto = _compute_historical_context(db, raw_text)
    ai_result = ai_gateway.analyze_document(
        InternalAnalyzeRequest(
            arquivo_nome=filename,
            texto_bruto=raw_text,
            contexto_historico=contexto,
        )
    )

    meta = ai_result.metadados_extraidos
    pred = ai_result.analise_preditiva
    lgpd = ai_result.auditoria_lgpd

    similares_reais = _buscar_processos_similares_reais(
        db,
        tema=meta.tema,
        magistrado=meta.magistrado,
        comarca=meta.comarca,
        resumo=ai_result.resumo_nlp,
        ignorar_numero=meta.numero_processo,
    )
    pred.casos_similares_encontrados = len(similares_reais)

    # Verifica se já existe processo com o mesmo número CNJ para operação idempotente
    existing = db.query(Processo).filter(Processo.numero_processo == meta.numero_processo).first()
    if existing:
        proc_id = existing.id_processo
        existing.arquivo_nome = filename
        existing.status = "PROCESSADO"
        existing.tema = meta.tema
        existing.magistrado = meta.magistrado
        existing.comarca = meta.comarca
        existing.autor_anonimizado = meta.partes_anonimizadas.autor
        existing.reu_anonimizado = meta.partes_anonimizadas.reu
        existing.resumo_nlp = ai_result.resumo_nlp
        if existing.analise_preditiva:
            existing.analise_preditiva.probabilidade_deferimento = pred.probabilidade_deferimento
            existing.analise_preditiva.margem_confianca = pred.margem_confianca
            existing.analise_preditiva.tempo_estimado_sentenca_meses = pred.tempo_estimado_sentenca_meses
            existing.analise_preditiva.casos_similares_encontrados = pred.casos_similares_encontrados
            existing.analise_preditiva.tese_recomendada = pred.tese_recomendada
            existing.analise_preditiva.tendencia_juiz = pred.tendencia_juiz
            existing.analise_preditiva.provedor_ia_utilizado = pred.provedor_ia
    else:
        short_hash = hashlib.sha1(f"{meta.numero_processo}-{uuid.uuid4()}".encode("utf-8")).hexdigest()[:5]
        proc_id = f"proc-{short_hash}"
        novo_proc = Processo(
            id_processo=proc_id,
            usuario_id=usuario.id if usuario else "usr-01",
            numero_processo=meta.numero_processo,
            arquivo_nome=filename,
            origem_ingestao="PDF",
            status="PROCESSADO",
            tema=meta.tema,
            magistrado=meta.magistrado,
            comarca=meta.comarca,
            autor_anonimizado=meta.partes_anonimizadas.autor,
            reu_anonimizado=meta.partes_anonimizadas.reu,
            resumo_nlp=ai_result.resumo_nlp,
            resultado_historico="Procedente" if pred.probabilidade_deferimento >= 0.6 else "Em Analise",
            data_julgamento=date.today(),
        )
        db.add(novo_proc)
        db.flush()

        nova_pred = AnalisePreditiva(
            id_processo=proc_id,
            probabilidade_deferimento=pred.probabilidade_deferimento,
            margem_confianca=pred.margem_confianca,
            tempo_estimado_sentenca_meses=pred.tempo_estimado_sentenca_meses,
            casos_similares_encontrados=pred.casos_similares_encontrados,
            tese_recomendada=pred.tese_recomendada,
            tendencia_juiz=pred.tendencia_juiz,
            provedor_ia_utilizado=pred.provedor_ia,
        )
        db.add(nova_pred)

    novo_log = LogAuditoriaLGPD(
        id_processo=proc_id,
        total_cpfs_mascarados=lgpd.total_cpfs_mascarados,
        total_nomes_mascarados=lgpd.total_nomes_mascarados,
        texto_higienizado_verificado=lgpd.texto_higienizado_verificado,
    )
    db.add(novo_log)
    db.commit()

    return ProcessoUploadResponse(
        id_processo=proc_id,
        arquivo_nome=filename,
        status="PROCESSADO",
        metadados_extraidos=meta,
        resumo_nlp=ai_result.resumo_nlp,
        analise_preditiva=pred,
        auditoria_lgpd=lgpd,
    )


@router.post("/upload-csv", response_model=CSVUploadResponse, status_code=status.HTTP_200_OK)
async def upload_processos_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: Optional[Usuario] = Depends(get_optional_current_user),
) -> CSVUploadResponse:
    """
    Importa em lote registros estruturados via planilha CSV (RF-03),
    aplicando higienização determinística local LGPD em 100% das linhas antes da persistência (RF-04 / RN-01).
    """
    filename = file.filename or "lote_processos.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ErroProcessamento (RN-04): Formato inválido. Envie um arquivo com extensão .csv.",
        )

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ErroProcessamento (RN-04): O arquivo CSV enviado está vazio.",
        )
    if len(raw_bytes) > MAX_CSV_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="ErroProcessamento (RN-04 / SEC-05): Planilha CSV excede o limite máximo permitido de 10MB.",
        )

    try:
        decoded = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = raw_bytes.decode("latin-1", errors="replace")

    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ErroProcessamento (RN-04): Cabeçalho CSV ausente ou malformado.",
        )

    normalized_headers = {h.strip().lower() for h in reader.fieldnames if h}
    missing = REQUIRED_CSV_COLUMNS - normalized_headers
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ErroProcessamento (RN-04): Colunas obrigatórias ausentes no CSV: {sorted(missing)}",
        )

    lidos = 0
    importados = 0
    anonimizados = 0

    for row in reader:
        lidos += 1
        norm_row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        num_proc = norm_row.get("numero_processo")
        if not num_proc:
            continue

        raw_autor = norm_row.get("autor", "Autor Anonimizado")
        raw_reu = norm_row.get("reu", "Réu")
        raw_resumo = norm_row.get("texto_resumo", "")

        autor_anon, autor_masked = AnonimizadorLGPD.mask_party_name(raw_autor)
        reu_anon, reu_masked = AnonimizadorLGPD.mask_party_name(raw_reu)
        clean_resumo, cpfs_masked, names_masked = AnonimizadorLGPD.sanitize_text(
            raw_resumo, known_natural_names=[raw_autor, raw_reu]
        )

        if autor_masked or reu_masked or cpfs_masked > 0 or names_masked > 0:
            anonimizados += 1

        try:
            dt_julg = datetime.strptime(norm_row.get("data_julgamento", ""), "%Y-%m-%d").date()
        except ValueError:
            dt_julg = date.today()

        resultado = norm_row.get("resultado") or "Procedente"
        prob = 0.76 if resultado.lower() in ("procedente", "acordo") else 0.38

        existing = db.query(Processo).filter(Processo.numero_processo == num_proc).first()
        if existing:
            proc_id = existing.id_processo
            existing.tema = norm_row.get("tema") or "Dano Moral"
            existing.magistrado = norm_row.get("magistrado") or "Dr. Rafael De Amorim"
            existing.comarca = norm_row.get("comarca") or "1ª Vara Cível de Maceió"
            existing.autor_anonimizado = autor_anon
            existing.reu_anonimizado = reu_anon
            existing.resumo_nlp = clean_resumo or "Resumo importado via lote CSV e higienizado."
            existing.resultado_historico = resultado
            existing.data_julgamento = dt_julg
        else:
            short_hash = hashlib.sha1(f"{num_proc}-{uuid.uuid4()}".encode("utf-8")).hexdigest()[:5]
            proc_id = f"proc-{short_hash}"
            tema_row = norm_row.get("tema") or "Dano Moral"
            magistrado_row = norm_row.get("magistrado") or "Dr. Rafael De Amorim"
            comarca_row = norm_row.get("comarca") or "1ª Vara Cível de Maceió"
            resumo_row = clean_resumo or "Resumo importado via lote CSV e higienizado."

            with db.no_autoflush:
                similares_csv = _buscar_processos_similares_reais(
                    db,
                    tema=tema_row,
                    magistrado=magistrado_row,
                    comarca=comarca_row,
                    resumo=resumo_row,
                    ignorar_numero=num_proc,
                )

            proc_obj = Processo(
                id_processo=proc_id,
                usuario_id=usuario.id if usuario else "usr-01",
                numero_processo=num_proc,
                arquivo_nome=filename,
                origem_ingestao="CSV",
                status="PROCESSADO",
                tema=tema_row,
                magistrado=magistrado_row,
                comarca=comarca_row,
                autor_anonimizado=autor_anon,
                reu_anonimizado=reu_anon,
                resumo_nlp=resumo_row,
                resultado_historico=resultado,
                data_julgamento=dt_julg,
            )
            db.add(proc_obj)
            db.flush()

            db.add(
                AnalisePreditiva(
                    id_processo=proc_id,
                    probabilidade_deferimento=prob,
                    margem_confianca=0.08,
                    tempo_estimado_sentenca_meses=11,
                    casos_similares_encontrados=len(similares_csv),
                    tese_recomendada="Jurisprudência dominante aplicável ao tema importado em lote.",
                    tendencia_juiz=f"Histórico consolidado para {proc_obj.magistrado}.",
                    provedor_ia_utilizado="local_heuristic",
                )
            )

        db.add(
            LogAuditoriaLGPD(
                id_processo=proc_id,
                total_cpfs_mascarados=cpfs_masked,
                total_nomes_mascarados=max(names_masked, 1 if (autor_masked or reu_masked) else 0),
                texto_higienizado_verificado=True,
            )
        )
        importados += 1

    if lidos == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ErroProcessamento (RN-04): O arquivo CSV não possui linhas de dados para importação.",
        )

    db.commit()

    return CSVUploadResponse(
        lote_status="PROCESSADO",
        arquivo_nome=filename,
        total_registros_lidos=lidos,
        total_importados_com_sucesso=importados,
        total_entidades_anonimizadas_lgpd=anonimizados,
    )


_TRIBUNAL_CNJ_CODES = {
    "TJAL": ".8.02.",
    "TJPE": ".8.17.",
    "TJRJ": ".8.19.",
    "TJSP": ".8.26.",
    "TRT19": ".5.19.",
}


def _converter_para_list_item(p: Processo) -> ProcessoListItemSchema:
    return ProcessoListItemSchema(
        id_processo=p.id_processo,
        numero_processo=p.numero_processo,
        tema=p.tema,
        magistrado=p.magistrado,
        comarca=p.comarca,
        partes_anonimizadas=f"{p.autor_anonimizado} vs {p.reu_anonimizado}",
        resultado=p.resultado_historico,
        data_julgamento=p.data_julgamento.isoformat() if p.data_julgamento else None,
        probabilidade_deferimento=(
            p.analise_preditiva.probabilidade_deferimento if p.analise_preditiva else None
        ),
    )


@router.get("", response_model=ProcessoListResponse, status_code=status.HTTP_200_OK)
def listar_processos(
    tema: Optional[str] = Query(default=None, description="Filtrar por tema jurídico"),
    juiz: Optional[str] = Query(default=None, description="Filtrar por nome do magistrado"),
    comarca: Optional[str] = Query(default=None, description="Filtrar por comarca ou órgão julgador"),
    tribunal: Optional[str] = Query(default=None, description="Filtrar por sigla ou código CNJ do tribunal (ex: TJAL)"),
    busca: Optional[str] = Query(default=None, description="Busca textual livre (CNJ, tema, juiz, comarca ou partes)"),
    pagina: int = Query(default=1, ge=1, description="Página atual"),
    limite: int = Query(default=10, ge=1, le=100, description="Itens por página"),
    db: Session = Depends(get_db),
    _usuario: Optional[Usuario] = Depends(get_optional_current_user),
) -> ProcessoListResponse:
    """
    Lista e filtra processos higienizados na Base de Conhecimento com paginação (RF-08 / UC-06 / UC-07).
    """
    query = db.query(Processo)

    if tema and tema.strip():
        query = query.filter(Processo.tema.ilike(f"%{tema.strip()}%"))
    if juiz and juiz.strip():
        query = query.filter(Processo.magistrado.ilike(f"%{juiz.strip()}%"))
    if comarca and comarca.strip():
        query = query.filter(Processo.comarca.ilike(f"%{comarca.strip()}%"))
    if tribunal and tribunal.strip():
        trib = tribunal.strip().upper()
        cnj_code = _TRIBUNAL_CNJ_CODES.get(trib, trib)
        if trib in ("TJAL", "8.02", ".8.02."):
            query = query.filter(
                or_(
                    Processo.numero_processo.ilike("%.8.02.%"),
                    Processo.comarca.ilike("%Maceió%"),
                    Processo.comarca.ilike("%Arapiraca%"),
                    Processo.comarca.ilike("%TJAL%"),
                )
            )
        else:
            query = query.filter(
                or_(
                    Processo.numero_processo.ilike(f"%{cnj_code}%"),
                    Processo.comarca.ilike(f"%{trib}%"),
                )
            )
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        query = query.filter(
            or_(
                Processo.numero_processo.ilike(term),
                Processo.id_processo.ilike(term),
                Processo.tema.ilike(term),
                Processo.magistrado.ilike(term),
                Processo.comarca.ilike(term),
                Processo.autor_anonimizado.ilike(term),
                Processo.reu_anonimizado.ilike(term),
                Processo.resumo_nlp.ilike(term),
            )
        )

    total = query.count()
    offset = (pagina - 1) * limite
    registros = query.order_by(Processo.criado_em.desc()).offset(offset).limit(limite).all()

    itens = [_converter_para_list_item(p) for p in registros]

    return ProcessoListResponse(
        total=total,
        pagina=pagina,
        itens=itens,
    )




# ==============================================================================
# Cadastro e Edição Manual de Processos (RF-08 / RN-01)
# ==============================================================================
RESULTADOS_FAVORAVEIS = ("procedente", "acordo")


def _estimar_analise_preditiva(db: Session, payload: ProcessoCadastroRequest, ignorar_id: Optional[str] = None) -> dict:
    """
    Estima os campos de AnalisePreditiva para um processo cadastrado manualmente, usando apenas
    dados reais da base: processos do mesmo tema e do mesmo magistrado já persistidos.
    Não há modelo treinado aqui: os valores são heurísticos e o provedor é registrado como 'local_heuristic'.
    """
    base = db.query(Processo)
    if ignorar_id:
        base = base.filter(Processo.id_processo != ignorar_id)

    mesmo_tema = base.filter(func.lower(Processo.tema) == payload.tema.lower()).all()
    mesmo_juiz = base.filter(func.lower(Processo.magistrado) == payload.magistrado.lower()).all()

    resultado = payload.resultado.lower()
    if resultado in RESULTADOS_FAVORAVEIS:
        probabilidade = 0.76  # mesma convenção da importação CSV para processos já decididos
    elif resultado == "improcedente":
        probabilidade = 0.38
    else:
        decididos = [
            p for p in (mesmo_juiz or mesmo_tema)
            if (p.resultado_historico or "").lower() in RESULTADOS_FAVORAVEIS + ("improcedente",)
        ]
        if decididos:
            favoraveis = sum(1 for p in decididos if p.resultado_historico.lower() in RESULTADOS_FAVORAVEIS)
            probabilidade = round(favoraveis / len(decididos), 2)
        else:
            probabilidade = 0.5
        probabilidade = max(min(probabilidade, 0.92), 0.08)

    prazos = [p.analise_preditiva.tempo_estimado_sentenca_meses for p in mesmo_tema if p.analise_preditiva]
    tempo = int(round(sum(prazos) / len(prazos))) if prazos else 12

    return {
        "probabilidade_deferimento": probabilidade,
        "margem_confianca": 0.08,
        "tempo_estimado_sentenca_meses": max(tempo, 1),
        "casos_similares_encontrados": len(mesmo_tema),
        "tese_recomendada": f"Estimativa heurística a partir de {len(mesmo_tema)} processo(s) do tema '{payload.tema}' na base.",
        "tendencia_juiz": f"Baseado em {len(mesmo_juiz)} processo(s) de {payload.magistrado} na base.",
        "provedor_ia_utilizado": "local_heuristic",
    }


def _anonimizar_cadastro(autor: str, reu: str, resumo: str) -> ProcessoAnonimizacaoResponse:
    autor_anon, autor_masked = AnonimizadorLGPD.mask_party_name(autor)
    reu_anon, reu_masked = AnonimizadorLGPD.mask_party_name(reu)
    resumo_limpo, cpfs_masked, names_masked = AnonimizadorLGPD.sanitize_text(
        resumo, known_natural_names=[autor, reu]
    )
    return ProcessoAnonimizacaoResponse(
        partes_anonimizadas=PartesAnonimizadasSchema(autor=autor_anon, reu=reu_anon),
        resumo=resumo_limpo,
        auditoria_lgpd=AuditoriaLGPDSchema(
            total_cpfs_mascarados=cpfs_masked,
            total_nomes_mascarados=names_masked + int(autor_masked) + int(reu_masked),
        ),
    )


@router.post("/anonimizacao/previa", response_model=ProcessoAnonimizacaoResponse)
def prever_anonimizacao(payload: ProcessoAnonimizacaoRequest) -> ProcessoAnonimizacaoResponse:
    """Executa a mesma higienização do cadastro sem persistir o rascunho."""
    return _anonimizar_cadastro(payload.autor.strip(), payload.reu.strip(), payload.resumo.strip())


def _aplicar_cadastro(db: Session, proc: Processo, payload: ProcessoCadastroRequest) -> None:
    """Aplica os campos do payload ao processo, passando partes e resumo pela barreira LGPD (RN-01)."""
    anonimizacao = _anonimizar_cadastro(payload.autor, payload.reu, payload.resumo)
    proc.numero_processo = payload.numero_processo
    proc.tema = payload.tema
    proc.magistrado = payload.magistrado
    proc.comarca = payload.comarca
    proc.autor_anonimizado = anonimizacao.partes_anonimizadas.autor
    proc.reu_anonimizado = anonimizacao.partes_anonimizadas.reu
    proc.resumo_nlp = anonimizacao.resumo
    proc.resultado_historico = payload.resultado
    proc.data_julgamento = payload.data_julgamento
    proc.status = "PROCESSADO"

    # no_autoflush: evita gravar o processo ainda incompleto enquanto a base é consultada
    with db.no_autoflush:
        estimativa = _estimar_analise_preditiva(db, payload, ignorar_id=proc.id_processo)
    if proc.analise_preditiva:
        for campo, valor in estimativa.items():
            setattr(proc.analise_preditiva, campo, valor)
    else:
        proc.analise_preditiva = AnalisePreditiva(id_processo=proc.id_processo, **estimativa)

    proc.logs_lgpd.append(
        LogAuditoriaLGPD(
            id_processo=proc.id_processo,
            **anonimizacao.auditoria_lgpd.model_dump(),
        )
    )


def _garantir_numero_unico(db: Session, numero_processo: str, ignorar_id: Optional[str] = None) -> None:
    query = db.query(Processo).filter(Processo.numero_processo == numero_processo)
    if ignorar_id:
        query = query.filter(Processo.id_processo != ignorar_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe um processo cadastrado com o número '{numero_processo}'.",
        )


@router.post("", response_model=ProcessoDetalhesResponse, status_code=status.HTTP_201_CREATED)
def cadastrar_processo(
    payload: ProcessoCadastroRequest,
    db: Session = Depends(get_db),
    usuario: Optional[Usuario] = Depends(get_optional_current_user),
) -> ProcessoDetalhesResponse:
    """
    Cadastra manualmente um processo na Base de Conhecimento (RF-08).
    Partes e resumo são anonimizados antes da persistência (RN-01). Retorna 409 se o número CNJ já existir.
    """
    _garantir_numero_unico(db, payload.numero_processo)

    short_hash = hashlib.sha1(f"{payload.numero_processo}-{uuid.uuid4()}".encode("utf-8")).hexdigest()[:5]
    proc = Processo(
        id_processo=f"proc-{short_hash}",
        usuario_id=usuario.id if usuario else "usr-01",
        numero_processo=payload.numero_processo,
        arquivo_nome="cadastro_manual",
        origem_ingestao="MANUAL",
    )
    db.add(proc)
    _aplicar_cadastro(db, proc, payload)
    db.commit()

    return obter_detalhes_processo(proc.id_processo, db)


@router.put("/{id_processo}", response_model=ProcessoDetalhesResponse, status_code=status.HTTP_200_OK)
def editar_processo(
    id_processo: str,
    payload: ProcessoCadastroRequest,
    db: Session = Depends(get_db),
    _usuario: Optional[Usuario] = Depends(get_optional_current_user),
) -> ProcessoDetalhesResponse:
    """
    Edita (substituição completa dos campos editáveis) um processo existente (RF-08).
    Nomes já mascarados (com '***') são preservados; novos nomes passam pela barreira LGPD (RN-01).
    Retorna 404 se o processo não existir e 409 se o novo número CNJ pertencer a outro processo.
    """
    proc = db.query(Processo).filter(Processo.id_processo == id_processo).first()
    if not proc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processo '{id_processo}' não encontrado na base de conhecimento.",
        )
    _garantir_numero_unico(db, payload.numero_processo, ignorar_id=id_processo)

    _aplicar_cadastro(db, proc, payload)
    db.commit()

    return obter_detalhes_processo(proc.id_processo, db)


@router.delete(
    "/{id_processo}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Excluir processo judicial",
    description=(
        "Remove definitivamente um processo da base de conhecimento pelo seu ID. "
        "As entidades associadas (análise preditiva e logs de auditoria LGPD) são excluídas "
        "automaticamente em cascata. Retorna HTTP 204 em caso de sucesso ou HTTP 404 se não encontrado."
    ),
    responses={
        status.HTTP_204_NO_CONTENT: {
            "description": "Processo e registros vinculados excluídos com sucesso.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Processo não encontrado na base de conhecimento.",
        },
    },
)
def excluir_processo(
    id_processo: str,
    db: Session = Depends(get_db),
    _usuario: Optional[Usuario] = Depends(get_optional_current_user),
) -> Response:
    """
    Exclui um processo judicial da Base de Conhecimento (RF-08).
    Aproveita a remoção em cascata (cascade='all, delete-orphan') para apagar a análise preditiva e logs LGPD.
    """
    proc = db.query(Processo).filter(Processo.id_processo == id_processo).first()
    if not proc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processo '{id_processo}' não encontrado na base de conhecimento.",
        )

    db.delete(proc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/datajud/sincronizar",
    response_model=DataJudSincronizacaoResponse,
    status_code=status.HTTP_200_OK,
    summary="Coletar e sincronizar lote de processos e jurisprudências via DataJud (CNJ)",
)
async def sincronizar_lote_datajud(
    payload: DataJudSincronizacaoRequest = DataJudSincronizacaoRequest(),
    db: Session = Depends(get_db),
    usuario: Optional[Usuario] = Depends(get_optional_current_user),
) -> DataJudSincronizacaoResponse:
    """
    Executa a coleta automática em lote de processos e jurisprudências na API Pública do DataJud (CNJ)
    (com fallback local resiliente) e atualiza a base histórica de forma idempotente (Card #27 / RF-08 / RN-01).
    Todos os registros passam pelo AnonimizadorLGPD antes da persistência.
    """
    tribunal_sigla = (payload.tribunal or "TJAL").strip().upper()
    coletados, fonte = await DataJudClient.coletar_lote_jurisprudencia(
        tribunal=tribunal_sigla,
        tema=payload.tema,
        limite=payload.limite,
    )

    novos_inseridos = 0
    atualizados = 0
    total_lgpd = 0
    itens_sincronizados: list[ProcessoListItemSchema] = []

    for item in coletados:
        dados_cadastro = DataJudClient.extrair_registro_para_acervo(item)
        req_cadastro = ProcessoCadastroRequest(**dados_cadastro)

        existing = db.query(Processo).filter(Processo.numero_processo == req_cadastro.numero_processo).first()
        if existing:
            proc = existing
            atualizados += 1
        else:
            short_hash = hashlib.sha1(f"{req_cadastro.numero_processo}-{uuid.uuid4()}".encode("utf-8")).hexdigest()[:5]
            proc = Processo(
                id_processo=f"proc-{short_hash}",
                usuario_id=usuario.id if usuario else "usr-01",
                numero_processo=req_cadastro.numero_processo,
                arquivo_nome=f"datajud_{tribunal_sigla.lower()}_sync",
                origem_ingestao="DATAJUD",
            )
            db.add(proc)
            novos_inseridos += 1

        _aplicar_cadastro(db, proc, req_cadastro)
        db.flush()

        ultimo_log = proc.logs_lgpd[-1] if proc.logs_lgpd else None
        if ultimo_log:
            total_lgpd += (ultimo_log.total_cpfs_mascarados or 0) + (ultimo_log.total_nomes_mascarados or 0)

        itens_sincronizados.append(_converter_para_list_item(proc))

    db.commit()

    return DataJudSincronizacaoResponse(
        tribunal=tribunal_sigla,
        fonte=fonte,
        total_coletados=len(coletados),
        novos_inseridos=novos_inseridos,
        atualizados=atualizados,
        total_entidades_anonimizadas_lgpd=total_lgpd,
        mensagem=(
            f"Sincronização DataJud ({tribunal_sigla}) concluída: "
            f"{novos_inseridos} novo(s) processo(s) inserido(s) e {atualizados} atualizado(s) com proteção LGPD."
        ),
        itens=itens_sincronizados,
    )


@router.get("/datajud/{numero_processo}", response_model=DataJudProcessoResponse, status_code=status.HTTP_200_OK)
async def consultar_processo_datajud(
    numero_processo: str,
    db: Session = Depends(get_db),
    _usuario: Optional[Usuario] = Depends(get_optional_current_user),
) -> DataJudProcessoResponse:
    """
    Consulta metadados processuais na API Pública do DataJud (CNJ) com fallback local (TJAL).
    Rastreabilidade: EAP 1.4.2 / RF-08 / ADR-002
    """
    return await DataJudClient.consultar_processo(numero_processo=numero_processo, db=db)


@router.get("/{id_processo}/similares", response_model=ProcessoListResponse, status_code=status.HTTP_200_OK)
def listar_processos_similares(
    id_processo: str,
    limite: int = Query(default=5, ge=1, le=50, description="Quantidade máxima de precedentes similares"),
    db: Session = Depends(get_db),
    _usuario: Optional[Usuario] = Depends(get_optional_current_user),
) -> ProcessoListResponse:
    """
    Localiza e retorna os processos reais mais semelhantes ao processo informado (RF-06 / Card #35),
    ordenados por correspondência de tema, magistrado, comarca e vocabulário da ementa.
    """
    proc = db.query(Processo).filter(Processo.id_processo == id_processo).first()
    if not proc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processo '{id_processo}' não encontrado na base de conhecimento.",
        )

    similares = _buscar_processos_similares_reais(
        db,
        tema=proc.tema,
        magistrado=proc.magistrado,
        comarca=proc.comarca,
        resumo=proc.resumo_nlp,
        ignorar_id=proc.id_processo,
    )
    recorte = similares[:limite]
    return ProcessoListResponse(
        total=len(similares),
        pagina=1,
        itens=[_converter_para_list_item(p) for p in recorte],
    )


@router.get("/{id_processo}", response_model=ProcessoDetalhesResponse, status_code=status.HTTP_200_OK)
def obter_detalhes_processo(
    id_processo: str,
    db: Session = Depends(get_db),
    _usuario: Optional[Usuario] = Depends(get_optional_current_user),
) -> ProcessoDetalhesResponse:
    """Retorna os metadados higienizados, resumo NLP e parecer preditivo de um processo específico."""
    proc = db.query(Processo).filter(Processo.id_processo == id_processo).first()
    if not proc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processo '{id_processo}' não encontrado na base de conhecimento.",
        )

    pred = proc.analise_preditiva
    ultimo_log = proc.logs_lgpd[-1] if proc.logs_lgpd else None
    if pred is not None:
        total_similares = pred.casos_similares_encontrados
    else:
        total_similares = len(
            _buscar_processos_similares_reais(
                db,
                tema=proc.tema,
                magistrado=proc.magistrado,
                comarca=proc.comarca,
                resumo=proc.resumo_nlp,
                ignorar_id=proc.id_processo,
            )
        )

    return ProcessoDetalhesResponse(
        id_processo=proc.id_processo,
        arquivo_nome=proc.arquivo_nome,
        status=proc.status,
        resultado=proc.resultado_historico,
        data_julgamento=proc.data_julgamento,
        metadados_extraidos=MetadadosExtraidosSchema(
            numero_processo=proc.numero_processo,
            tema=proc.tema,
            magistrado=proc.magistrado,
            comarca=proc.comarca,
            partes_anonimizadas=PartesAnonimizadasSchema(
                autor=proc.autor_anonimizado,
                reu=proc.reu_anonimizado,
            ),
        ),
        resumo_nlp=proc.resumo_nlp,
        analise_preditiva=AnalisePreditivaSchema(
            probabilidade_deferimento=pred.probabilidade_deferimento if pred else 0.70,
            margem_confianca=pred.margem_confianca if pred else 0.08,
            tempo_estimado_sentenca_meses=pred.tempo_estimado_sentenca_meses if pred else 12,
            casos_similares_encontrados=total_similares,
            tese_recomendada=pred.tese_recomendada if pred else "Análise baseada na jurisprudência dominante.",
            tendencia_juiz=pred.tendencia_juiz if pred else f"Histórico consolidado para {proc.magistrado}.",
            provedor_ia=pred.provedor_ia_utilizado if pred else "local_heuristic",
        ),
        auditoria_lgpd=AuditoriaLGPDSchema(
            total_cpfs_mascarados=ultimo_log.total_cpfs_mascarados if ultimo_log else 0,
            total_nomes_mascarados=ultimo_log.total_nomes_mascarados if ultimo_log else 1,
            texto_higienizado_verificado=True,
        ),
    )


def _aplicar_jurimetria_granular(
    db: Session,
    resultado: ResultadoComparacaoPecas,
) -> ResultadoComparacaoPecas:
    """Estima a procedência com base em desfechos históricos do mesmo tema."""
    if not resultado.teses:
        resultado.score_geral_favorabilidade_autor_pct = None
        return resultado

    desfecho = func.lower(func.trim(Processo.resultado_historico))
    # O upload de PDF e a importação CSV podem atribuir "Procedente" automaticamente.
    historico = db.query(Processo.tema, desfecho, func.count()).filter(
        Processo.origem_ingestao == "MANUAL",
        desfecho.in_(("procedente", "improcedente")),
        Processo.numero_processo != resultado.numero_processo,
    ).group_by(Processo.tema, desfecho).all()

    total_por_tema: Counter[str] = Counter()
    procedentes_por_tema: Counter[str] = Counter()
    for tema, decisao, quantidade in historico:
        chave = " ".join(tema.casefold().split())
        total_por_tema[chave] += quantidade
        if decisao == "procedente":
            procedentes_por_tema[chave] += quantidade

    estimativas: list[float] = []
    for tese in resultado.teses:
        chave = " ".join(tese.tema.casefold().split())
        total = total_por_tema[chave]
        if total < MIN_JULGADOS_POR_TEMA:
            tese.probabilidade_procedencia_pct = None
            tese.fundamentacao_preditiva = (
                f"Histórico insuficiente: {total} de {MIN_JULGADOS_POR_TEMA} julgados necessários no mesmo tema."
            )
            continue

        procedentes = procedentes_por_tema[chave]
        # A suavização de Laplace evita certeza artificial quando todos os desfechos coincidem.
        estimativa = round(100 * (procedentes + 1) / (total + 2), 1)
        tese.probabilidade_procedencia_pct = estimativa
        tese.fundamentacao_preditiva = (
            f"Referência histórica do tema: {procedentes} de {total} julgados procedentes, "
            "com suavização estatística."
        )
        estimativas.append(estimativa)

    resultado.score_geral_favorabilidade_autor_pct = (
        round(sum(estimativas) / len(estimativas), 1)
        if len(estimativas) == len(resultado.teses)
        else None
    )
    return resultado


@router.post("/comparar-pecas", response_model=ResultadoComparacaoPecas, status_code=status.HTTP_200_OK)
async def comparar_pecas_processuais(
    peticao_inicial: UploadFile = File(...),
    contestacao: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ResultadoComparacaoPecas:
    """
    Realiza o saneamento e confronto analítico de duas peças processuais (Petição Inicial vs. Contestação).
    Rastreabilidade:
    - Art. 357 do CPC (Decisão de Saneamento e Organização do Processo)
    - Art. 341 do CPC (Ônus da Impugnação Específica)
    - Art. 350 do CPC (Fato Impeditivo, Modificativo ou Extintivo)
    - RN-01: Barreira LGPD Obrigatória pré-processamento
    - RN-02: Jurimetria Granular por Tese Controvertida
    """
    nome_inicial = peticao_inicial.filename or "peticao_inicial.pdf"
    nome_contestacao = contestacao.filename or "contestacao.pdf"

    if not nome_inicial.lower().endswith(".pdf") or not nome_contestacao.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ErroProcessamento (RN-04): Formato inválido. Ambas as peças devem ser arquivos com extensão .pdf.",
        )

    bytes_inicial = await peticao_inicial.read()
    bytes_contestacao = await contestacao.read()

    if len(bytes_inicial) > MAX_PDF_SIZE_BYTES or len(bytes_contestacao) > MAX_PDF_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="ErroProcessamento (RN-04 / SEC-05): Um dos arquivos excede o limite máximo permitido de 15MB.",
        )

    try:
        texto_inicial, _ = ExtratorDocumental.extract_text_with_page_markers(bytes_inicial)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ErroProcessamento (RN-04) na Petição Inicial: {str(exc)}",
        ) from exc

    try:
        texto_contestacao, _ = ExtratorDocumental.extract_text_with_page_markers(bytes_contestacao)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ErroProcessamento (RN-04) na Contestação: {str(exc)}",
        ) from exc

    # Invariante RN-01: Higienização prévia estrita sob a LGPD
    sanitized_inicial, cpfs_init, _ = AnonimizadorLGPD.sanitize_text(texto_inicial)
    sanitized_contestacao, cpfs_cont, _ = AnonimizadorLGPD.sanitize_text(texto_contestacao)

    # Identificação de CNJ se presente
    cnj_match = re.search(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b", sanitized_inicial)
    numero_proc = cnj_match.group(0) if cnj_match else None

    # Confronto analítico bidirecional via AIProviderAdapter (Gemini com fallback determinístico local)
    resultado = ai_gateway.comparar_pecas(
        texto_inicial=sanitized_inicial,
        texto_contestacao=sanitized_contestacao,
        numero_processo=numero_proc,
    )

    # RN-02: Calibragem Jurimétrica Granular por Tese Controvertida
    return _aplicar_jurimetria_granular(db, resultado)
