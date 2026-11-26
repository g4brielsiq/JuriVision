"""
Cliente Assíncrono Resiliente para a API Pública do DataJud (CNJ).
Rastreabilidade:
- ARCHITECTURE.md: Seção 6 (Diagrama de Implantação e Integração Externa) e ADR-002
- MODELING.md: RF-08 (Consulta Jurisprudencial), RNF-05 (Tolerância a Falhas)
- EAP: 1.4.2 Integração com Base de Conhecimento Jurisprudencial
"""
import asyncio
from datetime import datetime
import logging
import re
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import Processo
from app.schemas.contracts import (
    DataJudAssuntoSchema,
    DataJudMovimentoSchema,
    DataJudProcessoResponse,
)

logger = logging.getLogger("jurivision.datajud_client")

# Mapeamento do segmento e código do tribunal no número CNJ para o alias do DataJud
TRIBUNAL_ALIAS_MAP = {
    "8.02": "api_publica_tjal",  # Tribunal de Justiça de Alagoas (Foco Principal do Projeto)
    "8.26": "api_publica_tjsp",  # Tribunal de Justiça de São Paulo
    "8.19": "api_publica_tjrj",  # Tribunal de Justiça do Rio de Janeiro
    "8.13": "api_publica_tjmg",  # Tribunal de Justiça de Minas Gerais
    "8.17": "api_publica_tjpe",  # Tribunal de Justiça de Pernambuco
    "8.05": "api_publica_tjba",  # Tribunal de Justiça da Bahia
    "8.25": "api_publica_tjse",  # Tribunal de Justiça de Sergipe
    "4.05": "api_publica_trf5",  # Tribunal Regional Federal da 5ª Região (Alagoas/Nordeste)
}

SIGLA_TO_ALIAS_MAP = {
    "TJAL": "api_publica_tjal",
    "TJSP": "api_publica_tjsp",
    "TJRJ": "api_publica_tjrj",
    "TJMG": "api_publica_tjmg",
    "TJPE": "api_publica_tjpe",
    "TJBA": "api_publica_tjba",
    "TJSE": "api_publica_tjse",
    "TRF5": "api_publica_trf5",
}

NAO_INFORMADO = "Não informado pelo DataJud"

# Desfecho pelos códigos de movimento da Tabela Processual Unificada (TPU/CNJ)
DESFECHO_POR_CODIGO_TPU = {
    219: "Procedente",  # Procedência
    221: "Procedente",  # Procedência em Parte
    220: "Improcedente",  # Improcedência
    466: "Acordo",  # Homologação de Transação
}

# Números do antigo "lote de contingência" que gravava processos fictícios quando o DataJud falhava.
# Servem apenas para removê-los de acervos já afetados (todos têm dígito verificador inválido).
PREFIXOS_CNJ_CONTINGENCIA_FICTICIA = (
    "0804110-12.2026.",
    "0804225-33.2026.",
    "0804390-81.2026.",
    "0804512-09.2026.",
    "0804677-44.2026.",
)

class DataJudClient:
    """
    Cliente HTTP assíncrono para consultar metadados processuais na API Pública do DataJud.
    Quando o CNJ não responde, informa a indisponibilidade em vez de preencher dados presumidos.
    """

    @classmethod
    def resolve_alias_tribunal(cls, numero_processo: str) -> str:
        """
        Determina o alias do Elasticsearch correspondente ao tribunal com base no número CNJ.
        Formato CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO (ex: 0710802-55.2018.8.02.0001 -> 8.02 -> api_publica_tjal).
        """
        digits = re.sub(r"\D", "", numero_processo)
        if len(digits) == 20:
            # Segmento J.TR está nas posições 13 a 16 (0-indexed: [13] = J, [14:16] = TR)
            j_tr = f"{digits[13]}.{digits[14:16]}"
            if j_tr in TRIBUNAL_ALIAS_MAP:
                return TRIBUNAL_ALIAS_MAP[j_tr]

        return settings.DATAJUD_DEFAULT_ALIAS

    @classmethod
    def resolve_alias_por_sigla(cls, tribunal: str) -> str:
        """Resolve o alias do Elasticsearch da API Pública do DataJud a partir da sigla do tribunal."""
        sigla = (tribunal or "TJAL").strip().upper()
        return SIGLA_TO_ALIAS_MAP.get(sigla, settings.DATAJUD_DEFAULT_ALIAS)

    @classmethod
    def formatar_numero_cnj(cls, numero_processo: str) -> str:
        """Normaliza números CNJ de 20 dígitos contínuos para o padrão NNNNNNN-DD.AAAA.J.TR.OOOO."""
        raw = (numero_processo or "").strip()
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 20:
            return f"{digits[:7]}-{digits[7:9]}.{digits[9:13]}.{digits[13]}.{digits[14:16]}.{digits[16:]}"
        return raw

    @staticmethod
    def cnj_digito_verificador_valido(numero_processo: str) -> bool:
        """Confere o dígito verificador do número CNJ (módulo 97, Resolução CNJ nº 65/2008)."""
        digits = re.sub(r"\D", "", numero_processo or "")
        if len(digits) != 20:
            return False
        sequencial, dv, restante = digits[:7], digits[7:9], digits[9:]
        return 98 - int(f"{sequencial}{restante}00") % 97 == int(dv)

    @classmethod
    def _tribunal_do_numero(cls, numero_processo: str) -> str:
        alias = cls.resolve_alias_tribunal(numero_processo)
        return alias.replace("api_publica_", "").upper()

    @classmethod
    async def _post_search(cls, url: str, payload: dict) -> httpx.Response:
        """POST na API Pública com uma nova tentativa curta quando o CNJ responde 429 (sobrecarga)."""
        headers = {
            "Authorization": f"APIKey {settings.DATAJUD_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "JuriVision-Client/1.0",
        }
        async with httpx.AsyncClient(timeout=settings.DATAJUD_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 429:
                await asyncio.sleep(2)
                response = await client.post(url, json=payload, headers=headers)
            return response

    @staticmethod
    def _descrever_falha(status_code: Optional[int], exc: Optional[Exception] = None) -> str:
        if exc is not None:
            if isinstance(exc, httpx.TimeoutException):
                return "A API Pública do DataJud (CNJ) demorou demais para responder."
            return "Não foi possível conectar à API Pública do DataJud (CNJ)."
        if status_code in (401, 403):
            return "A API Pública do DataJud recusou a chave de acesso (DATAJUD_API_KEY desatualizada)."
        if status_code == 429:
            return "A API Pública do DataJud (CNJ) está sobrecarregada no momento."
        return f"A API Pública do DataJud (CNJ) respondeu com erro (HTTP {status_code})."

    @classmethod
    async def consultar_processo(
        cls,
        numero_processo: str,
        db: Optional[Session] = None,
        visibilidade=None,
    ) -> DataJudProcessoResponse:
        """
        Consulta o processo na API Pública do DataJud via Elasticsearch DSL.
        Se o DataJud não responder, mostra apenas o que já está no acervo visível ao usuário
        (sem completar campos com valores presumidos) ou informa que a consulta falhou.
        """
        clean_digits = re.sub(r"\D", "", numero_processo)
        alias = cls.resolve_alias_tribunal(numero_processo)
        url = f"{settings.DATAJUD_BASE_URL.rstrip('/')}/{alias}/_search"
        payload = {
            "query": {
                "match": {
                    "numeroProcesso": clean_digits if len(clean_digits) == 20 else numero_processo
                }
            }
        }

        motivo_falha: Optional[str] = None
        try:
            response = await cls._post_search(url, payload)
            if response.status_code == 200:
                hits = response.json().get("hits", {}).get("hits", [])
                if hits:
                    return cls._parse_datajud_source(hits[0].get("_source", {}), numero_processo)
                logger.info("Processo %s não encontrado no índice DataJud (%s).", numero_processo, alias)
            else:
                motivo_falha = cls._descrever_falha(response.status_code)
                logger.warning("DataJud retornou status %d para %s.", response.status_code, numero_processo)
        except Exception as exc:
            motivo_falha = cls._descrever_falha(None, exc)
            logger.warning("Falha na comunicação com a API Pública do DataJud (%s).", exc.__class__.__name__)

        return cls._buscar_no_acervo(numero_processo, db, visibilidade, motivo_falha)

    @classmethod
    def _parse_datajud_source(cls, source: dict, numero_original: str) -> DataJudProcessoResponse:
        """Mapeia os dados brutos do Elasticsearch para o schema do JuriVision, sem completar lacunas."""
        numero_proc = str(source.get("numeroProcesso") or numero_original)
        tribunal = source.get("tribunal") or cls._tribunal_do_numero(numero_proc)

        classe_info = source.get("classe") or {}
        if isinstance(classe_info, dict):
            classe_nome = classe_info.get("nome") or NAO_INFORMADO
            classe_cod = classe_info.get("codigo")
        else:
            classe_nome, classe_cod = str(classe_info), None

        assuntos_list: list[DataJudAssuntoSchema] = []
        assunto_principal_nome: Optional[str] = None
        for a in source.get("assuntos") or []:
            if not isinstance(a, dict) or not a.get("nome"):
                continue
            is_princ = bool(a.get("principal", False))
            assuntos_list.append(DataJudAssuntoSchema(codigo=a.get("codigo"), nome=a["nome"], principal=is_princ))
            if is_princ and assunto_principal_nome is None:
                assunto_principal_nome = a["nome"]
        if assunto_principal_nome is None and assuntos_list:
            assunto_principal_nome = assuntos_list[0].nome

        orgao = source.get("orgaoJulgador") or {}
        orgao_nome = (orgao.get("nome") if isinstance(orgao, dict) else str(orgao)) or NAO_INFORMADO

        movimentos = [m for m in source.get("movimentos") or [] if isinstance(m, dict)]
        movimentos.sort(key=lambda m: str(m.get("dataHora") or ""), reverse=True)
        movimentos_list = [
            DataJudMovimentoSchema(codigo=m.get("codigo"), nome=m.get("nome") or "Movimentação", data_hora=m.get("dataHora"))
            for m in movimentos[:5]
        ]

        # Desfecho: a decisão de mérito mais recente pelos códigos da Tabela Processual Unificada
        desfecho, data_desfecho = None, None
        for m in movimentos:
            codigo = m.get("codigo")
            if codigo in DESFECHO_POR_CODIGO_TPU:
                desfecho = DESFECHO_POR_CODIGO_TPU[codigo]
                data_desfecho = m.get("dataHora")
                break

        return DataJudProcessoResponse(
            numero_processo=numero_proc,
            tribunal=tribunal,
            classe=classe_nome,
            classe_codigo=classe_cod,
            assuntos=assuntos_list,
            assunto_principal=assunto_principal_nome or NAO_INFORMADO,
            orgao_julgador=orgao_nome,
            data_ajuizamento=source.get("dataAjuizamento"),
            grau=source.get("grau"),
            movimentos_recentes=movimentos_list,
            desfecho=desfecho,
            data_desfecho=data_desfecho,
            fonte="datajud_api",
            sucesso=True,
            mensagem="Metadados recuperados da API Pública do DataJud (CNJ).",
        )

    @classmethod
    def _buscar_no_acervo(
        cls,
        numero_processo: str,
        db: Optional[Session],
        visibilidade,
        motivo_falha: Optional[str],
    ) -> DataJudProcessoResponse:
        """Procura o número no acervo visível ao usuário; devolve só os campos que o acervo realmente tem."""
        numero_fmt = cls.formatar_numero_cnj(numero_processo)
        tribunal = cls._tribunal_do_numero(numero_processo)
        proc = None
        if db is not None and numero_fmt.strip():
            query = db.query(Processo).filter(
                (Processo.numero_processo == numero_processo.strip()) | (Processo.numero_processo == numero_fmt)
            )
            if visibilidade is not None:
                query = query.filter(visibilidade)
            proc = query.first()

        prefixo = f"{motivo_falha} " if motivo_falha else "Processo não localizado na API Pública do DataJud. "
        if proc:
            return DataJudProcessoResponse(
                numero_processo=proc.numero_processo,
                tribunal=tribunal,
                classe=NAO_INFORMADO,
                assuntos=[DataJudAssuntoSchema(codigo=None, nome=proc.tema, principal=True)] if proc.tema else [],
                assunto_principal=proc.tema or NAO_INFORMADO,
                orgao_julgador=proc.comarca or NAO_INFORMADO,
                data_ajuizamento=None,
                grau=None,
                movimentos_recentes=[],
                desfecho=proc.resultado_historico if proc.resultado_historico != "Em Analise" else None,
                fonte="acervo_local",
                sucesso=True,
                mensagem=prefixo + "Exibindo os dados que já constam no seu acervo.",
            )

        return DataJudProcessoResponse(
            numero_processo=numero_fmt,
            tribunal=tribunal,
            classe=NAO_INFORMADO,
            assuntos=[],
            assunto_principal=NAO_INFORMADO,
            orgao_julgador=NAO_INFORMADO,
            fonte="indisponivel" if motivo_falha else "nao_encontrado",
            sucesso=False,
            mensagem=(
                prefixo + "Tente novamente em alguns minutos."
                if motivo_falha
                else prefixo + "Confira o número digitado."
            ),
        )

    @classmethod
    async def coletar_lote_jurisprudencia(
        cls,
        tribunal: str = "TJAL",
        tema: Optional[str] = None,
        limite: int = 3,
    ) -> tuple[list[DataJudProcessoResponse], str, Optional[str]]:
        """
        Coleta na API Pública do DataJud um lote de processos que já têm decisão de mérito ou acordo
        (códigos TPU 219, 220, 221 e 466), filtrando por tribunal e opcionalmente por assunto.

        Retorna (itens, fonte, motivo_falha). Se o DataJud não responder, a lista vem vazia:
        nenhum processo é inventado para preencher o acervo.
        """
        sigla = (tribunal or "TJAL").strip().upper()
        alias = cls.resolve_alias_por_sigla(sigla)
        url = f"{settings.DATAJUD_BASE_URL.rstrip('/')}/{alias}/_search"

        filtros: list[dict] = [{"terms": {"movimentos.codigo": sorted(DESFECHO_POR_CODIGO_TPU)}}]
        consulta: dict = {"bool": {"filter": filtros}}
        if tema and tema.strip():
            consulta["bool"]["must"] = [{"match": {"assuntos.nome": tema.strip()}}]

        payload = {
            "size": max(1, min(limite, 20)),
            "query": consulta,
            "sort": [{"dataAjuizamento": {"order": "desc"}}],
        }

        try:
            response = await cls._post_search(url, payload)
        except Exception as exc:
            logger.warning("Falha na coleta em lote da API Pública do DataJud (%s).", exc.__class__.__name__)
            return [], "indisponivel", cls._descrever_falha(None, exc)

        if response.status_code != 200:
            logger.warning("Coleta em lote DataJud retornou status %d (%s).", response.status_code, alias)
            return [], "indisponivel", cls._descrever_falha(response.status_code)

        coletados: list[DataJudProcessoResponse] = []
        for hit in response.json().get("hits", {}).get("hits", [])[:limite]:
            source = hit.get("_source", {})
            parsed = cls._parse_datajud_source(source, str(source.get("numeroProcesso", "")))
            parsed.numero_processo = cls.formatar_numero_cnj(parsed.numero_processo)
            parsed.tribunal = source.get("tribunal") or sigla
            coletados.append(parsed)
        return coletados, "datajud_api", None

    @staticmethod
    def _normalizar_tema(assunto: str) -> str:
        """Agrupa o assunto TPU nos temas usados pelos filtros e pela jurimetria (sem alterar o dado de origem)."""
        texto = assunto.lower()
        grupos = (
            (("voo", "aéreo", "aereo", "transporte aéreo", "bagagem"), "Atraso de Voo"),
            (("plano de saúde", "plano de saude", "saúde suplementar", "saude suplementar", "tratamento médico"), "Plano de Saúde"),
            (("trabalh", "rescis", "horas extras", "fgts"), "Direito Trabalhista"),
            (("tribut", "fiscal", "icms", "iss", "imposto"), "Tributário"),
            (("dano moral", "consumidor", "negativa", "indébito", "indebito"), "Dano Moral"),
        )
        for termos, tema in grupos:
            if any(t in texto for t in termos):
                return tema
        return assunto[:120]

    @classmethod
    def extrair_registro_para_acervo(cls, item: DataJudProcessoResponse) -> Optional[dict]:
        """
        Converte um processo do DataJud em dados de cadastro do acervo usando apenas o que o CNJ publica.
        A API Pública não divulga partes nem magistrado: esses campos ficam como "Não informado pelo DataJud".
        Retorna None quando o número CNJ não é válido.
        """
        numero_cnj = cls.formatar_numero_cnj(item.numero_processo)
        if not re.fullmatch(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}", numero_cnj):
            return None

        assunto = (item.assunto_principal or "").strip()
        tema = cls._normalizar_tema(assunto) if assunto and assunto != NAO_INFORMADO else NAO_INFORMADO

        data_julgamento = None
        if item.desfecho and item.data_desfecho:
            try:
                data_julgamento = datetime.strptime(str(item.data_desfecho)[:10], "%Y-%m-%d").date()
            except ValueError:
                data_julgamento = None

        movimentos = "; ".join(m.nome for m in item.movimentos_recentes if m.nome)
        resumo = (
            f"Metadados públicos do DataJud ({item.tribunal}): classe '{item.classe}', "
            f"órgão julgador '{item.orgao_julgador}', assunto principal '{tema}'. "
            f"Movimentações recentes: {movimentos or 'não informadas'}."
        )

        return {
            "numero_processo": numero_cnj,
            "tema": tema,
            "magistrado": NAO_INFORMADO,
            "comarca": item.orgao_julgador or NAO_INFORMADO,
            "autor": NAO_INFORMADO,
            "reu": NAO_INFORMADO,
            "resumo": resumo,
            "resultado": item.desfecho or "Em Analise",
            "data_julgamento": data_julgamento,
        }
