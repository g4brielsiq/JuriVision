"""
Script de Carga Expandida do Acervo Jurisprudencial do TJAL — JuriVision.
Rastreabilidade:
- EAP: 1.4.2 Integração com Base de Conhecimento Jurisprudencial
- Requisitos: RF-07 (Dashboard Gerencial), RF-08 (Consulta Jurisprudencial), RN-01 a RN-04
- Popula 50 novos processos reais/sintéticos higienizados (LGPD) de comarcas de Alagoas.
"""
from datetime import date, timedelta
import logging
import os
import random
import sys

# Garante que o diretório backend esteja no PYTHONPATH
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.database import SessionLocal, engine
from app.models.entities import AnalisePreditiva, Base, LogAuditoriaLGPD, Processo, Usuario

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_tjal_expandido")

COMARCAS = [
    "1ª Vara Cível de Maceió",
    "2ª Vara Cível de Maceió",
    "3ª Vara Cível de Maceió",
    "5ª Vara Cível de Maceió",
    "10ª Vara Cível de Maceió",
    "1ª Vara Cível de Arapiraca",
    "2ª Vara Cível de Arapiraca",
    "Vara do Único Ofício de Rio Largo",
    "1ª Vara Cível de Penedo",
    "Vara da Fazenda Pública de Maceió",
    "1ª Vara do Trabalho de Maceió",
    "2ª Vara do Trabalho de Maceió",
]

MAGISTRADOS = [
    "Dr. Rafael De Amorim",
    "Dra. Maria Silva",
    "Dr. Carlos Souza",
    "Dra. Amanda Cavalcante",
    "Dr. Marcelo Lins",
]

EMPRESAS_REUS = [
    "Banco Bradesco S.A.",
    "Banco Itaú Unibanco S.A.",
    "Banco Santander Brasil S.A.",
    "Caixa Econômica Federal",
    "Companhia Aérea Linhas Brasil S.A.",
    "Companhia Aérea Latam S.A.",
    "Companhia Aérea Gol Transportes Aéreos S.A.",
    "Operadora Unimed Maceió Cooperativa Médica",
    "Operadora Hapvida Assistência Médica S.A.",
    "Equatorial Energia Alagoas S.A.",
    "Companhia de Saneamento de Alagoas - CASAL",
    "Telefônica Brasil S.A. (Vivo)",
    "Claro S.A.",
    "Magazine Luiza S.A.",
    "MercadoLivre Comércio Eletrônico LTDA",
    "Tech Softwares e Inovações LTDA",
    "Fazenda Pública do Estado de Alagoas",
    "Município de Maceió",
]

NOMES_AUTORES = [
    "Antônio Carlos M. ***",
    "Beatriz Helena S. ***",
    "Camila Duarte F. ***",
    "Diego Henrique L. ***",
    "Eduardo Pires N. ***",
    "Fabiana Ribeiro O. ***",
    "Gustavo Mendes P. ***",
    "Helena Vasconcelos Q. ***",
    "Igor Batista R. ***",
    "Juliana Medeiros T. ***",
    "Kleber Nogueira U. ***",
    "Larissa Fonseca V. ***",
    "Mateus Silveira X. ***",
    "Natália Guimarães Z. ***",
    "Otávio Barreto B. ***",
    "Patrícia Tavares C. ***",
    "Renata Albuquerque D. ***",
    "Sérgio Valença G. ***",
    "Tatiane Cardoso H. ***",
    "Vinícius Peixoto J. ***",
]

CASOS_TEMPLATES = [
    # Dano Moral / Bancário e Consumo
    {
        "tema": "Dano Moral",
        "resumo": "Ação de indenização por dano moral em virtude de negativação indevida nos órgãos de proteção ao crédito após quitação integral de fatura.",
        "tese": "Configuração de dano moral in re ipsa pela inscrição irregular em cadastros restritivos, dispensando prova de prejuízo concreto (Súmula 385/STJ).",
        "prob_base": 0.78,
    },
    {
        "tema": "Dano Moral",
        "resumo": "Demanda indenizatória decorrente de golpe do falso boleto bancário emitido via canal de atendimento telefônico fraudulento atribuído à instituição.",
        "tese": "Responsabilidade objetiva fundada na teoria do risco da atividade (art. 14 do CDC e Súmula 479 do STJ - fortuito interno).",
        "prob_base": 0.72,
    },
    {
        "tema": "Dano Moral",
        "resumo": "Ação reparatória por suspensão indevida do fornecimento de energia elétrica residencial sem prévio aviso específico e com faturas em dia.",
        "tese": "Ilegalidade do corte no fornecimento de serviço essencial sem aviso tempestivo formal e comprovação de inadimplência contemporânea.",
        "prob_base": 0.82,
    },
    {
        "tema": "Dano Moral",
        "resumo": "Cancelamento injustificado de voo doméstico Maceió-Brasília gerando perda de compromisso profissional relevante com atraso superior a 8 horas.",
        "tese": "Dever de assistência material integral ao passageiro (art. 14 do CDC e Resolução 400 da ANAC) com arbitramento de dano moral presumido.",
        "prob_base": 0.85,
    },
    {
        "tema": "Dano Moral",
        "resumo": "Desvio produtivo do consumidor em razão de sucessivas ligações de cobrança vexatória destinadas a terceiro desconhecido titular da linha.",
        "tese": "Aplicação da teoria do desvio produtivo do consumidor em razão do tempo vital desperdiçado para solucionar falha reiterada do fornecedor.",
        "prob_base": 0.68,
    },
    {
        "tema": "Dano Moral",
        "resumo": "Cobrança indevida de encargos rotativos em conta-corrente universitária isenta de tarifa de pacote de serviços essenciais.",
        "tese": "Devolução em dobro do indébito (art. 42, parágrafo único, do CDC) e reparação por dano moral ante a reiterada recusa administrativa.",
        "prob_base": 0.74,
    },
    # Direito Trabalhista
    {
        "tema": "Direito Trabalhista",
        "resumo": "Reclamação trabalhista pugnando pela rescisão indireta do contrato por ausência contínua de recolhimento dos depósitos do FGTS.",
        "tese": "Falta grave patronal capitulada no art. 483, 'd', da CLT em decorrência do descumprimento de obrigações fundamentais do pacto laboral.",
        "prob_base": 0.80,
    },
    {
        "tema": "Direito Trabalhista",
        "resumo": "Pleito de pagamento de horas extras além da 8ª diária e adicional noturno com reflexos nas verbas rescisórias para operador de suporte.",
        "tese": "Inversão do ônus da prova decorrente da não apresentação dos cartões de ponto idôneos pelo empregador (Súmula 338, I, do TST).",
        "prob_base": 0.71,
    },
    {
        "tema": "Direito Trabalhista",
        "resumo": "Ação de indenização por assédio moral no ambiente de trabalho consubstanciado em imposição de metas abusivas e humilhação perante a equipe.",
        "tese": "Violação aos direitos da personalidade do trabalhador com dever de indenizar fundado nos arts. 186 e 927 do Código Civil c/c CLT.",
        "prob_base": 0.55,
    },
    # Plano de Saúde
    {
        "tema": "Plano de Saúde",
        "resumo": "Ação de obrigação de fazer c/c tutela antecipada requerendo autorização imediata de cirurgia oncológica de urgência negada por suposta carência.",
        "tese": "Prazo máximo de 24 horas de carência em situações de urgência e emergência comprovadas por laudo médico (art. 35-C da Lei 9.656/98).",
        "prob_base": 0.88,
    },
    {
        "tema": "Plano de Saúde",
        "resumo": "Pleito para fornecimento de medicamento importado não constante originariamente do rol da ANS, mas com registro na ANVISA e laudo circunstanciado.",
        "tese": "Mitigação da taxatividade do rol da ANS comprovada a indispensabilidade terapêutica e a inexistência de alternativa eficaz na lista oficial.",
        "prob_base": 0.65,
    },
    {
        "tema": "Plano de Saúde",
        "resumo": "Questionamento de reajuste por faixa etária de 85% aplicado aos 59 anos de idade em contrato coletivo por adesão.",
        "tese": "Abusividade do reajuste desprovido de base atuarial transparente e em contrariedade ao Estatuto da Pessoa Idosa (Tema 952/STJ).",
        "prob_base": 0.76,
    },
    # Direito Tributário
    {
        "tema": "Tributário",
        "resumo": "Ação declaratória de inexistência de relação jurídico-tributária visando afastar a cobrança de diferencial de alíquota (DIFAL) sem lei complementar.",
        "tese": "Impossibilidade de exigência do DIFAL de ICMS sobre operações interestaduais sem a edição de lei complementar federal regulamentadora (Tema 1093/STF).",
        "prob_base": 0.79,
    },
    {
        "tema": "Tributário",
        "resumo": "Embargos à execução fiscal discutindo cobrança de taxa de localização e funcionamento desprovida de efetivo exercício do poder de polícia.",
        "tese": "Necessidade de demonstração da atividade fiscalizatória efetiva para legitimar a exação da taxa municipal (art. 77 do CTN).",
        "prob_base": 0.58,
    },
]


def expand_database():
    """Popula 50 novos processos adicionais no acervo local (id: proc-1011 a proc-1060)."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Busca o usuário padrão (advogado)
        user = db.query(Usuario).first()
        user_id = user.id if user else "usr-01"

        total_existentes = db.query(Processo).count()
        logger.info("Processos atualmente existentes no banco de dados: %d", total_existentes)

        novos_adicionados = 0
        base_id = 1011

        for i in range(50):
            proc_id = f"proc-{base_id + i}"

            # Verifica idempotência
            if db.query(Processo).filter(Processo.id_processo == proc_id).first():
                continue

            template = CASOS_TEMPLATES[i % len(CASOS_TEMPLATES)]
            comarca = COMARCAS[i % len(COMARCAS)]
            juiz = MAGISTRADOS[i % len(MAGISTRADOS)]
            autor = NOMES_AUTORES[i % len(NOMES_AUTORES)]
            reu = EMPRESAS_REUS[i % len(EMPRESAS_REUS)]

            # Gera número CNJ alagoano realista
            seq = random.randint(10000, 99999)
            dv = random.randint(10, 99)
            ano = random.choice([2024, 2025, 2026])
            num_proc = f"00{seq:05d}-{dv:02d}.{ano}.8.02.0001"

            # Variação sutil na probabilidade de acordo com o juiz
            prob_ajustada = template["prob_base"]
            if "Rafael" in juiz:
                prob_ajustada = min(prob_ajustada + 0.04, 0.92)
            elif "Maria" in juiz:
                prob_ajustada = min(prob_ajustada + 0.02, 0.88)
            elif "Carlos" in juiz:
                prob_ajustada = max(prob_ajustada - 0.05, 0.45)

            # Resultado histórico coerente com a probabilidade
            if prob_ajustada >= 0.70:
                resultado = random.choices(["Procedente", "Acordo", "Improcedente"], weights=[70, 20, 10])[0]
            else:
                resultado = random.choices(["Improcedente", "Procedente", "Acordo"], weights=[60, 30, 10])[0]

            prazo_meses = random.randint(7, 18)
            casos_sim = random.randint(25, 80)
            dias_atras = random.randint(15, 360)
            data_julg = date.today() - timedelta(days=dias_atras)

            novo_proc = Processo(
                id_processo=proc_id,
                usuario_id=user_id,
                numero_processo=num_proc,
                arquivo_nome=f"peticao_caso_{base_id + i}.pdf",
                origem_ingestao="CSV" if (i % 2 == 0) else "PDF",
                status="PROCESSADO",
                tema=template["tema"],
                magistrado=juiz,
                comarca=comarca,
                autor_anonimizado=autor,
                reu_anonimizado=reu,
                resumo_nlp=f"{template['resumo']} Litígio perante {comarca}.",
                resultado_historico=resultado,
                data_julgamento=data_julg,
            )
            db.add(novo_proc)
            db.flush()

            nova_pred = AnalisePreditiva(
                id_processo=proc_id,
                probabilidade_deferimento=round(prob_ajustada, 2),
                margem_confianca=0.08,
                tempo_estimado_sentenca_meses=prazo_meses,
                casos_similares_encontrados=casos_sim,
                tese_recomendada=template["tese"],
                tendencia_juiz=(
                    f"O(A) magistrado(a) {juiz} possui taxa histórica de "
                    f"{int(prob_ajustada * 100)}% de procedência em demandas de {template['tema']} no TJAL."
                ),
                provedor_ia_utilizado="local_heuristic",
            )
            db.add(nova_pred)

            novo_lgpd = LogAuditoriaLGPD(
                id_processo=proc_id,
                total_cpfs_mascarados=random.randint(1, 2),
                total_nomes_mascarados=1,
                texto_higienizado_verificado=True,
            )
            db.add(novo_lgpd)

            novos_adicionados += 1

        db.commit()
        total_final = db.query(Processo).count()
        logger.info(
            "Carga expandida concluída com sucesso! Novos adicionados: %d. Total no banco: %d.",
            novos_adicionados,
            total_final,
        )

    except Exception as exc:
        db.rollback()
        logger.error("Erro durante a carga expandida: %s", exc)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    expand_database()
