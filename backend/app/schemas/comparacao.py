"""
Contratos Formais e Estruturas de Dados do Visualizador Comparativo de Peças (Pydantic v2).
Petição Inicial vs. Contestação (Saneamento Processual - Art. 357 do CPC).
Rastreabilidade:
- RN-01: Barreira LGPD Obrigatória
- RN-02: Jurimetria Granular por Ponto Controvertido
- CPC: Arts. 341 (Impugnação Específica / Omissão), 350 (Fato Novo da Defesa) e 357 (Decisão de Saneamento)
"""
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class StatusTese(str, Enum):
    CONVERGENTE = "convergente"
    DIVERGENTE = "divergente"
    INCONTROVERSO_POR_OMISSAO = "fato_incontroverso_por_omissao"
    FATO_NOVO_DEFESA = "fato_novo_ou_extintivo_reu"


class TipoTese(str, Enum):
    PRELIMINAR = "preliminar"
    PREJUDICIAL_MERITO = "prejudicial_merito"
    FATO_CRONOLOGIA = "fato_ou_valor"
    MERITO = "merito"
    TUTELA_PROVISORIA = "tutela_provisoria"
    PROVA_ONUS = "prova_e_onus"
    PEDIDO = "pedido_e_valor_causa"


class PontoControvertido(BaseModel):
    id_tese: str = Field(
        description="Identificador único sequencial, ex: 'TESE-01'."
    )
    tipo: TipoTese = Field(
        description="Categoria jurídica estrita entre os 7 eixos de análise processual."
    )
    tema: str = Field(
        description="Título curto e objetivo (ex: 'Data do Inadimplemento', 'Inversão do Ônus da Prova', 'Prescrição Trienal')."
    )
    trecho_autor: Optional[str] = Field(
        default=None,
        description="Citação literal exata extraída da Petição Inicial (sem alterar palavras). Deve ser null apenas se status='fato_novo_ou_extintivo_reu'."
    )
    trecho_reu: Optional[str] = Field(
        default=None,
        description="Citação literal exata extraída da Contestação. Deve ser null apenas se status='fato_incontroverso_por_omissao'."
    )
    status: StatusTese = Field(
        description="Classificação do confronto conforme arts. 341 e 350 do CPC."
    )
    forca_probatoria_autor: str = Field(
        description="Avaliação objetiva do lastro probatório do autor neste ponto (ex: 'Documental Robusta - Contrato Assinado')."
    )
    forca_probatoria_reu: str = Field(
        description="Avaliação objetiva do lastro probatório do réu neste ponto (ex: 'Mera Alegação Retórica' ou 'Não Impugnado')."
    )
    probabilidade_procedencia_pct: float = Field(
        ge=0.0,
        le=100.0,
        description="Estimativa percentual de êxito do autor neste ponto."
    )
    fundamentacao_preditiva: str = Field(
        description="Justificativa técnica cruzando provas apresentadas, norma aplicável e histórico jurimétrico."
    )
    impacto_processual: str = Field(
        description="Orientação prática acionável em 1 frase para o advogado (ex: 'Requerer reconhecimento de fato incontroverso em réplica')."
    )
    pagina_autor: Optional[int] = Field(
        default=None,
        description="Número inteiro da página extraído da tag [PÁG XX] da Petição Inicial."
    )
    pagina_reu: Optional[int] = Field(
        default=None,
        description="Número inteiro da página extraído da tag [PÁG XX] da Contestação."
    )


class ResultadoComparacaoPecas(BaseModel):
    id_comparacao: str = Field(
        description="Identificador único da análise comparativa gerada."
    )
    numero_processo: Optional[str] = Field(
        default=None,
        description="Número único CNJ do processo, se identificado."
    )
    resumo_controvertido_geral: str = Field(
        description="Síntese executiva do litígio, principais pontos controvertidos e riscos processuais."
    )
    total_teses: int = Field(ge=0)
    total_convergencias: int = Field(ge=0)
    total_divergencias: int = Field(ge=0)
    total_omissoes: int = Field(ge=0)
    total_fatos_novos_defesa: int = Field(ge=0)
    score_geral_favorabilidade_autor_pct: float = Field(ge=0.0, le=100.0)
    teses: List[PontoControvertido] = Field(default_factory=list)
    texto_higienizado_autor: Optional[str] = Field(
        default=None,
        description="Texto integral higienizado (LGPD) da petição inicial com marcadores de página."
    )
    texto_higienizado_reu: Optional[str] = Field(
        default=None,
        description="Texto integral higienizado (LGPD) da contestação com marcadores de página."
    )
    criado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
