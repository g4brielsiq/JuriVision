"""
Router de Métricas de Jurimetria e Dashboard — JuriVision.
Rastreabilidade:
- ARCHITECTURE.md: Seção 8.2 (GET /api/v1/dashboard/metricas)
- MODELING.md: RF-07 (Consolidação de Indicadores no Dashboard), UC-05, CT-07
"""
from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import AnalisePreditiva, Processo
from app.schemas.contracts import (
    DashboardMetricasResponse,
    DecisaoJuizSchema,
    VolumeTemaSchema,
)

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard de Jurimetria (RF-07)"])


@router.get("/metricas", response_model=DashboardMetricasResponse)
def obter_metricas_dashboard(db: Session = Depends(get_db)) -> DashboardMetricasResponse:
    """
    Consolida em tempo real os indicadores globais de jurimetria a partir dos processos
    higienizados persistidos no banco relacional (RF-07 / UC-05).
    """
    processos = db.query(Processo).all()
    total_processos = len(processos)

    if total_processos == 0:
        return DashboardMetricasResponse(
            taxa_exito_global=0.0,
            tempo_medio_tramitacao_meses=12,
            total_processos_analisados=0,
            decisoes_por_juiz=[],
            volume_por_tema=[],
        )

    favoraveis = 0
    juiz_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"procedentes": 0, "improcedentes": 0})
    tema_counts: dict[str, int] = defaultdict(int)

    for proc in processos:
        res_lower = (proc.resultado_historico or "").lower()
        is_favorable = res_lower in ("procedente", "acordo")
        if is_favorable:
            favoraveis += 1
            juiz_counts[proc.magistrado]["procedentes"] += 1
        elif res_lower == "improcedente":
            juiz_counts[proc.magistrado]["improcedentes"] += 1
        else:
            # Para processos recém-submetidos ("Em Analise"), pondera pela análise preditiva
            if proc.analise_preditiva and proc.analise_preditiva.probabilidade_deferimento >= 0.5:
                favoraveis += 1
                juiz_counts[proc.magistrado]["procedentes"] += 1
            else:
                juiz_counts[proc.magistrado]["improcedentes"] += 1

        tema_counts[proc.tema] += 1

    taxa_exito_global = round(favoraveis / total_processos, 3)

    analises = db.query(AnalisePreditiva).all()
    if analises:
        tempo_medio = int(
            round(sum(a.tempo_estimado_sentenca_meses for a in analises) / len(analises))
        )
    else:
        tempo_medio = 14

    decisoes_por_juiz = [
        DecisaoJuizSchema(
            juiz=juiz,
            procedentes=counts["procedentes"],
            improcedentes=counts["improcedentes"],
        )
        for juiz, counts in sorted(
            juiz_counts.items(),
            key=lambda item: (item[1]["procedentes"] + item[1]["improcedentes"]),
            reverse=True,
        )
    ]

    volume_por_tema = [
        VolumeTemaSchema(
            tema=tema,
            percentual=round((qtd / total_processos) * 100, 1),
        )
        for tema, qtd in sorted(tema_counts.items(), key=lambda item: item[1], reverse=True)
    ]

    return DashboardMetricasResponse(
        taxa_exito_global=taxa_exito_global,
        tempo_medio_tramitacao_meses=max(tempo_medio, 1),
        total_processos_analisados=total_processos,
        decisoes_por_juiz=decisoes_por_juiz,
        volume_por_tema=volume_por_tema,
    )
