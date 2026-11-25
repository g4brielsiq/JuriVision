"""
Relatório de qualidade do processamento de documentos e NLP (Card #18).

Uso (na raiz do projeto):
    Windows (PowerShell):  $env:PYTHONPATH="backend"; python scripts/avaliar_nlp.py
    Linux / macOS:         PYTHONPATH=backend python scripts/avaliar_nlp.py
"""
from app.core.nlp_avaliacao import avaliar, carregar_peticoes, relatorio


def main() -> None:
    peticoes = carregar_peticoes()
    print(f"Avaliando {len(peticoes)} petições de exemplo...\n")
    print(relatorio(avaliar(peticoes)))


if __name__ == "__main__":
    main()
