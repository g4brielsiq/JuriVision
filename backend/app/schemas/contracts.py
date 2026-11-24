"""
Contratos Formais de Entrada e Saída (Pydantic v2).
Rastreabilidade:
- ARCHITECTURE.md: Seção 8 (Contratos Oficiais de API REST — 8.1 a 8.7)
- MODELING.md: RNF-01 (Adequação Funcional — Completude e Correção Funcional), RF-01 a RF-09
"""
from datetime import date
from email.errors import HeaderParseError
from email.headerregistry import Address
import re
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


# ==============================================================================
# 8.1 Autenticação (RF-01)
# ==============================================================================
class LoginRequest(BaseModel):
    email: str = Field(..., examples=["advogado@escritorio.com"])
    senha: str = Field(..., min_length=4, examples=["senhaSegura123"])

class RegisterRequest(BaseModel):
    nome: str = Field(min_length=2, max_length=150, examples=["Ana Pereira"])
    email: str = Field(max_length=150, examples=["ana@escritorio.com"])
    senha: str = Field(min_length=8, max_length=128, repr=False)
    numero_oab: str = Field(max_length=50, examples=["54321/AL"])

    @field_validator("nome", "email", mode="before")
    @classmethod
    def aparar_espacos(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("nome")
    @classmethod
    def validar_nome(cls, value: str) -> str:
        if re.search(r"[\x00-\x1f\x7f]", value):
            raise ValueError("O nome contém caracteres inválidos.")
        return value

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, value: str) -> str:
        try:
            endereco = Address(addr_spec=value)
        except (ValueError, HeaderParseError):
            raise ValueError("Informe um e-mail válido.") from None
        if endereco.addr_spec != value or not re.fullmatch(
            r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
            r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+",
            endereco.domain,
        ):
            raise ValueError("Informe um e-mail válido.")
        return value.lower()

    @field_validator("senha")
    @classmethod
    def validar_senha(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Informe uma senha com pelo menos 8 caracteres.")
        return value

    @field_validator("numero_oab")
    @classmethod
    def normalizar_oab(cls, value: str) -> str:
        inscricao = re.fullmatch(r"([0-9]+) */ *([a-zA-Z]{2})", value.strip())
        ufs = "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
        if not inscricao or inscricao[2].upper() not in ufs:
            raise ValueError("Informe a OAB no formato número/UF, como 54321/AL.")
        return f"{inscricao[1]}/{inscricao[2].upper()}"


class UsuarioProfileSchema(BaseModel):
    id: str
    nome: str
    oab: str


class RegisterResponse(UsuarioProfileSchema):
    email: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioProfileSchema


PlanoTipo = Literal["FREE", "PRO"]


class PlanoAssinaturaStatusResponse(BaseModel):
    usuario_id: str
    nome: str
    plano: PlanoTipo = "FREE"
    analises_realizadas: int = Field(default=0, ge=0)
    limite_analises_free: int = Field(default=3, ge=1)
    analises_restantes: int = Field(default=3, ge=0)
    recursos_pro_liberados: bool = False
    lote_csv_liberado: bool = False
    tese_aprofundada_liberada: bool = False
    exportacao_pdf_ilimitada: bool = False


class PlanoUpgradeRequest(BaseModel):
    plano: PlanoTipo = Field(default="PRO")
    codigo_convite: Optional[str] = Field(default="CONAD2026", max_length=60)


# ==============================================================================
# 8.2 Métricas de Jurimetria — Dashboard (RF-07)
# ==============================================================================
class DecisaoJuizSchema(BaseModel):
    juiz: str
    procedentes: int = Field(..., ge=0)
    improcedentes: int = Field(..., ge=0)


class DistribuicaoResultadosSchema(BaseModel):
    procedentes: int = Field(default=0, ge=0)
    acordos: int = Field(default=0, ge=0)
    improcedentes: int = Field(default=0, ge=0)
    em_analise: int = Field(default=0, ge=0)


class VolumeTemaSchema(BaseModel):
    tema: str
    percentual: float = Field(..., ge=0.0, le=100.0)
    total: int = Field(default=0, ge=0)
    favoraveis: int = Field(default=0, ge=0)
    decididos: int = Field(default=0, ge=0, description="Decisões do tema com desfecho (base da taxa favorável)")
    taxa_favoravel: float = Field(default=0.0, ge=0.0, le=100.0)
    tempo_medio_meses: int = Field(default=12, ge=1)


class RecorteAcervoSchema(BaseModel):
    orgaos_julgadores: List[str] = Field(default_factory=list)
    total_orgaos_julgadores: int = Field(default=0, ge=0)
    ano_inicial: Optional[int] = None
    ano_final: Optional[int] = None


class DashboardMetricasResponse(BaseModel):
    taxa_exito_global: float = Field(..., ge=0.0, le=1.0)
    tempo_medio_tramitacao_meses: int = Field(..., ge=1)
    total_processos_analisados: int = Field(..., ge=0)
    total_decididos: int = Field(
        default=0, ge=0, description="Decisões com desfecho (procedente, acordo, improcedente): denominador da taxa"
    )
    decisoes_por_juiz: List[DecisaoJuizSchema]
    volume_por_tema: List[VolumeTemaSchema]
    distribuicao_resultados: DistribuicaoResultadosSchema = Field(
        default_factory=DistribuicaoResultadosSchema
    )
    recorte: RecorteAcervoSchema = Field(default_factory=RecorteAcervoSchema)


# ==============================================================================
# 8.3 Ingestão de Processo via PDF & Predição (RF-02, RF-04, RF-05, RF-06)
# ==============================================================================
class PartesAnonimizadasSchema(BaseModel):
    autor: str
    reu: str


class MetadadosExtraidosSchema(BaseModel):
    numero_processo: str
    tema: str
    magistrado: str
    comarca: str
    partes_anonimizadas: PartesAnonimizadasSchema


class AnalisePreditivaSchema(BaseModel):
    probabilidade_deferimento: float = Field(..., ge=0.0, le=1.0)
    margem_confianca: float = Field(..., ge=0.0, le=1.0)
    tempo_estimado_sentenca_meses: int = Field(..., ge=1)
    casos_similares_encontrados: int = Field(..., ge=0)
    tese_recomendada: str
    tendencia_juiz: str
    provedor_ia: str = "local_heuristic"


class AuditoriaLGPDSchema(BaseModel):
    total_cpfs_mascarados: int = 0
    total_nomes_mascarados: int = 0
    texto_higienizado_verificado: bool = True


class ProcessoUploadResponse(BaseModel):
    id_processo: str
    arquivo_nome: str
    status: str
    metadados_extraidos: MetadadosExtraidosSchema
    resumo_nlp: str
    analise_preditiva: AnalisePreditivaSchema
    auditoria_lgpd: Optional[AuditoriaLGPDSchema] = None


# ==============================================================================
# 8.4 Ingestão em Lote via Planilha CSV (RF-03, RF-04)
# ==============================================================================
class CSVUploadResponse(BaseModel):
    lote_status: str
    arquivo_nome: str
    total_registros_lidos: int = Field(..., ge=0)
    total_importados_com_sucesso: int = Field(..., ge=0)
    total_entidades_anonimizadas_lgpd: int = Field(..., ge=0)


# ==============================================================================
# 8.5 Consulta e Base de Conhecimento (RF-08)
# ==============================================================================
class ProcessoListItemSchema(BaseModel):
    id_processo: str
    numero_processo: str
    tema: str
    magistrado: str
    comarca: str
    partes_anonimizadas: str
    resultado: str
    data_julgamento: Optional[str] = None
    probabilidade_deferimento: Optional[float] = None
    resumo_curto: Optional[str] = None


class ProcessoListResponse(BaseModel):
    total: int = Field(..., ge=0)
    pagina: int = Field(..., ge=1)
    itens: List[ProcessoListItemSchema]


class FiltrosDisponiveisResponse(BaseModel):
    temas: List[str]
    magistrados: List[str]
    comarcas: List[str]


# ==============================================================================
# 8.5.1 Cadastro e Edição Manual de Processos (RF-08 / RN-01)
# ==============================================================================
CNJ_PATTERN = r"^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$"

ResultadoProcesso = Literal["Procedente", "Improcedente", "Acordo", "Em Analise"]


class ProcessoDetalhesResponse(ProcessoUploadResponse):
    resultado: str
    data_julgamento: Optional[date]


class ProcessoAnonimizacaoRequest(BaseModel):
    autor: str = Field(default="", max_length=200)
    reu: str = Field(default="", max_length=200)
    resumo: str = ""


class ProcessoAnonimizacaoResponse(BaseModel):
    partes_anonimizadas: PartesAnonimizadasSchema
    resumo: str
    auditoria_lgpd: AuditoriaLGPDSchema


class ProcessoCadastroRequest(BaseModel):
    """
    Corpo de entrada para cadastro (POST) e edição completa (PUT) de um processo.
    Os nomes das partes e o resumo são recebidos em texto bruto e SEMPRE passam pelo
    AnonimizadorLGPD antes da persistência (RN-01). Nada é gravado sem máscara.
    """

    numero_processo: str = Field(
        ...,
        pattern=CNJ_PATTERN,
        description="Número CNJ no formato NNNNNNN-DD.AAAA.J.TR.OOOO",
        examples=["0801234-56.2025.8.02.0001"],
    )
    tema: str = Field(..., min_length=2, max_length=120, examples=["Dano Moral"])
    magistrado: str = Field(..., min_length=2, max_length=150, examples=["Dr. Rafael De Amorim"])
    comarca: str = Field(
        default="1ª Vara Cível de Maceió", min_length=2, max_length=150, examples=["1ª Vara Cível de Maceió"]
    )
    autor: str = Field(..., min_length=2, max_length=200, examples=["Maria Aparecida Santos"])
    reu: str = Field(..., min_length=2, max_length=200, examples=["Banco do Brasil S.A."])
    resumo: str = Field(..., min_length=10, description="Ementa ou síntese dos fatos (será higienizada)")
    resultado: ResultadoProcesso = Field(default="Em Analise")
    data_julgamento: Optional[date] = Field(default=None, examples=["2025-08-15"])

    @field_validator("numero_processo", "tema", "magistrado", "comarca", "autor", "reu", "resumo", mode="before")
    @classmethod
    def _strip_texto(cls, value):
        return value.strip() if isinstance(value, str) else value


# ==============================================================================
# 8.7 Contrato Interno Back-end <-> AI Engine (ADR-001 / ADR-002)
# ==============================================================================
class PrecedenteSimilarSchema(BaseModel):
    id_processo: str
    numero_processo: str
    tema: str
    magistrado: str
    resultado: str
    similaridade: float
    prazo_meses: int = 12
    tese: str = ""


class ContextoHistoricoSchema(BaseModel):
    total_casos_similares: int = 42
    taxa_favoravel_juiz: float = 0.72
    tempo_medio_meses: int = 9
    margem_confianca_calculada: Optional[float] = None
    tese_precedente_similar: Optional[str] = None
    magistrado_inferido: Optional[str] = None
    precedentes_similares: List[PrecedenteSimilarSchema] = []


class InternalAnalyzeRequest(BaseModel):
    arquivo_nome: str
    texto_bruto: str
    contexto_historico: ContextoHistoricoSchema


class InternalAnalyzeResponse(BaseModel):
    metadados_extraidos: MetadadosExtraidosSchema
    resumo_nlp: str
    analise_preditiva: AnalisePreditivaSchema
    auditoria_lgpd: AuditoriaLGPDSchema


# ==============================================================================
# 8.8 Consulta Pública DataJud / CNJ (Integração Híbrida)
# ==============================================================================
class DataJudMovimentoSchema(BaseModel):
    codigo: Optional[int] = None
    nome: str
    data_hora: Optional[str] = None


class DataJudAssuntoSchema(BaseModel):
    codigo: Optional[int] = None
    nome: str
    principal: Optional[bool] = False


class DataJudProcessoResponse(BaseModel):
    numero_processo: str
    tribunal: str
    classe: str
    classe_codigo: Optional[int] = None
    assuntos: List[DataJudAssuntoSchema] = []
    assunto_principal: str
    orgao_julgador: str
    data_ajuizamento: Optional[str] = None
    grau: Optional[str] = None
    movimentos_recentes: List[DataJudMovimentoSchema] = []
    fonte: str = "datajud_api"  # "datajud_api" | "local_cache_fallback"
    sucesso: bool = True
    mensagem: str = "Metadados recuperados com sucesso da API Pública do DataJud."


class DataJudSincronizacaoRequest(BaseModel):
    tribunal: str = Field(
        default="TJAL",
        min_length=2,
        max_length=20,
        description="Sigla do tribunal para coleta automática (ex.: TJAL, TJSP, TJRJ, TJPE, TRF5)",
        examples=["TJAL"],
    )
    tema: Optional[str] = Field(
        default=None,
        max_length=120,
        description="Filtro opcional de assunto/matéria jurisprudencial para coleta direcionada",
        examples=["Dano Moral"],
    )
    limite: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Quantidade máxima de processos e jurisprudências a coletar no lote",
    )


class DataJudSincronizacaoResponse(BaseModel):
    tribunal: str
    fonte: str = "datajud_api"  # "datajud_api" | "local_cache_fallback"
    total_coletados: int = Field(..., ge=0)
    novos_inseridos: int = Field(..., ge=0)
    atualizados: int = Field(..., ge=0)
    total_entidades_anonimizadas_lgpd: int = Field(default=0, ge=0)
    mensagem: str
    itens: List[ProcessoListItemSchema] = []

