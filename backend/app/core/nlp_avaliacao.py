"""
Avaliação de qualidade do pipeline de NLP processual (Card #18 — "Validar a qualidade
dos resumos e das classificações").

Compara a saída do motor local com um conjunto de petições de exemplo anotadas à mão
(`backend/tests/fixtures/peticoes_nlp.json`) e calcula a taxa de acerto por campo.
Usado pelos testes automatizados e pelo script `scripts/avaliar_nlp.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path

from app.core.ai_gateway import LocalDeterministicFallbackAdapter
from app.core.nlp_processual import NAO_IDENTIFICADA, NAO_IDENTIFICADO, PREFIXO_SEM_CNJ
from app.schemas.contracts import ContextoHistoricoSchema, InternalAnalyzeRequest

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "peticoes_nlp.json"


@dataclass
class ResultadoCampo:
    acertos: int = 0
    total: int = 0
    erros: list[str] = field(default_factory=list)

    @property
    def taxa(self) -> float:
        return self.acertos / self.total if self.total else 1.0

    def registrar(self, ok: bool, detalhe: str) -> None:
        self.total += 1
        if ok:
            self.acertos += 1
        else:
            self.erros.append(detalhe)


def carregar_peticoes(caminho: Path = FIXTURES) -> list[dict]:
    return json.loads(caminho.read_text(encoding="utf-8"))


def avaliar(peticoes: list[dict] | None = None) -> dict[str, ResultadoCampo]:
    peticoes = peticoes if peticoes is not None else carregar_peticoes()
    adaptador = LocalDeterministicFallbackAdapter()
    campos = {
        nome: ResultadoCampo()
        for nome in (
            "tema", "numero_processo", "magistrado", "comarca", "autor",
            "caracteristicas", "valor_causa", "pedidos", "resumo", "lgpd",
        )
    }

    for p in peticoes:
        esperado = p["esperado"]
        resp = adaptador.analyze_document(
            InternalAnalyzeRequest(
                arquivo_nome=f"{p['id']}.pdf",
                texto_bruto=p["texto"],
                contexto_historico=ContextoHistoricoSchema(),
            )
        )
        meta = resp.metadados_extraidos
        car = meta.caracteristicas
        pid = p["id"]

        campos["tema"].registrar(meta.tema == esperado["tema"], f"{pid}: '{meta.tema}' != '{esperado['tema']}'")

        if esperado["numero_processo"]:
            ok = meta.numero_processo == esperado["numero_processo"]
        else:
            ok = meta.numero_processo.startswith(PREFIXO_SEM_CNJ)
        campos["numero_processo"].registrar(ok, f"{pid}: '{meta.numero_processo}' != '{esperado['numero_processo']}'")

        mag_esperado = esperado["magistrado"] or NAO_IDENTIFICADO
        campos["magistrado"].registrar(meta.magistrado == mag_esperado, f"{pid}: '{meta.magistrado}' != '{mag_esperado}'")

        com_esperada = esperado["comarca"] or NAO_IDENTIFICADA
        campos["comarca"].registrar(meta.comarca == com_esperada, f"{pid}: '{meta.comarca}' != '{com_esperada}'")

        if "autor_mascarado" in esperado:
            autor = meta.partes_anonimizadas.autor
            campos["autor"].registrar(autor == esperado["autor_mascarado"], f"{pid}: '{autor}' != '{esperado['autor_mascarado']}'")

        for nome, valor in esperado.get("caracteristicas", {}).items():
            obtido = getattr(car, nome)
            campos["caracteristicas"].registrar(obtido == valor, f"{pid}.{nome}: {obtido} != {valor}")

        campos["valor_causa"].registrar(
            car.valor_causa == esperado["valor_causa"], f"{pid}: {car.valor_causa} != {esperado['valor_causa']}"
        )
        campos["pedidos"].registrar(
            len(car.pedidos) >= esperado["pedidos_min"], f"{pid}: {len(car.pedidos)} pedido(s), mínimo {esperado['pedidos_min']}"
        )

        # Resumo: deve existir, ter tamanho razoável e citar o tema quando classificado
        resumo_ok = 40 <= len(resp.resumo_nlp) <= 900
        if esperado["tema"] != "Não classificado":
            resumo_ok = resumo_ok and esperado["tema"] in resp.resumo_nlp
        campos["resumo"].registrar(resumo_ok, f"{pid}: resumo fora do padrão ({len(resp.resumo_nlp)} caracteres)")

        # LGPD: nenhum nome completo ou CPF pode aparecer no resumo nem nos pedidos
        saida = resp.resumo_nlp + " " + " ".join(car.pedidos) + " " + (car.classe_processual or "")
        vazou = [n for n in esperado.get("nomes_proibidos", []) if n in saida]
        campos["lgpd"].registrar(not vazou, f"{pid}: dados pessoais expostos {vazou}")

    return campos


def relatorio(campos: dict[str, ResultadoCampo]) -> str:
    linhas = ["Campo               Acertos   Taxa", "-" * 38]
    for nome, r in campos.items():
        linhas.append(f"{nome:<18} {r.acertos:>3}/{r.total:<4}  {r.taxa:>6.0%}")
    erros = [e for r in campos.values() for e in r.erros]
    if erros:
        linhas += ["", "Divergências:"] + [f"  - {e}" for e in erros]
    return "\n".join(linhas)
