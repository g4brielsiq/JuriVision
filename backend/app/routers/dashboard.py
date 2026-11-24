"""
Router de Métricas de Jurimetria e Dashboard — JuriVision.
Rastreabilidade:
- ARCHITECTURE.md: Seção 8.2 (GET /api/v1/dashboard/metricas)
- MODELING.md: RF-07 (Consolidação de Indicadores no Dashboard), UC-05, CT-07
"""
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import build_processo_visibility_filter, get_optional_current_user
from app.models.entities import Processo, Usuario
from app.schemas.contracts import (
    DashboardMetricasResponse,
    DecisaoJuizSchema,
    DistribuicaoResultadosSchema,
    RecorteAcervoSchema,
    VolumeTemaSchema,
)

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard de Jurimetria (RF-07)"])


@router.get("/metricas", response_model=DashboardMetricasResponse)
def obter_metricas_dashboard(
    tema: Optional[str] = Query(default=None, description="Filtra indicadores por assunto/matéria"),
    juiz: Optional[str] = Query(default=None, description="Filtra indicadores por magistrado(a)"),
    db: Session = Depends(get_db),
    current_user: Optional[Usuario] = Depends(get_optional_current_user),
) -> DashboardMetricasResponse:
    """
    Consolida em tempo real os indicadores globais de jurimetria a partir dos processos
    higienizados visíveis ao usuário atual (RF-07 / UC-05).
    """
    query = db.query(Processo).filter(build_processo_visibility_filter(current_user))
    if tema and tema.strip():
        query = query.filter(Processo.tema.ilike(f"%{tema.strip()}%"))
    if juiz and juiz.strip():
        query = query.filter(Processo.magistrado.ilike(f"%{juiz.strip()}%"))

    processos = query.all()
    total_processos = len(processos)
    recorte = _calcular_recorte(processos)

    if total_processos == 0:
        return DashboardMetricasResponse(
            taxa_exito_global=0.0,
            tempo_medio_tramitacao_meses=12,
            total_processos_analisados=0,
            total_decididos=0,
            decisoes_por_juiz=[],
            volume_por_tema=[],
            distribuicao_resultados=DistribuicaoResultadosSchema(),
            recorte=recorte,
        )

    # Metodologia (nota exibida no painel): só entram no cálculo de proporção as decisões
    # com desfecho conhecido. Procedências e acordos formam o grupo favorável; improcedências
    # o desfavorável. Processos "Em análise" são contados à parte e ficam fora do denominador,
    # sem projeção preditiva misturada ao histórico.
    favoraveis = 0
    decididos = 0
    dist = {"procedentes": 0, "acordos": 0, "improcedentes": 0, "em_analise": 0}
    juiz_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"procedentes": 0, "improcedentes": 0})
    tema_counts: dict[str, int] = defaultdict(int)
    tema_favs: dict[str, int] = defaultdict(int)
    tema_decididos: dict[str, int] = defaultdict(int)
    tema_prazos: dict[str, list[int]] = defaultdict(list)

    for proc in processos:
        res_lower = (proc.resultado_historico or "").lower()
        tema_counts[proc.tema] += 1

        if res_lower in ("procedente", "acordo"):
            dist["procedentes" if res_lower == "procedente" else "acordos"] += 1
            favoraveis += 1
            decididos += 1
            juiz_counts[proc.magistrado]["procedentes"] += 1
            tema_favs[proc.tema] += 1
            tema_decididos[proc.tema] += 1
        elif res_lower == "improcedente":
            dist["improcedentes"] += 1
            decididos += 1
            juiz_counts[proc.magistrado]["improcedentes"] += 1
            tema_decididos[proc.tema] += 1
        else:
            dist["em_analise"] += 1

        if proc.analise_preditiva is not None:
            tema_prazos[proc.tema].append(proc.analise_preditiva.tempo_estimado_sentenca_meses)

    taxa_exito_global = round(favoraveis / decididos, 3) if decididos else 0.0

    prazos = [
        p.analise_preditiva.tempo_estimado_sentenca_meses
        for p in processos
        if p.analise_preditiva is not None
    ]
    if prazos:
        tempo_medio = int(round(sum(prazos) / len(prazos)))
    else:
        tempo_medio = 14

    decisoes_por_juiz = [
        DecisaoJuizSchema(
            juiz=juiz_nome,
            procedentes=counts["procedentes"],
            improcedentes=counts["improcedentes"],
        )
        for juiz_nome, counts in sorted(
            juiz_counts.items(),
            key=lambda item: (item[1]["procedentes"] + item[1]["improcedentes"]),
            reverse=True,
        )
    ]

    volume_por_tema = []
    for tema_nome, qtd in sorted(tema_counts.items(), key=lambda item: item[1], reverse=True):
        fav_tema = tema_favs[tema_nome]
        decididos_tema = tema_decididos[tema_nome]
        prazos_tema = tema_prazos[tema_nome]
        tempo_tema = (
            max(int(round(sum(prazos_tema) / len(prazos_tema))), 1)
            if prazos_tema
            else max(tempo_medio, 1)
        )
        volume_por_tema.append(
            VolumeTemaSchema(
                tema=tema_nome,
                percentual=round((qtd / total_processos) * 100, 1),
                total=qtd,
                favoraveis=fav_tema,
                decididos=decididos_tema,
                taxa_favoravel=round((fav_tema / decididos_tema) * 100, 1) if decididos_tema else 0.0,
                tempo_medio_meses=tempo_tema,
            )
        )

    return DashboardMetricasResponse(
        taxa_exito_global=taxa_exito_global,
        tempo_medio_tramitacao_meses=max(tempo_medio, 1),
        total_processos_analisados=total_processos,
        total_decididos=decididos,
        decisoes_por_juiz=decisoes_por_juiz,
        volume_por_tema=volume_por_tema,
        distribuicao_resultados=DistribuicaoResultadosSchema(**dist),
        recorte=recorte,
    )


def _calcular_recorte(processos: list[Processo]) -> RecorteAcervoSchema:
    """Descreve o recorte real do acervo visível (órgãos julgadores e período), sem valores fixos."""
    comarca_counts: dict[str, int] = defaultdict(int)
    anos: list[int] = []
    for proc in processos:
        nome = (proc.comarca or "").strip()
        if nome:
            comarca_counts[nome] += 1
        if proc.data_julgamento is not None:
            anos.append(proc.data_julgamento.year)

    comarcas = [
        nome for nome, _ in sorted(comarca_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    return RecorteAcervoSchema(
        orgaos_julgadores=comarcas[:5],
        total_orgaos_julgadores=len(comarcas),
        ano_inicial=min(anos) if anos else None,
        ano_final=max(anos) if anos else None,
    )
