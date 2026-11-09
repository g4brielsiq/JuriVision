"""
Carga Inicial Idempotente (Database Seed) — JuriVision.
Rastreabilidade:
- ARCHITECTURE.md: Seção 7 (MER/DER) e Seção 8 (Contratos de Login, Dashboard e Base de Conhecimento)
- Requisitos: RF-01, RF-04, RF-06, RF-07, RF-08, RN-01
"""
from datetime import date
import logging
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.entities import AnalisePreditiva, LogAuditoriaLGPD, Processo, Usuario

logger = logging.getLogger("jurivision.seed")


def seed_initial_data(db: Session) -> None:
    """
    Popula o banco de dados de forma idempotente com o advogado padrão e processos
    históricos higienizados (LGPD) caso a base esteja vazia.
    """
    existing_user = db.query(Usuario).filter(Usuario.email == "advogado@escritorio.com").first()
    if not existing_user:
        default_user = Usuario(
            id="usr-01",
            nome="Lucas Gabriel",
            email="advogado@escritorio.com",
            senha_hash=hash_password("senhaSegura123"),
            numero_oab="12345/AL",
        )
        db.add(default_user)
        db.flush()
        logger.info("Usuário padrão 'advogado@escritorio.com' (OAB 12345/AL) criado.")
    else:
        default_user = existing_user

    if db.query(Processo).count() > 0:
        db.commit()
        return

    seed_processes = [
        {
            "id_processo": "proc-1001",
            "numero_processo": "0019283-44.2025.8.02.0001",
            "arquivo_nome": "peticao_dano_moral_bancario.pdf",
            "origem_ingestao": "PDF",
            "tema": "Dano Moral",
            "magistrado": "Dra. Maria Silva",
            "comarca": "1ª Vara Cível de Maceió",
            "autor_anonimizado": "Felipe C. ***",
            "reu_anonimizado": "Banco Bradesco S.A.",
            "resumo_nlp": "Ação declaratória de inexistência de débito c/c indenização por danos morais decorrente de inscrição indevida em cadastro de inadimplentes.",
            "resultado_historico": "Procedente",
            "data_julgamento": date(2026, 8, 15),
            "probabilidade": 0.78,
            "prazo": 11,
            "casos": 64,
            "tese": "Dano moral in re ipsa configurado pela negativação indevida (Súmula 385 a contrario sensu do STJ).",
        },
        {
            "id_processo": "proc-1002",
            "numero_processo": "0004512-19.2025.8.02.0001",
            "arquivo_nome": "reclamatoria_trabalhista_he.pdf",
            "origem_ingestao": "PDF",
            "tema": "Direito Trabalhista",
            "magistrado": "Dr. Rafael De Amorim",
            "comarca": "2ª Vara do Trabalho de Maceió",
            "autor_anonimizado": "Emanuele V. ***",
            "reu_anonimizado": "Tech Softwares LTDA",
            "resumo_nlp": "Reclamação trabalhista pleiteando pagamento de horas extraordinárias habituais e reflexos sobre verbas rescisórias e FGTS.",
            "resultado_historico": "Acordo",
            "data_julgamento": date(2026, 9, 2),
            "probabilidade": 0.74,
            "prazo": 9,
            "casos": 48,
            "tese": "Aplicação da Súmula 338 do TST para inversão do ônus probatório relativo aos cartões de ponto.",
        },
        {
            "id_processo": "proc-1003",
            "numero_processo": "0055102-88.2025.8.02.0001",
            "arquivo_nome": "acao_obrigacao_plano_saude.pdf",
            "origem_ingestao": "PDF",
            "tema": "Plano de Saúde",
            "magistrado": "Dra. Maria Silva",
            "comarca": "3ª Vara Cível de Maceió",
            "autor_anonimizado": "José R. ***",
            "reu_anonimizado": "Operadora Unimed S.A.",
            "resumo_nlp": "Ação de obrigação de fazer com pedido de tutela de urgência para custeio de procedimento cirúrgico negado sob alegação de rol taxativo.",
            "resultado_historico": "Improcedente",
            "data_julgamento": date(2026, 7, 20),
            "probabilidade": 0.54,
            "prazo": 14,
            "casos": 39,
            "tese": "Mitigação do rol da ANS mediante comprovação científica de eficácia e inexistência de substituto terapêutico.",
        },
        {
            "id_processo": "proc-1004",
            "numero_processo": "0088210-12.2026.8.02.0001",
            "arquivo_nome": "peticao_inicial_voo.pdf",
            "origem_ingestao": "PDF",
            "tema": "Dano Moral",
            "magistrado": "Dr. Rafael De Amorim",
            "comarca": "1ª Vara Cível de Maceió",
            "autor_anonimizado": "Lucas G. ***",
            "reu_anonimizado": "Companhia Aérea Linhas Brasil S.A.",
            "resumo_nlp": "Ação de reparação civil contra transportadora aérea decorrente de cancelamento abusivo de voo internacional sem assistência emergencial ao passageiro.",
            "resultado_historico": "Procedente",
            "data_julgamento": date(2026, 10, 5),
            "probabilidade": 0.75,
            "prazo": 9,
            "casos": 42,
            "tese": "Aplicação prioritária do Código de Defesa do Consumidor e súmula sobre danos presumidos por falta de assistência.",
        },
        {
            "id_processo": "proc-1005",
            "numero_processo": "0031904-55.2025.8.02.0002",
            "arquivo_nome": "repeticao_indebito_tributario.pdf",
            "origem_ingestao": "CSV",
            "tema": "Tributário",
            "magistrado": "Dr. Carlos Souza",
            "comarca": "Vara da Fazenda Pública de Arapiraca",
            "autor_anonimizado": "Fernando G. ***",
            "reu_anonimizado": "Fazenda Pública Estadual",
            "resumo_nlp": "Ação anulatória de débito fiscal cumulada com repetição de indébito referente à cobrança de ICMS sobre demanda contratada de energia.",
            "resultado_historico": "Procedente",
            "data_julgamento": date(2026, 6, 18),
            "probabilidade": 0.65,
            "prazo": 18,
            "casos": 27,
            "tese": "Incidência do ICMS restrita à energia efetivamente consumida conforme tese firmada em repercussão geral (Súmula 391/STJ).",
        },
        {
            "id_processo": "proc-1006",
            "numero_processo": "0044129-03.2025.8.02.0001",
            "arquivo_nome": "indenizacao_extravio_bagagem.pdf",
            "origem_ingestao": "CSV",
            "tema": "Dano Moral",
            "magistrado": "Dr. Rafael De Amorim",
            "comarca": "1ª Vara Cível de Maceió",
            "autor_anonimizado": "Daniel F. ***",
            "reu_anonimizado": "Companhia Aérea Latam S.A.",
            "resumo_nlp": "Demanda indenizatória por extravio temporário de bagagem em viagem doméstica por período superior a 72 horas.",
            "resultado_historico": "Procedente",
            "data_julgamento": date(2026, 8, 29),
            "probabilidade": 0.76,
            "prazo": 10,
            "casos": 51,
            "tese": "Responsabilidade objetiva da transportadora aérea por falha no dever de guarda de bagagem.",
        },
        {
            "id_processo": "proc-1007",
            "numero_processo": "0061209-71.2025.8.02.0001",
            "arquivo_nome": "cobranca_indevida_cartao.pdf",
            "origem_ingestao": "CSV",
            "tema": "Dano Moral",
            "magistrado": "Dr. Rafael De Amorim",
            "comarca": "2ª Vara Cível de Maceió",
            "autor_anonimizado": "Pedro H. ***",
            "reu_anonimizado": "Banco Itaú Unibanco S.A.",
            "resumo_nlp": "Contestação de cobrança de seguro prestamista não contratado em fatura de cartão de crédito sem prévia anuência.",
            "resultado_historico": "Improcedente",
            "data_julgamento": date(2026, 5, 14),
            "probabilidade": 0.62,
            "prazo": 13,
            "casos": 35,
            "tese": "Vedação à venda casada de serviços bancários (art. 39, I, do CDC) e restituição em dobro de valores pagos.",
        },
        {
            "id_processo": "proc-1008",
            "numero_processo": "0072811-09.2025.8.02.0001",
            "arquivo_nome": "home_care_unimed.pdf",
            "origem_ingestao": "CSV",
            "tema": "Plano de Saúde",
            "magistrado": "Dr. Rafael De Amorim",
            "comarca": "1ª Vara Cível de Maceió",
            "autor_anonimizado": "Ygor V. ***",
            "reu_anonimizado": "Operadora Unimed Maceió S.A.",
            "resumo_nlp": "Pedido de fornecimento de internação domiciliar (home care) a paciente idoso portador de cardiopatia grave.",
            "resultado_historico": "Procedente",
            "data_julgamento": date(2026, 9, 19),
            "probabilidade": 0.81,
            "prazo": 8,
            "casos": 44,
            "tese": "Abusividade de cláusula contratual que exclui atendimento domiciliar substitutivo à internação hospitalar.",
        },
        {
            "id_processo": "proc-1009",
            "numero_processo": "0091023-41.2025.8.02.0001",
            "arquivo_nome": "vinculo_empregaticio_pj.pdf",
            "origem_ingestao": "CSV",
            "tema": "Direito Trabalhista",
            "magistrado": "Dr. Carlos Souza",
            "comarca": "1ª Vara do Trabalho de Maceió",
            "autor_anonimizado": "Gabriel D. ***",
            "reu_anonimizado": "Consultoria Digital S.A.",
            "resumo_nlp": "Ação trabalhista visando reconhecimento de vínculo empregatício sob alegação de subordinação jurídica e habitualidade.",
            "resultado_historico": "Improcedente",
            "data_julgamento": date(2026, 4, 22),
            "probabilidade": 0.48,
            "prazo": 16,
            "casos": 31,
            "tese": "Princípio da primazia da realidade sobre a forma (art. 9º da CLT) mediante comprovação dos requisitos do art. 3º.",
        },
        {
            "id_processo": "proc-1010",
            "numero_processo": "0011509-60.2026.8.02.0001",
            "arquivo_nome": "fraude_pix_responsabilidade.pdf",
            "origem_ingestao": "PDF",
            "tema": "Dano Moral",
            "magistrado": "Dra. Maria Silva",
            "comarca": "1ª Vara Cível de Maceió",
            "autor_anonimizado": "Victor S. ***",
            "reu_anonimizado": "Banco Santander Brasil S.A.",
            "resumo_nlp": "Ação de ressarcimento por fraude bancária eletrônica atípica fora do perfil de movimentação do correntista.",
            "resultado_historico": "Procedente",
            "data_julgamento": date(2026, 10, 12),
            "probabilidade": 0.71,
            "prazo": 12,
            "casos": 58,
            "tese": "Fortuito interno relativo a fraudes e delitos praticados por terceiros no âmbito de operações bancárias (Súmula 479/STJ).",
        },
    ]

    for item in seed_processes:
        proc = Processo(
            id_processo=item["id_processo"],
            usuario_id=default_user.id,
            numero_processo=item["numero_processo"],
            arquivo_nome=item["arquivo_nome"],
            origem_ingestao=item["origem_ingestao"],
            status="PROCESSADO",
            tema=item["tema"],
            magistrado=item["magistrado"],
            comarca=item["comarca"],
            autor_anonimizado=item["autor_anonimizado"],
            reu_anonimizado=item["reu_anonimizado"],
            resumo_nlp=item["resumo_nlp"],
            resultado_historico=item["resultado_historico"],
            data_julgamento=item["data_julgamento"],
        )
        db.add(proc)
        db.flush()

        pred = AnalisePreditiva(
            id_processo=proc.id_processo,
            probabilidade_deferimento=item["probabilidade"],
            margem_confianca=0.08,
            tempo_estimado_sentenca_meses=item["prazo"],
            casos_similares_encontrados=item["casos"],
            tese_recomendada=item["tese"],
            tendencia_juiz=(
                f"Magistrado(a) {item['magistrado']} possui índice histórico de "
                f"{int(item['probabilidade'] * 100)}% de decisões favoráveis neste padrão fático."
            ),
            provedor_ia_utilizado="local_heuristic",
        )
        lgpd_log = LogAuditoriaLGPD(
            id_processo=proc.id_processo,
            total_cpfs_mascarados=1,
            total_nomes_mascarados=1,
            texto_higienizado_verificado=True,
        )
        db.add(pred)
        db.add(lgpd_log)

    db.commit()
    logger.info("Base histórica inicial populada com %d processos higienizados (LGPD).", len(seed_processes))
