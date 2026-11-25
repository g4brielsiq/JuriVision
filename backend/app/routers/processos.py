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
from app.core.config import settings
from app.core.datajud_client import DataJudClient
from app.core.database import get_db
from app.core.nlp_engine import (
    classify_legal_theme,
    compute_jurimetria_prediction,
    extract_court_and_judge,
    rank_similar_precedents,
)
from app.core.security import (
    PUBLIC_OWNER_ID,
    build_processo_visibility_filter,
    can_read_processo,
    ensure_can_modify_processo,
    get_effective_user_id,
    get_optional_current_user,
)
from app.models.entities import AnalisePreditiva, LogAuditoriaLGPD, Processo, Usuario
from app.schemas.comparacao import ResultadoComparacaoPecas
from app.schemas.contracts import (
    AnalisePreditivaSchema,
    AuditoriaLGPDSchema,
    ContextoHistoricoSchema,
    CSVUploadResponse,
    DataJudProcessoResponse,
    DataJudSincronizacaoRequest,
    DataJudSincronizacaoResponse,
    FiltrosDisponiveisResponse,
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


def _compute_historical_context(
    db: Session,
    raw_text: str,
    current_user: Optional[Usuario] = None,
) -> ContextoHistoricoSchema:
    """
    Consulta os processos visíveis ao usuário (RN-02) e executa ranqueamento real por
    similaridade textual (TF-IDF + BM25) + Intervalo de Confiança de Wilson.
    """
    sanitized_query, _, _ = AnonimizadorLGPD.sanitize_text(raw_text or "")
    tema_detectado, _, _ = classify_legal_theme(sanitized_query)
    magistrado_detectado, _ = extract_court_and_judge(raw_text or "")

    vis_filter = build_processo_visibility_filter(current_user)
    processes = db.query(Processo).filter(vis_filter).all()

    pred_ctx = compute_jurimetria_prediction(
        query_text=sanitized_query,
        processes=processes,
        target_tema=tema_detectado,
        target_magistrado=magistrado_detectado,
        top_k=15,
    )
    return ContextoHistoricoSchema(**pred_ctx)


@router.post("/upload-pdf", response_model=ProcessoUploadResponse, status_code=status.HTTP_200_OK)
async def upload_processo_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Optional[Usuario] = Depends(get_optional_current_user),
) -> ProcessoUploadResponse:
    """
    Recebe uma petição inicial em PDF (RF-02), valida sua integridade binária (RN-04),
    aplica controle de cotas Freemium (FREE vs PRO), aciona o pipeline isolado de IA com
    barreira LGPD obrigatória (RF-04, RF-05, RF-06) e persiste o processo higienizado (ADR-003).
    """
    if current_user is not None:
        plano_atual = (current_user.plano or "FREE").upper()
        usadas = int(current_user.analises_realizadas or 0)
        if plano_atual == "FREE" and usadas >= settings.FREE_PLAN_PDF_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    f"LimitePlanoFree: Você atingiu o limite gratuito de {settings.FREE_PLAN_PDF_LIMIT} "
                    "análises de petições em PDF no plano FREE. Faça upgrade para o plano JuriVision PRO "
                    "para análises ilimitadas."
                ),
            )

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

    contexto = _compute_historical_context(db, raw_text, current_user=current_user)
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
    owner_id = get_effective_user_id(current_user)

    # Verifica se já existe processo com o mesmo número CNJ para operação idempotente e respeita isolamento
    existing = db.query(Processo).filter(Processo.numero_processo == meta.numero_processo).first()
    if existing:
        if existing.usuario_id not in (None, PUBLIC_OWNER_ID, owner_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe um processo privado registrado com este número CNJ por outro usuário.",
            )
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
            usuario_id=owner_id,
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
    if current_user is not None:
        current_user.analises_realizadas = int(current_user.analises_realizadas or 0) + 1
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
    current_user: Optional[Usuario] = Depends(get_optional_current_user),
) -> CSVUploadResponse:
    """
    Importa em lote registros estruturados via planilha CSV (RF-03),
    aplicando higienização determinística local LGPD em 100% das linhas antes da persistência (RF-04 / RN-01).
    Recurso exclusivo do plano PRO quando autenticado.
    """
    if current_user is not None and (current_user.plano or "FREE").upper() == "FREE":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                "RecursoExclusivoPro: A importação em lote via planilha CSV é exclusiva "
                "para assinantes do plano JuriVision PRO."
            ),
        )

    owner_id = get_effective_user_id(current_user)
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
    visible_processes = db.query(Processo).filter(build_processo_visibility_filter(current_user)).all()

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
        tema_row = norm_row.get("tema") or "Dano Moral"
        mag_row = norm_row.get("magistrado") or "Magistrado não especificado"
        comarca_row = norm_row.get("comarca") or "Juízo Cível Competente"
        resumo_row = clean_resumo or "Resumo importado via lote CSV e higienizado."

        pred_ctx = compute_jurimetria_prediction(
            query_text=f"{tema_row} {mag_row} {comarca_row} {resumo_row}",
            processes=visible_processes,
            target_tema=tema_row,
            target_magistrado=mag_row,
            top_k=15,
        )
        if resultado.lower() in ("procedente", "acordo"):
            prob = 0.76
        elif resultado.lower() == "improcedente":
            prob = 0.38
        else:
            prob = pred_ctx["taxa_favoravel_juiz"]

        existing = db.query(Processo).filter(Processo.numero_processo == num_proc).first()
        if existing:
            if existing.usuario_id not in (None, PUBLIC_OWNER_ID, owner_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"O processo '{num_proc}' pertence de forma privada a outro usuário.",
                )
            proc_id = existing.id_processo
            existing.tema = tema_row
            existing.magistrado = mag_row
            existing.comarca = comarca_row
            existing.autor_anonimizado = autor_anon
            existing.reu_anonimizado = reu_anon
            existing.resumo_nlp = resumo_row
            existing.resultado_historico = resultado
            existing.data_julgamento = dt_julg
        else:
            short_hash = hashlib.sha1(f"{num_proc}-{uuid.uuid4()}".encode("utf-8")).hexdigest()[:5]
            proc_id = f"proc-{short_hash}"
            proc_obj = Processo(
                id_processo=proc_id,
                usuario_id=owner_id,
                numero_processo=num_proc,
                arquivo_nome=filename,
                origem_ingestao="CSV",
                status="PROCESSADO",
                tema=tema_row,
                magistrado=mag_row,
                comarca=comarca_row,
                autor_anonimizado=autor_anon,
                reu_anonimizado=reu_anon,
                resumo_nlp=resumo_row,
                resultado_historico=resultado,
                data_julgamento=dt_julg,
            )
            db.add(proc_obj)
            db.flush()

            _, default_tese, _ = classify_legal_theme(f"{tema_row} {resumo_row}")
            tese_csv = pred_ctx["tese_precedente_similar"] or default_tese
            sim_count = pred_ctx["total_casos_similares"]
            margem_csv = pred_ctx["margem_confianca_calculada"]
            prazo_csv = pred_ctx["tempo_medio_meses"]

            db.add(
                AnalisePreditiva(
                    id_processo=proc_id,
                    probabilidade_deferimento=prob,
                    margem_confianca=margem_csv,
                    tempo_estimado_sentenca_meses=prazo_csv,
                    casos_similares_encontrados=sim_count,
                    tese_recomendada=tese_csv,
                    tendencia_juiz=(
                        f"Comparação estatística com {sim_count} precedente(s) similar(es) para "
                        f"{proc_obj.magistrado} (margem ±{int(round(margem_csv * 100))}%)."
                    ),
                    provedor_ia_utilizado="local_heuristic",
                )
            )
            visible_processes.append(proc_obj)

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
        resumo_curto=p.resumo_nlp,
    )


@router.get("", response_model=ProcessoListResponse, status_code=status.HTTP_200_OK)
def listar_processos(
    tema: Optional[str] = Query(default=None, description="Filtrar por tema jurídico"),
    juiz: Optional[str] = Query(default=None, description="Filtrar por nome do magistrado"),
    comarca: Optional[str] = Query(default=None, description="Filtrar por comarca ou órgão julgador"),
    tribunal: Optional[str] = Query(default=None, description="Filtrar por sigla ou código CNJ do tribunal (ex: TJAL)"),
    busca: Optional[str] = Query(default=None, description="Busca textual livre (CNJ, tema, juiz, comarca ou partes)"),
    ordenacao: Optional[str] = Query(
        default="recentes", description="Ordenação no servidor: recentes | antigas | assunto"
    ),
    ids: Optional[str] = Query(
        default=None, description="Filtro opcional de IDs separados por vírgula (ex: proc-1001,proc-1004)"
    ),
    pagina: int = Query(default=1, ge=1, description="Página atual"),
    limite: int = Query(default=10, ge=1, le=100, description="Itens por página"),
    db: Session = Depends(get_db),
    current_user: Optional[Usuario] = Depends(get_optional_current_user),
) -> ProcessoListResponse:
    """
    Lista e filtra processos higienizados visíveis na Base de Conhecimento com paginação (RF-08 / UC-06 / UC-07).
    """
    query = db.query(Processo).filter(build_processo_visibility_filter(current_user))

    if ids is not None:
        id_list = [item.strip() for item in ids.split(",") if item.strip()]
        if not id_list:
            query = query.filter(Processo.id_processo == "__nenhum__")
        else:
            query = query.filter(Processo.id_processo.in_(id_list))

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
    if ordenacao == "antigas":
        ordered_query = query.order_by(Processo.data_julgamento.asc(), Processo.criado_em.asc())
    elif ordenacao == "assunto":
        ordered_query = query.order_by(
            Processo.tema.asc(), Processo.data_julgamento.desc(), Processo.criado_em.desc()
        )
    else:
        ordered_query = query.order_by(Processo.data_julgamento.desc(), Processo.criado_em.desc())

    registros = ordered_query.offset(offset).limit(limite).all()

    itens = [_converter_para_list_item(p) for p in registros]

    return ProcessoListResponse(
        total=total,
        pagina=pagina,
        itens=itens,
    )


@router.get("/filtros", response_model=FiltrosDisponiveisResponse, status_code=status.HTTP_200_OK)
def obter_filtros_disponiveis(
    db: Session = Depends(get_db),
    current_user: Optional[Usuario] = Depends(get_optional_current_user),
) -> FiltrosDisponiveisResponse:
    """Retorna as listas distintas e ordenadas de temas, magistrados e comarcas visíveis ao usuário."""
    vis_filter = build_processo_visibility_filter(current_user)
    temas = sorted({r[0] for r in db.query(Processo.tema).filter(vis_filter).distinct().all() if r[0]})
    magistrados = sorted(
        {r[0] for r in db.query(Processo.magistrado).filter(vis_filter).distinct().all() if r[0]}
    )
    comarcas = sorted({r[0] for r in db.query(Processo.comarca).filter(vis_filter).distinct().all() if r[0]})
    return FiltrosDisponiveisResponse(temas=temas, magistrados=magistrados, comarcas=comarcas)




# ==============================================================================
# Cadastro e Edição Manual de Processos (RF-08 / RN-01)
# ==============================================================================
RESULTADOS_FAVORAVEIS = ("procedente", "acordo")


def _estimar_analise_preditiva(
    db: Session,
    payload: ProcessoCadastroRequest,
    ignorar_id: Optional[str] = None,
    current_user: Optional[Usuario] = None,
) -> dict:
    """
    Estima os campos de AnalisePreditiva para um processo cadastrado manualmente, usando
    similaridade textual real (TF-IDF + BM25) e Intervalo de Confiança de Wilson sobre o acervo visível.
    """
    base = db.query(Processo).filter(build_processo_visibility_filter(current_user))
    if ignorar_id:
        base = base.filter(Processo.id_processo != ignorar_id)

    candidatos = base.all()
    sanitized_resumo, _, _ = AnonimizadorLGPD.sanitize_text(payload.resumo)
    query_txt = f"{payload.tema} {payload.magistrado} {payload.comarca} {sanitized_resumo}"
    pred_ctx = compute_jurimetria_prediction(
        query_text=query_txt,
        processes=candidatos,
        target_tema=payload.tema,
        target_magistrado=payload.magistrado,
        top_k=15,
    )

    resultado = payload.resultado.lower()
    if resultado in RESULTADOS_FAVORAVEIS:
        probabilidade = 0.76
    elif resultado == "improcedente":
        probabilidade = 0.38
    else:
        probabilidade = pred_ctx["taxa_favoravel_juiz"]

    similares = pred_ctx["total_casos_similares"]
    margem = pred_ctx["margem_confianca_calculada"]
    tempo = pred_ctx["tempo_medio_meses"]
    tese = pred_ctx["tese_precedente_similar"] or (
        f"Análise comparativa baseada em {similares} precedente(s) similar(es) ao tema '{payload.tema}' no acervo."
    )

    return {
        "probabilidade_deferimento": probabilidade,
        "margem_confianca": margem,
        "tempo_estimado_sentenca_meses": max(tempo, 1),
        "casos_similares_encontrados": similares,
        "tese_recomendada": tese,
        "tendencia_juiz": (
            f"Baseado em {similares} precedente(s) similar(es) (margem ±{int(round(margem * 100))}% "
            f"para {payload.magistrado})."
        ),
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


def _aplicar_cadastro(
    db: Session,
    proc: Processo,
    payload: ProcessoCadastroRequest,
    current_user: Optional[Usuario] = None,
) -> None:
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
        estimativa = _estimar_analise_preditiva(
            db, payload, ignorar_id=proc.id_processo, current_user=current_user
        )
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
    current_user: Optional[Usuario] = Depends(get_optional_current_user),
) -> ProcessoDetalhesResponse:
    """
    Cadastra manualmente um processo na Base de Conhecimento (RF-08).
    Partes e resumo são anonimizados antes da persistência (RN-01). Retorna 409 se o número CNJ já existir.
    """
    _garantir_numero_unico(db, payload.numero_processo)

    short_hash = hashlib.sha1(f"{payload.numero_processo}-{uuid.uuid4()}".encode("utf-8")).hexdigest()[:5]
    proc = Processo(
        id_processo=f"proc-{short_hash}",
        usuario_id=get_effective_user_id(current_user),
        numero_processo=payload.numero_processo,
        arquivo_nome="cadastro_manual",
        origem_ingestao="MANUAL",
    )
    db.add(proc)
    _aplicar_cadastro(db, proc, payload, current_user=current_user)
    db.commit()

    return obter_detalhes_processo(proc.id_processo, db, current_user)


@router.put("/{id_processo}", response_model=ProcessoDetalhesResponse, status_code=status.HTTP_200_OK)
def editar_processo(
    id_processo: str,
    payload: ProcessoCadastroRequest,
    db: Session = Depends(get_db),
    current_user: Optional[Usuario] = Depends(get_optional_current_user),
) -> ProcessoDetalhesResponse:
    """
    Edita (substituição completa dos campos editáveis) um processo existente (RF-08).
    Nomes já mascarados (com '***') são preservados; novos nomes passam pela barreira LGPD (RN-01).
    Retorna 404 se o processo não existir/não for visível, 403 se for acervo público externo e 409 se CNJ duplicado.
    """
    proc = db.query(Processo).filter(Processo.id_processo == id_processo).first()
    if not proc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processo '{id_processo}' não encontrado na base de conhecimento.",
        )
    ensure_can_modify_processo(proc, current_user)
    _garantir_numero_unico(db, payload.numero_processo, ignorar_id=id_processo)

    _aplicar_cadastro(db, proc, payload, current_user=current_user)
    db.commit()

    return obter_detalhes_processo(proc.id_processo, db, current_user)


@router.delete(
    "/{id_processo}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Excluir processo judicial",
    description=(
        "Remove definitivamente um processo da base de conhecimento pelo seu ID. "
        "As entidades associadas (análise preditiva e logs de auditoria LGPD) são excluídas "
        "automaticamente em cascata. Retorna HTTP 204 em caso de sucesso, HTTP 403 para acervo público "
        "por conta externa ou HTTP 404 se não encontrado."
    ),
    responses={
        status.HTTP_204_NO_CONTENT: {
            "description": "Processo e registros vinculados excluídos com sucesso.",
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "Acervo público protegido contra exclusão por contas externas.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Processo não encontrado na base de conhecimento.",
        },
    },
)
def excluir_processo(
    id_processo: str,
    db: Session = Depends(get_db),
    current_user: Optional[Usuario] = Depends(get_optional_current_user),
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
    ensure_can_modify_processo(proc, current_user)

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
    current_user: Optional[Usuario] = Depends(get_optional_current_user),
) -> DataJudSincronizacaoResponse:
    """
    Executa a coleta automática em lote de processos e jurisprudências na API Pública do DataJud (CNJ)
    (com fallback local resiliente) e atualiza a base histórica visível de forma idempotente (Card #27 / RF-08 / RN-01).
    Todos os registros passam pelo AnonimizadorLGPD e pelo motor TF-IDF/BM25 antes da persistência.
    """
    tribunal_sigla = (payload.tribunal or "TJAL").strip().upper()
    coletados, fonte = await DataJudClient.coletar_lote_jurisprudencia(
        tribunal=tribunal_sigla,
        tema=payload.tema,
        limite=payload.limite,
    )

    owner_id = get_effective_user_id(current_user)
    novos_inseridos = 0
    atualizados = 0
    total_lgpd = 0
    itens_sincronizados: list[ProcessoListItemSchema] = []

    for item in coletados:
        dados_cadastro = DataJudClient.extrair_registro_para_acervo(item)
        req_cadastro = ProcessoCadastroRequest(**dados_cadastro)

        existing = db.query(Processo).filter(Processo.numero_processo == req_cadastro.numero_processo).first()
        if existing:
            if existing.usuario_id not in (None, PUBLIC_OWNER_ID, owner_id):
                continue
            if (
                current_user is not None
                and current_user.id != PUBLIC_OWNER_ID
                and existing.usuario_id in (None, PUBLIC_OWNER_ID)
            ):
                continue
            proc = existing
            atualizados += 1
        else:
            short_hash = hashlib.sha1(
                f"{req_cadastro.numero_processo}-{uuid.uuid4()}".encode("utf-8")
            ).hexdigest()[:5]
            proc = Processo(
                id_processo=f"proc-{short_hash}",
                usuario_id=owner_id,
                numero_processo=req_cadastro.numero_processo,
                arquivo_nome=f"datajud_{tribunal_sigla.lower()}_sync",
                origem_ingestao="DATAJUD",
            )
            db.add(proc)
            novos_inseridos += 1

        _aplicar_cadastro(db, proc, req_cadastro, current_user=current_user)
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
    current_user: Optional[Usuario] = Depends(get_optional_current_user),
) -> ProcessoListResponse:
    """
    Localiza e retorna os precedentes reais mais semelhantes ao processo informado (RF-06 / Card #35),
    ranqueados por Similaridade de Cosseno TF-IDF + Okapi BM25 dentro do acervo visível ao usuário.
    """
    proc = db.query(Processo).filter(Processo.id_processo == id_processo).first()
    if not proc or not can_read_processo(proc, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processo '{id_processo}' não encontrado na base de conhecimento.",
        )

    candidatos = (
        db.query(Processo)
        .filter(build_processo_visibility_filter(current_user), Processo.id_processo != proc.id_processo)
        .all()
    )
    ranked = rank_similar_precedents(
        query_text=f"{proc.tema} {proc.comarca} {proc.magistrado} {proc.resumo_nlp}",
        processes=candidatos,
        target_tema=proc.tema,
        target_magistrado=proc.magistrado,
        top_k=len(candidatos) or 1,
        min_similarity=0.05,
    )
    by_id = {p.id_processo: p for p in candidatos}
    similares_ordenados = [by_id[item["id_processo"]] for item in ranked if item["id_processo"] in by_id]

    return ProcessoListResponse(
        total=len(similares_ordenados),
        pagina=1,
        itens=[_converter_para_list_item(p) for p in similares_ordenados[:limite]],
    )


@router.get("/{id_processo}", response_model=ProcessoDetalhesResponse, status_code=status.HTTP_200_OK)
def obter_detalhes_processo(
    id_processo: str,
    db: Session = Depends(get_db),
    current_user: Optional[Usuario] = Depends(get_optional_current_user),
) -> ProcessoDetalhesResponse:
    """Retorna os metadados higienizados, resumo NLP e parecer preditivo de um processo específico."""
    proc = db.query(Processo).filter(Processo.id_processo == id_processo).first()
    if not proc or not can_read_processo(proc, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processo '{id_processo}' não encontrado na base de conhecimento.",
        )

    pred = proc.analise_preditiva
    ultimo_log = proc.logs_lgpd[-1] if proc.logs_lgpd else None

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
            casos_similares_encontrados=pred.casos_similares_encontrados if pred else 25,
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
    current_user: Optional[Usuario] = None,
) -> ResultadoComparacaoPecas:
    """Estima a procedência com base em desfechos históricos do mesmo tema (respeitando o isolamento multi-usuário)."""
    if not resultado.teses:
        resultado.score_geral_favorabilidade_autor_pct = None
        return resultado

    desfecho = func.lower(func.trim(Processo.resultado_historico))
    # O upload de PDF e a importação CSV podem atribuir "Procedente" automaticamente.
    historico = db.query(Processo.tema, desfecho, func.count()).filter(
        Processo.origem_ingestao == "MANUAL",
        desfecho.in_(("procedente", "improcedente")),
        Processo.numero_processo != resultado.numero_processo,
        build_processo_visibility_filter(current_user),
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
    current_user: Optional[Usuario] = Depends(get_optional_current_user),
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
    return _aplicar_jurimetria_granular(db, resultado, current_user)
