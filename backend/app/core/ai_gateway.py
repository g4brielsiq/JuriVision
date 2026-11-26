"""
Fronteira de Isolamento do Módulo de Inteligência Artificial (Port & Adapter + Barreira LGPD).
Rastreabilidade:
- ARCHITECTURE.md: ADR-001 (HTTP Interno), ADR-002 (Strategy/Adapter + Fallback Local), Seção 5 e Seção 8.7
- MODELING.md: RF-02, RF-04, RF-05, RF-06, RNF-05 (Tolerância a Falhas), RNF-06 (LGPD), RNF-07 (Modularidade), RN-01 a RN-04
"""
from abc import ABC, abstractmethod
import base64
from collections import Counter
import hashlib
import io
import json
import logging
import re
from typing import Callable, Optional, Tuple
import uuid
import zlib

import httpx
from pypdf import PdfReader

from app.core.config import settings
from app.core.nlp_engine import (
    build_rag_precedents_context,
    compute_wilson_margin,
    extract_court_and_judge,
    synthesize_local_rag_tendencia,
)
from app.core.nlp_processual import (
    NAO_IDENTIFICADA,
    NAO_IDENTIFICADO,
    ClassificadorAssunto,
    ExtratorCaracteristicas,
    ExtratorInformacoesProcessuais,
    GeradorResumo,
    LimpadorTexto,
    sem_acento,
)
from app.schemas.comparacao import (
    PontoControvertido,
    RespostaComparacaoGemini,
    ResultadoComparacaoPecas,
    StatusTese,
    TipoTese,
)
from app.schemas.contracts import (
    AnalisePreditivaSchema,
    AuditoriaLGPDSchema,
    ContextoHistoricoSchema,
    InternalAnalyzeRequest,
    InternalAnalyzeResponse,
    MetadadosExtraidosSchema,
    PartesAnonimizadasSchema,
    SecoesPeticaoSchema,
)

logger = logging.getLogger("jurivision.ai_gateway")

PLACEHOLDER_VALUE_REGEX = re.compile(
    r"(?i)^(?:n[ãa]o\s+(?:informad[oa]|identificad[oa]|especificad[oa])|magistrado\s+n[ãa]o\s+especificado)\b"
)

# Expressões Regulares Auditáveis para Proteção de Dados Pessoais (LGPD - RF-04 / RN-01)
CPF_REGEX = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
RG_LABELED_REGEX = re.compile(
    r"(?i)\b(?:RG|Identidade)\s*[:nº°.-]*\s*(\d{1,2}\.?\d{3}\.?\d{3}-?[\dXx]|\d{6,10})\b"
)
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_REGEX = re.compile(
    r"(?i)(?:\+55\s*\(?\d{2}\)?\s*9?\d{4}[-\s]?\d{4}\b|\(\d{2}\)\s*9?\d{4}[-\s]?\d{4}\b"
    r"|\b(?:tel(?:efone)?|cel(?:ular)?|whatsapp|fone)\s*[:nº°.-]*\s*(?:\+55\s*)?\(?\d{2}\)?\s*9?\d{4}[-\s]?\d{4}\b"
    r"|\b\d{2}\s+9\d{4}-\d{4}\b)"
)
CEP_REGEX = re.compile(r"(?i)(?:\bCEP\s*[:nº°.-]*\s*\d{2}\.?\d{3}-\d{3}\b|(?<!\d)\b\d{5}-\d{3}\b(?!\.\d))")
DOC_EXTRA_REGEX = re.compile(
    r"(?i)\b(?:CNH|CTPS|PIS(?:/PASEP)?|PASEP|Passaporte|T[íi]tulo\s+de\s+Eleitor|Cart[ãa]o\s+(?:do\s+)?SUS|CNS)"
    r"\s*[:nº°.-]*\s*(?:[A-Z]{2})?\d(?:[\d./-]|\s(?=\d)){4,19}\d\b"
)
ADDRESS_REGEX = re.compile(
    r"(?i)(?:\b(?:residente\s+e\s+domiciliad[oa]\s+(?:na|no|à|em)|domiciliad[oa]\s+(?:na|no|à|em)|endere[çc]o\s*[:.-]+)"
    r"\s*(?:Rua|Avenida|Av\.|Travessa|Alameda|Pra[çc]a|Rodovia|Estrada|Condom[íi]nio|Loteamento)\s+[^\n\r.;\[]+"
    r"|\b(?:Rua|Avenida|Av\.|Travessa|Alameda)\s+[A-ZÀ-Ú][A-Za-zÀ-ú0-9\s]{2,45},\s*(?:n[º°.]?\s*)?\d{1,5}"
    r"(?:\s*,\s*(?:apto\.?|apartamento|bloco|casa|sala)\s*[A-Za-z0-9-]+)?)"
)
CNJ_REGEX = re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")

CORPORATE_KEYWORDS = (
    "s.a",
    "s/a",
    "ltda",
    "me",
    "epp",
    "eireli",
    "companhia",
    "cia",
    "banco",
    "unimed",
    "hapvida",
    "equatorial",
    "casal",
    "telefônica",
    "telefonica",
    "vivo",
    "claro",
    "tim",
    "magazine",
    "mercadolivre",
    "mercado livre",
    "hospital",
    "clínica",
    "clinica",
    "linhas",
    "aérea",
    "aerea",
    "transportes",
    "operadora",
    "cooperativa",
    "empresa",
    "comércio",
    "comercio",
    "serviços",
    "servicos",
    "instituição",
    "instituicao",
    "financeira",
    "seguradora",
    "construtora",
    "supermercado",
    "farmácia",
    "farmacia",
    "faculdade",
    "universidade",
    "instituto",
    "fundação",
    "fundacao",
    "associação",
    "associacao",
    "sindicato",
    "prefeitura",
    "secretaria",
    "ministério",
    "ministerio",
    "autarquia",
    "anac",
    "ans",
    "anatel",
    "aneel",
    "anvisa",
    "procon",
    "detran",
    "nubank",
    "softwares",
    "tecnologia",
    "consultoria",
    "estado",
    "município",
    "municipio",
    "união",
    "uniao",
    "fazenda",
    "inss",
    "bradesco",
    "itaú",
    "itau",
    "santander",
    "caixa",
    "latam",
    "gol",
    "azul",
)

CORPORATE_REGEX = re.compile(
    r"(?i)(?:^|[\s,./(-])(?:"
    + "|".join(re.escape(kw) for kw in CORPORATE_KEYWORDS)
    + r")(?=$|[\s,.)/-])"
)

LEGAL_AND_GEO_STOPWORDS = {
    "código",
    "codigo",
    "defesa",
    "consumidor",
    "civil",
    "processo",
    "processual",
    "penal",
    "trabalho",
    "trabalhista",
    "tributário",
    "tributario",
    "constituição",
    "constituicao",
    "federal",
    "estadual",
    "municipal",
    "súmula",
    "sumula",
    "tema",
    "artigo",
    "lei",
    "decreto",
    "resolução",
    "resolucao",
    "vara",
    "cível",
    "civel",
    "comarca",
    "tribunal",
    "justiça",
    "justica",
    "superior",
    "supremo",
    "regional",
    "turma",
    "câmara",
    "camara",
    "seção",
    "secao",
    "juizado",
    "especial",
    "maceió",
    "maceio",
    "arapiraca",
    "penedo",
    "alagoas",
    "brasil",
    "brasília",
    "brasilia",
    "dano",
    "moral",
    "material",
    "indenização",
    "indenizacao",
    "reparação",
    "reparacao",
    "obrigação",
    "obrigacao",
    "tutela",
    "urgência",
    "urgencia",
    "atraso",
    "voo",
    "plano",
    "saúde",
    "saude",
    "horas",
    "extras",
    "rescisão",
    "rescisao",
    "contrato",
    "ação",
    "acao",
    "declaratória",
    "declaratoria",
    "inexistência",
    "inexistencia",
    "débito",
    "debito",
    "procedente",
    "improcedente",
    "acordo",
    "sentença",
    "sentenca",
    "acórdão",
    "acordao",
    "decisão",
    "decisao",
    "julgamento",
    "síntese",
    "sintese",
    "factual",
    "direito",
    "juiz",
    "juíza",
    "juiza",
    "magistrado",
    "magistrada",
    "desembargador",
    "desembargadora",
    "ministro",
    "ministra",
    "relator",
    "relatora",
    "dr",
    "dra",
    "exmo",
    "exma",
    "excelentíssimo",
    "excelentissimo",
    "senhor",
    "senhora",
    "autor",
    "autora",
    "requerente",
    "reclamante",
    "réu",
    "reu",
    "ré",
    "re",
    "requerido",
    "requerida",
    "reclamado",
    "reclamada",
    "executado",
    "executada",
    "exequente",
    "paciente",
    "impetrante",
    "testemunha",
    "vítima",
    "vitima",
    "brasileiro",
    "brasileira",
    "casado",
    "casada",
    "solteiro",
    "solteira",
    "divorciado",
    "divorciada",
    "viúvo",
    "viúva",
    "residente",
    "domiciliado",
    "domiciliada",
    "portador",
    "portadora",
    "inscrito",
    "inscrita",
}

GEO_PHRASES = (
    "são paulo",
    "sao paulo",
    "rio de janeiro",
    "rio largo",
    "belo horizonte",
    "porto alegre",
    "santa catarina",
    "minas gerais",
    "mato grosso",
    "espírito santo",
    "espirito santo",
    "distrito federal",
)


class AnonimizadorLGPD:
    """
    Motor determinístico local de higienização de Dados Pessoais (PII) em conformidade com a LGPD.
    Cumpre o invariante RN-01: nenhum CPF, RG, e-mail, telefone, endereço ou nome real de pessoa
    física transpõe esta barreira.
    """

    @staticmethod
    def is_corporate_entity(name: str) -> bool:
        if not name:
            return False
        return bool(CORPORATE_REGEX.search(name))

    @classmethod
    def _clean_candidate_person_name(cls, candidate: str) -> str:
        """
        Valida e limpa candidato a nome de pessoa física capturado em prosa jurídica,
        interrompendo antes de termos jurídicos/geográficos e evitando falsos positivos.
        """
        cleaned = " ".join((candidate or "").strip(" ,.;:-").split())
        if not cleaned or cls.is_corporate_entity(cleaned):
            return ""
        lower_full = cleaned.lower()
        if any(phrase in lower_full for phrase in GEO_PHRASES):
            return ""

        prepositions = {"de", "da", "do", "das", "dos", "e"}
        raw_tokens = cleaned.split()
        kept: list[str] = []
        for tok in raw_tokens:
            low = tok.lower().strip(".,;:")
            if low in LEGAL_AND_GEO_STOPWORDS:
                break
            if low in prepositions:
                kept.append(tok)
                continue
            if not re.match(r"^[A-ZÀ-Ú][a-zà-ú'-]{1,}$", tok):
                break
            kept.append(tok)

        while kept and kept[-1].lower() in prepositions:
            kept.pop()

        significant = [t for t in kept if t.lower() not in prepositions]
        if len(significant) < 2:
            return ""

        result = " ".join(kept)
        if cls.is_corporate_entity(result):
            return ""
        return result

    @classmethod
    def _is_followed_by_corporate_suffix(cls, text: str, end_pos: int) -> bool:
        tail = text[end_pos : end_pos + 30].lstrip(" ,.-")
        return bool(re.match(r"(?i)^(?:S\.?A\.?|S/A|LTDA\.?|ME|EPP|EIRELI)\b", tail))

    @classmethod
    def mask_party_name(cls, raw_name: str) -> Tuple[str, bool]:
        """
        Anonimiza o nome de pessoa física preservando apenas o primeiro nome/iniciais + '***'.
        Se for pessoa jurídica (empresa/órgão), preserva a razão social para fins de jurimetria.
        Retorna (nome_formatado, foi_mascarado).
        """
        cleaned = " ".join(raw_name.strip().split())
        if not cleaned:
            return "Parte Anonimizada ***", True
        if cls.is_placeholder_value(cleaned):
            return cleaned, False

        # Se já estiver mascarado, mantém e contabiliza como verificado
        if "***" in cleaned or "[NOME_ANONIMIZADO]" in cleaned:
            return cleaned, True

        if cls.is_corporate_entity(cleaned):
            return cleaned, False

        # Remove CPFs ou RGs residuais caso estejam concatenados ao nome
        cleaned, _ = CPF_REGEX.subn("", cleaned)
        tokens = [t for t in re.split(r"\s+", cleaned.strip(" ,;-")) if t]
        if not tokens:
            return "Parte Anonimizada ***", True

        prepositions = {"de", "da", "do", "das", "dos", "e"}
        significant = [t for t in tokens if t.lower() not in prepositions]

        if len(significant) == 1:
            return f"{significant[0]} ***", True

        first_name = significant[0]
        second_initial = significant[1][0].upper()
        return f"{first_name} {second_initial}. ***", True

    @classmethod
    def extract_parties_from_text(cls, raw_text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extrai Autor e Réu de cabeçalhos explícitos ou de construções em prosa jurídica.
        Retorna None para a parte não encontrada (nenhum nome é inventado).
        """
        autor_match = re.search(
            r"(?i)\b(?:Autor(?:a)?|Requerente|Reclamante)\s*:\s*([^\n\r,;]{3,60})", raw_text
        )
        if autor_match:
            raw_autor = autor_match.group(1).strip()
        else:
            prose_autor = re.search(
                r"(?i:\b(?:Autor(?:a)?|Requerente|Reclamante|Impetrante|Exequente)\s+"
                r"|movid[oa]\s+por\s+|ajuizad[oa]\s+por\s+|propost[oa]\s+por\s+|promovid[oa]\s+por\s+)"
                r"([A-ZÀ-Ú][a-zà-ú]{1,25}(?:\s+(?:de|da|do|das|dos|e)\s+[A-ZÀ-Ú][a-zà-ú]{1,25}|\s+[A-ZÀ-Ú][a-zà-ú]{1,25}){1,4})",
                raw_text,
            )
            cleaned_autor = cls._clean_candidate_person_name(prose_autor.group(1)) if prose_autor else ""
            raw_autor = cleaned_autor or None

        reu_match = re.search(
            r"(?i)\b(?:R[ée]u|R[ée]|Requerid[oa]|Reclamad[oa])\s*:\s*([^\n\r,;]{3,60})", raw_text
        )
        if reu_match:
            raw_reu = reu_match.group(1).strip()
        else:
            prose_reu = re.search(
                r"(?i:\bem[ \t]+face[ \t]+de[ \t]+|\bem[ \t]+desfavor[ \t]+de[ \t]+|\bcontra[ \t]+"
                r"|\bR[ée]u[ \t]+|\bR[ée][ \t]+|\bRequerid[oa][ \t]+|\bReclamad[oa][ \t]+)"
                r"([A-ZÀ-Ú][A-Za-zÀ-ú0-9.&/-]*(?:[ \t]+(?:de|da|do|das|dos|e|[A-ZÀ-Ú][A-Za-zÀ-ú0-9.&/-]*)){1,5})",
                raw_text,
            )
            if prose_reu:
                raw_cand_reu = prose_reu.group(1).strip(" ,;:")
                corp_end = re.search(r"(?i)\b(?:S\.?A\.?|S/A|LTDA\.?|EIRELI)(?:\.|$)", raw_cand_reu)
                if corp_end:
                    candidate_reu = raw_cand_reu[: corp_end.end()].strip(" ,;:")
                else:
                    candidate_reu = raw_cand_reu.strip(" ,.;:")
                if cls.is_corporate_entity(candidate_reu) or cls._is_followed_by_corporate_suffix(
                    raw_text, prose_reu.end()
                ):
                    raw_reu = candidate_reu
                else:
                    cleaned_reu = cls._clean_candidate_person_name(candidate_reu)
                    raw_reu = cleaned_reu or None
            else:
                raw_reu = None

        return raw_autor, raw_reu

    @staticmethod
    def is_placeholder_value(value: str) -> bool:
        """Marcadores de campo vazio ("Não informado pelo DataJud", "Não identificado") não são nomes de pessoas."""
        return bool(PLACEHOLDER_VALUE_REGEX.match((value or "").strip()))

    @classmethod
    def sanitize_text(cls, raw_text: str, known_natural_names: list[str] | None = None) -> Tuple[str, int, int]:
        """
        Varre um texto jurídico bruto e substitui documentos civis (RG, CNH/CTPS/PIS, CPF),
        e-mails, telefones, CEPs, endereços e nomes de pessoas físicas (em cabeçalhos e prosa).
        Retorna: (texto_higienizado, total_identificadores_mascarados, total_nomes_mascarados)
        """
        if not raw_text:
            return "", 0, 0
        if known_natural_names:
            known_natural_names = [n for n in known_natural_names if n and not cls.is_placeholder_value(n)]

        # Documentos rotulados (RG, CNH, CTPS, PIS, CNS) antes de CPF para evitar colisão de 11 dígitos
        sanitized, rg_count = RG_LABELED_REGEX.subn("RG: [RG_ANONIMIZADO]", raw_text)
        sanitized, doc_extra_count = DOC_EXTRA_REGEX.subn("[DOC_ANONIMIZADO]", sanitized)
        sanitized, cpf_count = CPF_REGEX.subn("[CPF_ANONIMIZADO]", sanitized)
        sanitized, email_count = EMAIL_REGEX.subn("[EMAIL_ANONIMIZADO]", sanitized)
        sanitized, phone_count = PHONE_REGEX.subn("[TELEFONE_ANONIMIZADO]", sanitized)
        sanitized, cep_count = CEP_REGEX.subn("[CEP_ANONIMIZADO]", sanitized)
        sanitized, address_count = ADDRESS_REGEX.subn("[ENDERECO_ANONIMIZADO]", sanitized)

        doc_pii_count = (
            cpf_count
            + rg_count
            + doc_extra_count
            + email_count
            + phone_count
            + cep_count
            + address_count
        )

        names_masked = 0
        discovered_names: list[str] = []
        name_seq = r"([A-ZÀ-Ú][a-zà-ú]{1,25}(?:\s+(?:de|da|do|das|dos|e)\s+[A-ZÀ-Ú][a-zà-ú]{1,25}|\s+[A-ZÀ-Ú][a-zà-ú]{1,25}){1,4})"

        # 1. Papéis processuais com ou sem ":" (Autor, Autora, Réu, Requerente, Testemunha, etc.)
        role_pattern = re.compile(
            r"(?i:\b(?:Autor(?:a)?|Requerente|Reclamante|Paciente|Impetrante|Exequente|"
            r"R[ée]u|R[ée]|Requerid[oa]|Reclamad[oa]|Executad[oa]|Testemunha|V[íi]tima))\s*(?::\s*|\s+)"
            + name_seq
        )

        # 2. Locuções processuais em prosa contínua
        prose_pattern = re.compile(
            r"(?i:\b(?:movid[oa]\s+por|ajuizad[oa]\s+por|propost[oa]\s+por|promovid[oa]\s+por|"
            r"impetrad[oa]\s+por|em\s+face\s+de|em\s+desfavor\s+de|contra|prescrit[oa]\s+para|"
            r"correntista|consumidor(?:a)?|segurad[oa]))\s+"
            + name_seq
        )

        for pattern in (role_pattern, prose_pattern):
            def _replace_labeled_or_prose(match: re.Match, _src=None) -> str:
                nonlocal names_masked
                full = match.group(0)
                raw_cand = match.group(1)
                prefix = full[: len(full) - len(raw_cand)]
                if cls._is_followed_by_corporate_suffix(match.string, match.end()):
                    return full
                cleaned = cls._clean_candidate_person_name(raw_cand)
                if not cleaned:
                    return full
                discovered_names.append(cleaned)
                masked, was_masked = cls.mask_party_name(cleaned)
                if was_masked:
                    names_masked += 1
                trailing = raw_cand[len(cleaned) :]
                return f"{prefix}{masked}{trailing}"

            sanitized = pattern.sub(_replace_labeled_or_prose, sanitized)

        # 3. Qualificação civil clássica antes de vírgula (ex.: "Fulano de Tal, brasileiro, casado, inscrito no CPF...")
        qualificacao_pattern = re.compile(
            name_seq
            + r"(?=,\s*(?i:brasileir[oa]|casad[oa]|solteir[oa]|divorciad[oa]|vi[úu]v[oa]|"
            r"inscrit[oa]\s+no\s+(?:CPF|\[CPF)|portador(?:a)?\s+d[eo]\s+RG|CPF\b|RG\b|"
            r"residente\s+e\s+domiciliad[oa]|\[ENDERECO_ANONIMIZADO\]))"
        )

        def _replace_qualificacao(match: re.Match) -> str:
            nonlocal names_masked
            raw_cand = match.group(1)
            before = match.string[max(0, match.start() - 25) : match.start()]
            if re.search(r"(?i)\b(?:Dr\.?|Dra\.?|Ju[íi]z(?:a)?|Magistrad[oa]|Desembargador(?:a)?|Ministr[oa])\s*$", before):
                return match.group(0)
            if cls._is_followed_by_corporate_suffix(match.string, match.end()):
                return match.group(0)
            cleaned = cls._clean_candidate_person_name(raw_cand)
            if not cleaned:
                return match.group(0)
            discovered_names.append(cleaned)
            masked, was_masked = cls.mask_party_name(cleaned)
            if was_masked:
                names_masked += 1
            return masked

        sanitized = qualificacao_pattern.sub(_replace_qualificacao, sanitized)

        # 4. Nomes conhecidos (partes do formulário/CSV ou descobertos na etapa acima) e variações parciais
        all_known: list[str] = []
        for candidate_name in (known_natural_names or []) + discovered_names:
            clean_person = (candidate_name or "").strip()
            if (
                clean_person
                and "***" not in clean_person
                and not cls.is_corporate_entity(clean_person)
                and len(clean_person) >= 3
                and clean_person not in all_known
            ):
                all_known.append(clean_person)

        prepositions = {"de", "da", "do", "das", "dos", "e"}
        for person_name in all_known:
            masked_person, _ = cls.mask_party_name(person_name)
            full_re = re.compile(r"\b" + re.escape(person_name) + r"\b")
            sanitized, count_full = full_re.subn(masked_person, sanitized)
            if count_full:
                names_masked += count_full

            sig_tokens = [t for t in person_name.split() if t.lower() not in prepositions]
            if len(sig_tokens) >= 2:
                # Prenome composto (ex.: "João Carlos")
                first_two = f"{sig_tokens[0]} {sig_tokens[1]}"
                if first_two != person_name and len(first_two) >= 5:
                    two_re = re.compile(r"\b" + re.escape(first_two) + r"\b")
                    sanitized, count_two = two_re.subn(masked_person, sanitized)
                    names_masked += count_two

                last_name = sig_tokens[-1]
                if (
                    len(last_name) >= 5
                    and last_name.lower() not in LEGAL_AND_GEO_STOPWORDS
                    and not cls.is_corporate_entity(last_name)
                ):
                    # Menções com pronome de tratamento + sobrenome (Sr./Sra. Albuquerque)
                    title_re = re.compile(
                        r"\b(?:Sr\.?|Sra\.?|Senhor(?:a)?)\s+" + re.escape(last_name) + r"\b"
                    )
                    sanitized, count_title = title_re.subn(masked_person, sanitized)
                    names_masked += count_title

                    # Menção isolada ao sobrenome (sem título jurídico ou prenome diferente imediatamente antes)
                    if len(last_name) >= 6:
                        surname_re = re.compile(r"\b" + re.escape(last_name) + r"\b")

                        def _replace_isolated_surname(m: re.Match) -> str:
                            nonlocal names_masked
                            before = m.string[max(0, m.start() - 35) : m.start()]
                            if re.search(
                                r"(?i)\b(?:Dr\.?|Dra\.?|Ju[íi]z(?:a)?|Magistrad[oa]|Desembargador(?:a)?)\s+(?:[A-ZÀ-Ú][a-zà-ú]+\s+)*$",
                                before,
                            ):
                                return m.group(0)
                            if re.search(r"[A-ZÀ-Ú][a-zà-ú]+\s+(?:de\s+|da\s+|do\s+)?$", before):
                                return m.group(0)
                            names_masked += 1
                            return masked_person

                        sanitized = surname_re.sub(_replace_isolated_surname, sanitized)

        return sanitized, doc_pii_count, names_masked


class SegmentadorPeticao:
    """
    Segmentador determinístico de seções fundamentais de petições iniciais (Art. 319 CPC).
    Identifica e particiona o texto em:
    - Dos Fatos (narrativa fática)
    - Do Direito (fundamentação jurídica)
    - Dos Pedidos (pleitos e requerimentos finais)
    - Preliminares (questões prévias, se houver)
    - Cabeçalho (endereçamento e qualificação das partes)
    """

    PATTERNS = [
        (
            "preliminares",
            re.compile(
                r"(?i)(?:^|\n)[#*_\s]*(?:(?:[I|V|X\d]+[\.\-\)\s]+)?(?:DAS?\s+PRELIMINARES?|PRELIMINARMENTE|DAS?\s+QUEST[OÕ]ES\s+PRELIMINARES?))[#*_\s]*[:\.\-]*(?:\s*|\n)"
            ),
        ),
        (
            "dos_fatos",
            re.compile(
                r"(?i)(?:^|\n)[#*_\s]*(?:(?:[I|V|X\d]+[\.\-\)\s]+)?(?:DOS?\s+FATOS|DA\s+S[IÍ]NTESE\s+F[AÁ]TICA|BREVE\s+RELATO(?:[A-Z\s]*DOS\s+FATOS)?|DOS?\s+ACONTECIMENTOS|S[IÍ]NTESE\s+DOS\s+FATOS|DA\s+NARRATIVA\s+F[AÁ]TICA|DOS\s+FATOS\s+E\s+FUNDAMENTOS|DA\s+VERDADE\s+DOS\s+FATOS))[#*_\s]*[:\.\-]*(?:\s*|\n)"
            ),
        ),
        (
            "do_direito",
            re.compile(
                r"(?i)(?:^|\n)[#*_\s]*(?:(?:[I|V|X\d]+[\.\-\)\s]+)?(?:DO\s+DIREITO|DOS?\s+FUNDAMENTOS?\s+JUR[IÍ]DICOS?|DA\s+FUNDAMENTA[CÇ][AÃ]O\s+JUR[IÍ]DICA|DO\s+M[EÉ]RITO|DA\s+APLICA[CÇ][AÃ]O\s+DO\s+DIREITO|DAS\s+RAZ[OÕ]ES\s+DE\s+DIREITO|DO\s+DIREITO\s+E\s+DA\s+JURISPRUD[EÊ]NCIA))[#*_\s]*[:\.\-]*(?:\s*|\n)"
            ),
        ),
        (
            "dos_pedidos",
            re.compile(
                r"(?i)(?:^|\n)[#*_\s]*(?:(?:[I|V|X\d]+[\.\-\)\s]+)?(?:DOS?\s+PEDIDOS?|DOS?\s+REQUERIMENTOS|DOS?\s+PEDIDOS\s+E\s+REQUERIMENTOS?|REQUERIMENTOS\s+FINAIS|DO\s+PLEITO|DA\s+CONCLUS[AÃ]O(?:\s+E\s+PEDIDOS)?|DIANTE\s+DO\s+EXPOSTO[,\s]+REQUER|PELO\s+EXPOSTO[,\s]+REQUER|ISTO\s+POSTO[,\s]+REQUER|ANTE\s+O\s+EXPOSTO[,\s]+REQUER))[#*_\s]*[:\.\-]*(?:\s*|\n)"
            ),
        ),
    ]

    @classmethod
    def segmentar(cls, text: str) -> SecoesPeticaoSchema:
        """
        Segmenta o texto de uma petição inicial retornando um SecoesPeticaoSchema.
        Opera deterministicamente com regex formal e possui fallback heurístico inteligente para petições sem títulos formais.
        """
        if not text or not text.strip():
            return SecoesPeticaoSchema()

        # 1. Procura ocorrências de marcadores de seções estruturadas
        matches = []
        for name, pat in cls.PATTERNS:
            for m in pat.finditer(text):
                matches.append((m.start(), m.end(), name, m.group(0)))

        if matches:
            matches.sort(key=lambda x: x[0])
            cabecalho = text[: matches[0][0]].strip() or None
            sections: dict[str, str] = {
                "dos_fatos": "",
                "do_direito": "",
                "dos_pedidos": "",
                "preliminares": "",
            }
            for i, (start, end, name, heading) in enumerate(matches):
                next_start = matches[i + 1][0] if i + 1 < len(matches) else len(text)
                content = text[end:next_start].strip()
                if sections[name]:
                    sections[name] += "\n\n" + content
                else:
                    sections[name] = content

            return SecoesPeticaoSchema(
                dos_fatos=sections["dos_fatos"],
                do_direito=sections["do_direito"],
                dos_pedidos=sections["dos_pedidos"],
                preliminares=sections["preliminares"] or None,
                cabecalho=cabecalho,
            )

        # 2. Fallback heurístico para petições sem títulos formais explícitos
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        fatos_parts: list[str] = []
        direito_parts: list[str] = []
        pedidos_parts: list[str] = []
        cabecalho_parts: list[str] = []

        is_pedidos = False
        for para in paragraphs:
            para_lower = para.lower()
            if any(
                t in para_lower
                for t in (
                    "requer",
                    "pede deferimento",
                    "diante do exposto",
                    "ante o exposto",
                    "isto posto",
                    "pelo exposto",
                    "pede-se",
                    "requer-se",
                )
            ):
                is_pedidos = True

            if is_pedidos:
                pedidos_parts.append(para)
            elif any(
                legal in para_lower
                for legal in (
                    "artigo",
                    "art.",
                    "arts.",
                    "cdc",
                    "cpc",
                    "clt",
                    "código civil",
                    "código",
                    "sumula",
                    "súmula",
                    "jurisprudência",
                    "jurisprudencia",
                    "precedente",
                    "responsabilidade civil",
                    "dano moral in re ipsa",
                )
            ):
                direito_parts.append(para)
            elif (
                any(
                    head in para_lower
                    for head in (
                        "excelentíssimo",
                        "excelentissimo",
                        "vara cível",
                        "vara civel",
                        "processo:",
                        "autor:",
                        "réu:",
                        "requerente:",
                        "requerido:",
                    )
                )
                and not fatos_parts
            ):
                cabecalho_parts.append(para)
            else:
                fatos_parts.append(para)

        return SecoesPeticaoSchema(
            dos_fatos="\n\n".join(fatos_parts).strip(),
            do_direito="\n\n".join(direito_parts).strip(),
            dos_pedidos="\n\n".join(pedidos_parts).strip(),
            preliminares=None,
            cabecalho="\n\n".join(cabecalho_parts).strip() or None,
        )

    @classmethod
    def segmentar_dict(cls, text: str) -> dict[str, str]:
        """Retorna as seções segmentadas em formato de dicionário simples."""
        return cls.segmentar(text).model_dump()


class ExtratorDocumental:
    """
    Serviço determinístico local de validação de integridade e extração textual de PDFs (RF-02 / RN-04).
    Suporta PDFs padrão via `pypdf`, operadores `Tj`/`TJ` diretos, metadados `/ActualText` e streams `FlateDecode`.
    Implementa fallback de OCR resiliente para PDFs escaneados como imagem (ADR-002 / RNF-05).
    """

    @staticmethod
    def _unescape_pdf_literal(segment: str) -> str:
        return (
            segment.replace(r"\(", "(")
            .replace(r"\)", ")")
            .replace(r"\\", "\\")
            .replace(r"\n", " ")
            .replace(r"\r", " ")
            .replace(r"\t", " ")
        )

    @classmethod
    def _extract_operators_from_stream_text(cls, stream_text: str) -> list[str]:
        chunks: list[str] = []
        op_pattern = re.compile(
            r"\(([^()\\]*(?:\\.[^()\\]*)*)\)\s*Tj|\[([^\]]+)\]\s*TJ",
            re.DOTALL,
        )
        for match in op_pattern.finditer(stream_text):
            if match.group(1) is not None:
                text = cls._unescape_pdf_literal(match.group(1)).strip()
                if len(text) >= 4:
                    chunks.append(text)
            elif match.group(2) is not None:
                parts = re.findall(r"\(([^()\\]*(?:\\.[^()\\]*)*)\)", match.group(2))
                joined = "".join(cls._unescape_pdf_literal(p) for p in parts).strip()
                if len(joined) >= 4:
                    chunks.append(joined)

        if not chunks:
            for meta_pat in (
                r"/ActualText\s*\(([^()\\]*(?:\\.[^()\\]*)*)\)",
                r"/Contents\s*\(([^()\\]*(?:\\.[^()\\]*)*)\)",
            ):
                for raw_meta in re.findall(meta_pat, stream_text):
                    cleaned = cls._unescape_pdf_literal(raw_meta).strip()
                    if len(cleaned) >= 4:
                        chunks.append(cleaned)
        return chunks

    _custom_ocr_provider: Optional[Callable[[bytes], str]] = None

    @classmethod
    def register_ocr_provider(cls, provider: Optional[Callable[[bytes], str]]) -> None:
        """Permite registrar um provedor customizado de OCR (injeção de dependência / testes / microsserviço)."""
        cls._custom_ocr_provider = provider

    @classmethod
    def reset_ocr_provider(cls) -> None:
        """Restaura o provedor padrão de OCR."""
        cls._custom_ocr_provider = None

    @classmethod
    def _has_images(cls, reader: Optional[PdfReader], file_bytes: bytes) -> bool:
        """Detecta presença de objetos de imagem no PDF sem depender obrigatoriamente de Pillow."""
        if reader and reader.pages:
            for page in reader.pages:
                try:
                    resources = page.get("/Resources", {})
                    if hasattr(resources, "get"):
                        xobjs = resources.get("/XObject", {})
                        if hasattr(xobjs, "values"):
                            for xobj in xobjs.values():
                                obj = xobj.get_object() if hasattr(xobj, "get_object") else xobj
                                if getattr(obj, "get", None) and obj.get("/Subtype") == "/Image":
                                    return True
                except Exception:
                    pass
        # Verificação rápida no stream binário caso a árvore de objetos esteja corrompida ou enxuta
        return bool(re.search(rb"/Subtype\s*/Image", file_bytes))

    @classmethod
    def _is_scanned_pdf(cls, reader: Optional[PdfReader], file_bytes: bytes, digital_text: str) -> bool:
        """Identifica se o PDF é um documento escaneado/imagem (texto digital ausente/mínimo e presença de imagens)."""
        clean = (digital_text or "").strip()
        if len(clean) < 30:
            return cls._has_images(reader, file_bytes)
        return False

    @classmethod
    def _ocr_via_gemini(cls, file_bytes: bytes) -> Optional[str]:
        """
        Executa OCR multimodal via Google Gemini API (Free Tier) quando chave estiver disponível.
        Transcreve fielmente documentos escaneados e petições digitalizadas.
        """
        api_key = settings.GEMINI_API_KEY.strip()
        if not api_key or settings.AI_PROVIDER not in ("gemini", "auto"):
            return None

        prompt = (
            "Você é um sistema de OCR jurídico de alta precisão. Transcreva na íntegra todo o conteúdo "
            "textual legível presente neste documento de petição inicial escaneada/imagem, preservando títulos, "
            "seções (como 'DOS FATOS', 'DO DIREITO', 'DOS PEDIDOS'), números de processo, parágrafos e dados das partes "
            "exatamente como constam no documento original. Retorne exclusivamente o texto transcrito, sem introduções."
        )

        b64_pdf = base64.b64encode(file_bytes).decode("utf-8")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "application/pdf",
                                "data": b64_pdf,
                            }
                        },
                        {"text": prompt},
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.1},
        }

        try:
            with httpx.Client(timeout=settings.GEMINI_TIMEOUT_SECONDS) as client:
                res = client.post(url, headers={"x-goog-api-key": api_key}, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            text = parts[0].get("text", "").strip()
                            if text:
                                logger.info("OCR concluído com sucesso via Gemini Vision Multimodal.")
                                return text
        except Exception as exc:
            logger.info("Tentativa de OCR via Gemini Vision falhou ou offline (%s: %s).", exc.__class__.__name__, exc)

        return None

    @classmethod
    def _ocr_via_pytesseract(cls, file_bytes: bytes, reader: Optional[PdfReader]) -> Optional[str]:
        """
        Executa OCR local via Tesseract / Pytesseract quando a biblioteca e o binário estiverem instalados.
        """
        try:
            import pytesseract
            from PIL import Image

            if not reader or not reader.pages:
                return None

            transcribed_pages = []
            for page in reader.pages:
                try:
                    for img_file in page.images:
                        img = Image.open(io.BytesIO(img_file.data))
                        page_text = pytesseract.image_to_string(img, lang="por+eng")
                        if page_text.strip():
                            transcribed_pages.append(page_text.strip())
                except Exception:
                    pass

            if transcribed_pages:
                logger.info("OCR concluído com sucesso via Pytesseract local.")
                return "\n".join(transcribed_pages).strip()
        except (ImportError, Exception) as exc:
            logger.debug("Pytesseract local indisponível ou falhou (%s).", exc)

        return None

    @classmethod
    def _ocr_local_heuristico(cls, file_bytes: bytes, reader: Optional[PdfReader]) -> Optional[str]:
        """
        Motor local determinístico de OCR e inspeção de camadas de imagem (RNF-05 / RN-04).
        Recupera metadados textuais de digitalização (Title, Subject, Keywords), streams OCR embutidos
        e marcadores textuais de imagens em conformidade com o padrão e-SAJ/PJe.
        """
        chunks = []

        # 1. Metadados do documento PDF (padrão de scanners jurídicos que gravam metadados OCR no PDF Info)
        if reader and reader.metadata:
            meta = reader.metadata
            for attr in ("subject", "title", "author"):
                val = getattr(meta, attr, None)
                if val and isinstance(val, str) and len(val.strip()) > 10:
                    chunks.append(val.strip())

        # 2. Busca por anotações ou streams textuais de OCR / OCRText
        raw_latin = file_bytes.decode("latin-1", errors="ignore")
        ocr_streams = re.findall(r"(?i)/OCR(?:Text)?\s*\(([^()]{10,})\)", raw_latin)
        if ocr_streams:
            chunks.extend(ocr_streams)

        # 3. Strings textuais associadas a anotações de imagem (/Contents de anotações)
        annot_texts = re.findall(
            r"/Subtype\s*/(?:Text|FreeText|Highlight)[^>]*?/Contents\s*\(([^()]{10,})\)", raw_latin
        )
        if annot_texts:
            chunks.extend(annot_texts)

        if chunks:
            logger.info("Texto recuperado via extrator local heurístico de camadas OCR.")
            return "\n".join(chunks).strip()

        return None

    @classmethod
    def _executar_fallback_ocr(cls, file_bytes: bytes, reader: Optional[PdfReader] = None) -> str:
        """
        Executa a cadeia de fallback de OCR para PDFs escaneados em imagem:
        1. Provedor customizado registrado (mock/teste/extensão)
        2. Gemini Vision OCR (Google AI Studio)
        3. Pytesseract local
        4. Extrator local heurístico determinístico
        """
        # 1. Provedor customizado registrado
        if cls._custom_ocr_provider is not None:
            try:
                res = cls._custom_ocr_provider(file_bytes)
                if res and res.strip():
                    logger.info("Texto extraído com sucesso pelo provedor customizado de OCR.")
                    return res.strip()
            except Exception as exc:
                logger.warning("Falha ao invocar provedor customizado de OCR: %s", exc)

        # 2. Gemini Vision Multimodal
        gemini_text = cls._ocr_via_gemini(file_bytes)
        if gemini_text:
            return gemini_text

        # 3. Pytesseract
        tesseract_text = cls._ocr_via_pytesseract(file_bytes, reader)
        if tesseract_text:
            return tesseract_text

        # 4. Extrator Local Heurístico
        local_text = cls._ocr_local_heuristico(file_bytes, reader)
        if local_text:
            return local_text

        raise ValueError(
            "Não foi possível extrair texto legível do PDF escaneado após tentativa de OCR (FalhaOCR / Documento vazio)."
        )

    @classmethod
    def extract_text_from_pdf_bytes(cls, file_bytes: bytes) -> str:
        """
        Extrai texto de bytes de PDF com validação binária (%PDF-), extração direta de streams de texto
        e fallback automático para OCR quando o arquivo consistir em documento escaneado/imagem (RN-04 / RNF-05).
        """
        text, _ = cls.extract_text_with_page_markers(file_bytes)
        return re.sub(r"\[PÁG \d+\]\n?", "", text).strip()

    @classmethod
    def _extract_fallback_chunks(cls, file_bytes: bytes) -> list[str]:
        """Fallback para PDFs sintéticos: operadores Tj/TJ diretos e streams FlateDecode."""
        raw_latin = file_bytes.decode("latin-1", errors="ignore")
        chunks = cls._extract_operators_from_stream_text(raw_latin)
        if chunks:
            return chunks
        for stream_match in re.finditer(
            rb"stream(?:\r\n|\n)(.*?)(?:\r\n|\n)?endstream", file_bytes, flags=re.DOTALL
        ):
            raw_stream = stream_match.group(1)
            decompressed = b""
            for attempt in (raw_stream, raw_stream.rstrip(b"\r\n")):
                for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
                    try:
                        decompressed = zlib.decompress(attempt, wbits)
                        break
                    except Exception:
                        continue
                if decompressed:
                    break
            if decompressed:
                stream_str = decompressed.decode("utf-8", errors="ignore") or decompressed.decode(
                    "latin-1", errors="ignore"
                )
                chunks.extend(cls._extract_operators_from_stream_text(stream_str))
        return chunks

    @classmethod
    def extract_text_with_page_markers(cls, file_bytes: bytes) -> Tuple[str, dict[int, str]]:
        """
        Extrai texto do PDF injetando marcadores [PÁG XX] por página (e acionando fallback de OCR se escaneado).
        Retorna (texto_completo_anotado, dicionario_paginas).
        """
        if not file_bytes or len(file_bytes) < 10:
            raise ValueError("Arquivo vazio ou sem conteúdo binário válido.")

        if not file_bytes.lstrip().startswith(b"%PDF-"):
            raise ValueError("Assinatura binária inválida: o arquivo enviado não é um documento PDF (%PDF-).")

        pages_dict: dict[int, str] = {}
        reader = None
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            for idx, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    pages_dict[idx] = page_text.strip()
        except Exception:
            pass

        if not pages_dict:
            chunks = cls._extract_fallback_chunks(file_bytes)
            if chunks:
                pages_dict[1] = "\n".join(chunks).strip()

        full_text = "\n".join(pages_dict.values()).strip()

        # Se texto digital estiver vazio ou for documento escaneado em imagem, aciona o Fallback de OCR
        if not full_text or cls._is_scanned_pdf(reader, file_bytes, full_text):
            if cls._has_images(reader, file_bytes):
                logger.info("PDF escaneado em imagem identificado. Acionando Fallback de OCR (RN-04 / RNF-05)...")
                ocr_text = cls._executar_fallback_ocr(file_bytes, reader)
                pages_dict = {1: ocr_text.strip()}
                full_text = ocr_text.strip()

        if not pages_dict or not full_text:
            raise ValueError("Não foi possível extrair texto legível do PDF enviado (FalhaOCR / Documento vazio).")

        full_parts = [f"[PÁG {pnum:02d}]\n{ptext}" for pnum, ptext in pages_dict.items()]
        annotated_text = "\n\n".join(full_parts).strip()
        return annotated_text, pages_dict

    @staticmethod
    def segment_macro_sections(annotated_text: str) -> dict[str, str]:
        """
        Segmenta estruturalmente o texto da peça nos 7 eixos jurídicos fundamentais do CPC.
        """
        section_patterns = {
            "preliminares": re.compile(r"(?i)\b(?:das?\s+preliminares|da\s+preliminar|preliminarmente)\b"),
            "prejudiciais_merito": re.compile(r"(?i)\b(?:prejudicial\s+de\s+m[ée]rito|prescri[çc][ãa]o|decad[êe]ncia)\b"),
            "fatos": re.compile(r"(?i)\b(?:dos?\s+fatos|da\s+cronologia|do\s+resumo\s+f[áa]tico|s[íi]ntese\s+f[áa]tica)\b"),
            "merito": re.compile(r"(?i)\b(?:do\s+m[ée]rito|do\s+direito|fundamenta[çc][ãa]o\s+jur[íi]dica)\b"),
            "tutela_provisoria": re.compile(r"(?i)\b(?:tutela\s+de\s+urg[êe]ncia|tutela\s+antecipada|tutela\s+provis[óo]ria)\b"),
            "provas_onus": re.compile(r"(?i)\b(?:das?\s+provas|produ[çc][ãa]o\s+de\s+provas|[ôo]nus\s+da\s+prova|invers[ãa]o\s+do\s+[ôo]nus)\b"),
            "pedidos": re.compile(r"(?i)\b(?:dos?\s+pedidos|do\s+pedido|dos?\s+requerimentos|valor\s+da\s+causa)\b"),
        }
        sections: dict[str, str] = {k: "" for k in section_patterns}
        # Varredura por blocos/parágrafos
        blocks = annotated_text.split("\n\n")
        current_section = "fatos"
        for block in blocks:
            matched = False
            for sec_name, pattern in section_patterns.items():
                if pattern.search(block[:120]):
                    current_section = sec_name
                    matched = True
                    break
            sections[current_section] = (sections[current_section] + "\n\n" + block).strip()
        return sections

    @classmethod
    def segmentar_secoes(cls, text: str) -> SecoesPeticaoSchema:
        """Segmenta o texto de uma petição inicial em Dos Fatos, Do Direito e Dos Pedidos."""
        return SegmentadorPeticao.segmentar(text)

    @classmethod
    def extract_text_and_sections(cls, file_bytes: bytes) -> tuple[str, SecoesPeticaoSchema]:
        """Extrai texto (com fallback de OCR se escaneado) e segmenta as seções da petição."""
        text = cls.extract_text_from_pdf_bytes(file_bytes)
        secoes = cls.segmentar_secoes(text)
        return text, secoes


class AIGatewayPort(ABC):
    """
    Interface Abstrata (Port) para comunicação entre o Back-end Core e o Motor de Inteligência (ADR-002).
    """

    @abstractmethod
    def analyze_document(self, request: InternalAnalyzeRequest) -> InternalAnalyzeResponse:
        """Processa um documento extraindo metadados anonimizados, resumo NLP e análise preditiva."""
        raise NotImplementedError

    @abstractmethod
    def comparar_pecas(
        self,
        texto_inicial: str,
        texto_contestacao: str,
        contexto_historico: Optional[ContextoHistoricoSchema] = None,
        numero_processo: Optional[str] = None,
    ) -> ResultadoComparacaoPecas:
        """Realiza saneamento e confronto analítico bidirecional de duas peças processuais (CPC art. 357)."""
        raise NotImplementedError



class LocalDeterministicFallbackAdapter(AIGatewayPort):
    """
    Adaptador Heurístico e Estatístico Local (`local_heuristic`).
    Garante funcionamento 100% autônomo e determinístico (RNF-05 / RN-03) quando o container
    `ai_engine` está em scaffolding ou sem chave de LLM externo.
    """

    @staticmethod
    def _segmentar_e_sanitizar_secoes(raw_text: str, known_names: list[str]) -> SecoesPeticaoSchema:
        """Isola e higieniza sob a LGPD (RN-01) as seções fundamentais da petição inicial."""
        secoes_raw = SegmentadorPeticao.segmentar(raw_text)

        sanitized_fatos, _, _ = AnonimizadorLGPD.sanitize_text(
            secoes_raw.dos_fatos, known_natural_names=known_names
        )
        sanitized_direito, _, _ = AnonimizadorLGPD.sanitize_text(
            secoes_raw.do_direito, known_natural_names=known_names
        )
        sanitized_pedidos, _, _ = AnonimizadorLGPD.sanitize_text(
            secoes_raw.dos_pedidos, known_natural_names=known_names
        )
        sanitized_prelim = None
        if secoes_raw.preliminares:
            sanitized_prelim, _, _ = AnonimizadorLGPD.sanitize_text(
                secoes_raw.preliminares, known_natural_names=known_names
            )
        sanitized_cabecalho = None
        if secoes_raw.cabecalho:
            sanitized_cabecalho, _, _ = AnonimizadorLGPD.sanitize_text(
                secoes_raw.cabecalho, known_natural_names=known_names
            )

        return SecoesPeticaoSchema(
            dos_fatos=sanitized_fatos,
            do_direito=sanitized_direito,
            dos_pedidos=sanitized_pedidos,
            preliminares=sanitized_prelim,
            cabecalho=sanitized_cabecalho,
        )

    def analyze_document(self, request: InternalAnalyzeRequest) -> InternalAnalyzeResponse:
        # 0. Limpeza e normalização do texto extraído (Card #18): remove marcadores de página,
        #    cabeçalhos/rodapés repetidos e hifenização de quebra de linha.
        raw_text = LimpadorTexto.limpar(request.texto_bruto or "")
        ctx = request.contexto_historico

        # 1 a 3. Identificação das informações processuais e classificação de tema.
        #    Nada é inventado: o que não for encontrado vira "Não identificado" e é listado
        #    em `campos_nao_identificados`.
        info = ExtratorInformacoesProcessuais.extrair(raw_text, request.arquivo_nome)
        classificacao = ClassificadorAssunto.classificar(raw_text)
        numero_processo = info.numero_processo
        tema = classificacao.tema
        tese_recomendada = classificacao.tese_recomendada
        # Segunda leitura do próprio documento (prosa jurídica) para o que os rótulos não revelaram.
        magistrado_prosa, comarca_prosa = extract_court_and_judge(raw_text)
        autor_prosa, reu_prosa = AnonimizadorLGPD.extract_parties_from_text(raw_text)
        complementos = {
            "magistrado": (info.magistrado == NAO_IDENTIFICADO and magistrado_prosa, "magistrado", magistrado_prosa),
            "comarca": (info.comarca == NAO_IDENTIFICADA and comarca_prosa, "comarca", comarca_prosa),
            "autor": (not info.autor and autor_prosa, "autor", autor_prosa),
            "reu": (not info.reu and reu_prosa, "reu", reu_prosa),
        }
        for campo, (aplicar, atributo, valor) in complementos.items():
            if aplicar:
                setattr(info, atributo, valor)
                if campo in info.campos_nao_identificados:
                    info.campos_nao_identificados.remove(campo)
        magistrado = info.magistrado
        comarca = info.comarca

        # 4. Partes e Barreira Obrigatória LGPD (RN-01 / RF-04)
        nomes_conhecidos = [n for n in (info.autor, info.reu) if n]
        if info.autor:
            autor_anon, autor_masked = AnonimizadorLGPD.mask_party_name(info.autor)
        else:
            autor_anon, autor_masked = NAO_IDENTIFICADO, False
        if info.reu:
            reu_anon, reu_masked = AnonimizadorLGPD.mask_party_name(info.reu)
        else:
            reu_anon, reu_masked = NAO_IDENTIFICADO, False

        sanitized_text, cpf_rg_count, contextual_names_count = AnonimizadorLGPD.sanitize_text(
            raw_text, known_natural_names=nomes_conhecidos
        )
        total_names_masked = max(
            contextual_names_count,
            (1 if autor_masked else 0) + (1 if reu_masked else 0),
        )

        # 5. Seções higienizadas, características processuais e resumo estruturado (RF-05)
        secoes_sanitizadas = self._segmentar_e_sanitizar_secoes(raw_text, nomes_conhecidos)
        classe_higienizada = None
        if info.classe_processual:
            classe_higienizada, _, _ = AnonimizadorLGPD.sanitize_text(
                info.classe_processual, known_natural_names=nomes_conhecidos
            )
        caracteristicas = ExtratorCaracteristicas.extrair(raw_text, secoes_sanitizadas, classe_higienizada)
        resumo_nlp = GeradorResumo.gerar(
            texto_higienizado=sanitized_text,
            secoes=secoes_sanitizadas,
            classificacao=classificacao,
            caracteristicas=caracteristicas,
            autor=autor_anon if info.autor else None,
            reu=reu_anon if info.reu else None,
            comarca=comarca,
        )

        # Garantia extra pós-sumarização de que nenhum CPF/RG escapou
        resumo_nlp, extra_cpf, _ = AnonimizadorLGPD.sanitize_text(resumo_nlp)
        cpf_rg_count += extra_cpf

        # 6. Cálculo Preditivo Ponderado e Margem de Confiança Estatística de Wilson (RF-06 / RN-02)
        prob = round(min(max(ctx.taxa_favoravel_juiz, 0.15), 0.95), 2)
        casos_similares = max(int(ctx.total_casos_similares), 0)
        tempo_meses = max(int(ctx.tempo_medio_meses), 1)
        margem = (
            round(float(ctx.margem_confianca_calculada), 2)
            if ctx.margem_confianca_calculada is not None
            else compute_wilson_margin(prob, casos_similares)
        )
        tese_final = (
            ctx.tese_precedente_similar
            if (ctx.tese_precedente_similar and casos_similares >= 1)
            else tese_recomendada
        )
        tendencia_juiz = synthesize_local_rag_tendencia(
            magistrado=(
                "magistrado(a) não identificado(a) no documento"
                if magistrado == NAO_IDENTIFICADO
                else magistrado
            ),
            tema=tema,
            prob=prob,
            margem=margem,
            casos_similares=casos_similares,
            precedentes=ctx.precedentes_similares,
        )

        return InternalAnalyzeResponse(
            metadados_extraidos=MetadadosExtraidosSchema(
                numero_processo=numero_processo,
                tema=tema,
                magistrado=magistrado,
                comarca=comarca,
                partes_anonimizadas=PartesAnonimizadasSchema(
                    autor=autor_anon,
                    reu=reu_anon,
                ),
                secoes=secoes_sanitizadas,
                caracteristicas=caracteristicas,
                confianca_classificacao=classificacao.confianca,
                campos_nao_identificados=info.campos_nao_identificados,
            ),
            resumo_nlp=resumo_nlp,
            analise_preditiva=AnalisePreditivaSchema(
                probabilidade_deferimento=prob,
                margem_confianca=margem,
                tempo_estimado_sentenca_meses=tempo_meses,
                casos_similares_encontrados=casos_similares,
                tese_recomendada=tese_final,
                tendencia_juiz=tendencia_juiz,
                provedor_ia="local_heuristic",
            ),
            auditoria_lgpd=AuditoriaLGPDSchema(
                total_cpfs_mascarados=cpf_rg_count,
                total_nomes_mascarados=total_names_masked,
                texto_higienizado_verificado=True,
            ),
        )

    @staticmethod
    def _find_page_number(annotated_text: str, snippet: Optional[str]) -> Optional[int]:
        if not snippet:
            return None
        posicao = annotated_text.find(snippet)
        if posicao == -1:
            # Tolerância a variações de espaço/quebra de linha entre o trecho e o texto anotado
            palavras = [re.escape(p) for p in snippet.strip().split() if p]
            if palavras:
                m = re.search(r"\s+".join(palavras), annotated_text, flags=re.IGNORECASE)
                if m:
                    posicao = m.start()
        if posicao == -1:
            return None
        paginas = re.findall(r"(?m)^\[PÁG (\d+)\]$", annotated_text[:posicao])
        return int(paginas[-1]) if paginas else None

    @staticmethod
    def _normalizar_bloco_pagina_pdf(bloco: str) -> str:
        """
        Higieniza ruídos típicos de PDFs jurídicos (PJe/e-SAJ) dentro de uma página:
        - Remove cabeçalhos/rodapés de assinatura digital e numeração solta de página via LimpadorTexto;
        - Desfaz hifenização de quebra de linha (ex: 'indeni-\\nzação' -> 'indenização');
        - Reconstrói frases quebradas no meio da coluna do PDF (linhas sem pontuação terminal '.!?:;').
        """
        if not bloco or not bloco.strip():
            return ""

        # Preserva textos já limpos onde cada linha é um título ou uma sentença pontuada
        tem_hifen_quebra = bool(re.search(r"[A-Za-zÀ-ú]-\r?\n\s*[A-Za-zÀ-ú]", bloco))
        tem_rodape_sistema = bool(LimpadorTexto.RODAPE_SISTEMA.search(bloco))
        linhas_brutas = [l.strip() for l in bloco.splitlines() if l.strip()]
        tem_quebra_meio_frase = any(
            not l.endswith((".", "!", "?", ":", ";"))
            and not LimpadorTexto._eh_titulo(l)
            and not re.match(r"^(?:Processo|Autor(?:a)?|R[ée]u|Requerente|Requerid[oa]|Magistrad[oa])\s*:", l, re.I)
            for l in linhas_brutas[:-1]
        )

        if not (tem_hifen_quebra or tem_rodape_sistema or tem_quebra_meio_frase):
            return "\n".join(linhas_brutas)

        limpo = LimpadorTexto.limpar(bloco)
        # Reconstrói quebras de coluna de PDF em que a próxima linha começa com número, 'R$' ou nome próprio no meio da frase
        linhas = [l.strip() for l in limpo.splitlines() if l.strip()]
        reconstruidas: list[str] = []
        for linha in linhas:
            if (
                reconstruidas
                and not reconstruidas[-1].endswith((".", "!", "?", ":", ";"))
                and not LimpadorTexto._eh_titulo(reconstruidas[-1])
                and not LimpadorTexto._eh_titulo(linha)
                and not LimpadorTexto.ITEM_ENUMERADO.match(linha)
                and not re.match(r"^(?:Processo|Autor(?:a)?|R[ée]u|Requerente|Requerid[oa]|Magistrad[oa])\s*:", linha, re.I)
                and not re.match(r"^(?:Processo|Autor(?:a)?|R[ée]u|Requerente|Requerid[oa]|Magistrad[oa])\s*:", reconstruidas[-1], re.I)
            ):
                reconstruidas[-1] = f"{reconstruidas[-1]} {linha}"
            else:
                reconstruidas.append(linha)

        texto_pagina = "\n".join(reconstruidas)
        # Normaliza valores monetários ou datas partidos por espaço múltiplo
        texto_pagina = re.sub(r"R\$\s+(\d)", r"R$ \1", texto_pagina)
        return texto_pagina

    @classmethod
    def _normalizar_peca_com_paginas(cls, texto: str) -> str:
        """Aplica limpeza de ruídos de PDF preservando intactos os marcadores [PÁG XX]."""
        if not texto:
            return ""
        partes = re.split(r"(?m)^(\[PÁG \d+\])[ \t]*\r?$", texto)
        if len(partes) == 1:
            return cls._normalizar_bloco_pagina_pdf(texto)

        blocos_saida: list[str] = []
        prefixo = cls._normalizar_bloco_pagina_pdf(partes[0])
        if prefixo:
            blocos_saida.append(prefixo)

        for idx in range(1, len(partes), 2):
            marcador = partes[idx].strip()
            conteudo = partes[idx + 1] if idx + 1 < len(partes) else ""
            conteudo_limpo = cls._normalizar_bloco_pagina_pdf(conteudo)
            if conteudo_limpo:
                blocos_saida.append(f"{marcador}\n{conteudo_limpo}")
            else:
                blocos_saida.append(marcador)

        return "\n".join(blocos_saida)

    @staticmethod
    def _extrair_trechos_comparacao(texto: str) -> list[str]:
        """
        Extrai sentenças completas e autocontidas do texto normalizado (separando parágrafos
        multissentenciais em frases individuais e ignorando marcadores [PÁG XX] e títulos curtos).
        """
        sentencas: list[str] = []
        for linha in texto.splitlines():
            linha_str = linha.strip()
            if not linha_str or re.match(r"^\[PÁG \d+\]$", linha_str):
                continue
            # Divide parágrafos com múltiplas frases em sentenças individuais preservando o texto literal
            partes = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ú0-9\"'(])", linha_str)
            for p in partes:
                p_clean = p.strip()
                if p_clean:
                    sentencas.append(p_clean)
        return sentencas

    def comparar_pecas(
        self,
        texto_inicial: str,
        texto_contestacao: str,
        contexto_historico: Optional[ContextoHistoricoSchema] = None,
        numero_processo: Optional[str] = None,
    ) -> ResultadoComparacaoPecas:
        clean_init = self._normalizar_peca_com_paginas(texto_inicial or "")
        clean_cont = self._normalizar_peca_com_paginas(texto_contestacao or "")
        lower_init = clean_init.lower()
        lower_cont = clean_cont.lower()
        norm_init = sem_acento(clean_init)
        norm_cont = sem_acento(clean_cont)

        def localizar(candidatos: list[str], *termos: str) -> Optional[str]:
            # 1ª passagem: busca case-insensitive direta
            achado = next(
                (s for s in candidatos if any(termo.lower() in s.lower() for termo in termos if termo)),
                None,
            )
            if achado:
                return achado
            # 2ª passagem: busca insensível a acentos e múltiplos espaços (resiliente a OCR/PDFs sujos)
            termos_norm = [sem_acento(re.sub(r"\s+", " ", t.strip())) for t in termos if t and t.strip()]
            return next(
                (
                    s
                    for s in candidatos
                    if any(tn in sem_acento(re.sub(r"\s+", " ", s)) for tn in termos_norm)
                ),
                None,
            )

        trechos_inicial = self._extrair_trechos_comparacao(clean_init)
        trechos_defesa = self._extrair_trechos_comparacao(clean_cont)

        if not numero_processo:
            cnj_m = CNJ_REGEX.search(clean_init) or CNJ_REGEX.search(clean_cont)
            if cnj_m:
                numero_processo = cnj_m.group(0)

        teses: list[PontoControvertido] = []
        tese_counter = 1

        # 1. VARREDURA DIRETA: Fatos, Cronologia e Valores
        datas_init = re.findall(r"\b(\d{2}/\d{2}/\d{4})\b", clean_init)
        if datas_init:
            data_alvo = datas_init[0]
            trecho_autor_data = localizar(trechos_inicial, data_alvo)
            trecho_defesa_data = localizar(trechos_defesa, data_alvo, "data")
            norm_trecho_data = sem_acento(trecho_defesa_data or "")
            termos_oposicao_data = ("impugna", "diverge", "nao ocorreu", "incorret", "falso", "nega")

            if trecho_defesa_data and any(w in norm_trecho_data for w in termos_oposicao_data):
                trecho_reu_data = trecho_defesa_data
                status_data = StatusTese.DIVERGENTE
                forca_aut = "Documental Robusta - Registros de Atendimento"
                forca_reu = "Alegação Retórica Desprovida de Prova"
                impacto_data = "Requerer na réplica fixação de ponto incontroverso ou produção de prova testemunhal/documental quanto à data."
            elif data_alvo in clean_cont:
                trecho_reu_data = localizar(trechos_defesa, data_alvo)
                status_data = StatusTese.CONVERGENTE
                forca_aut = "Fato Admitido Expressamente"
                forca_reu = "Concordância Fática Expressa"
                impacto_data = "Ponto incontroverso por convergência fática expressa (art. 374, II do CPC): dispensada dilação probatória."
            else:
                trecho_reu_data = None
                status_data = StatusTese.INCONTROVERSO_POR_OMISSAO
                forca_aut = "Alegação Fática Específica na Petição Inicial"
                forca_reu = "Ausência de Impugnação Específica (Art. 341 CPC)"
                impacto_data = "Requerer na réplica a decretação da preclusão e presunção de veracidade (art. 341 do CPC)."

            teses.append(
                PontoControvertido(
                    id_tese=f"TESE-{tese_counter:02d}",
                    tipo=TipoTese.FATO_CRONOLOGIA,
                    tema="Cronologia e Data do Inadimplemento",
                    trecho_autor=trecho_autor_data,
                    trecho_reu=trecho_reu_data,
                    status=status_data,
                    forca_probatoria_autor=forca_aut,
                    forca_probatoria_reu=forca_reu,
                    fundamentacao_preditiva="Apresentação de cronologia pormenorizada com suporte documental vincula a defesa ao ônus da impugnação específica.",
                    impacto_processual=impacto_data,
                    pagina_autor=self._find_page_number(clean_init, trecho_autor_data),
                    pagina_reu=self._find_page_number(clean_cont, trecho_reu_data) if trecho_reu_data else None,
                )
            )
            tese_counter += 1

        valores_init = re.findall(r"R\$[^\S\n]*\d(?:[\d.,]*\d)?", clean_init)
        if valores_init:
            val_alvo = valores_init[0]
            val_compacto = re.sub(r"\s+", "", val_alvo)
            trecho_aut_val = localizar(trechos_inicial, val_alvo.lower(), val_compacto.lower())
            trecho_defesa_val = localizar(
                trechos_defesa,
                val_alvo.lower(), val_compacto.lower(), "valor", "excesso", "desproporcional", "exorbitante",
            )
            norm_trecho_val = sem_acento(trecho_defesa_val or "")
            termos_oposicao_val = ("excesso", "desproporcional", "impugna", "excessivo", "exorbitante", "enriquecimento sem causa")

            if trecho_defesa_val and any(w in norm_trecho_val for w in termos_oposicao_val):
                trecho_reu_val = trecho_defesa_val
                status_val = StatusTese.DIVERGENTE
                impacto_val = "Juntar comprovantes fiscais e extratos complementares para demonstrar a exata liquidez do dano."
                forca_r_val = "Alegação de Excesso de Execução"
            elif val_alvo in clean_cont or val_compacto in re.sub(r"\s+", "", clean_cont):
                trecho_reu_val = localizar(trechos_defesa, val_alvo.lower(), val_compacto.lower())
                status_val = StatusTese.CONVERGENTE
                impacto_val = "Fato incontroverso quanto ao montante: postular julgamento antecipado parcial do mérito (art. 356 CPC)."
                forca_r_val = "Reconhecimento do Pedido Parcial"
            else:
                trecho_reu_val = None
                status_val = StatusTese.INCONTROVERSO_POR_OMISSAO
                impacto_val = "Pleitear reconhecimento de veracidade sobre o valor pretendido ante a ausência de impugnação específica (art. 341 CPC)."
                forca_r_val = "Não Impugnado na Contestação"

            teses.append(
                PontoControvertido(
                    id_tese=f"TESE-{tese_counter:02d}",
                    tipo=TipoTese.FATO_CRONOLOGIA,
                    tema="Quantificação dos Danos e Valor Pleiteado",
                    trecho_autor=trecho_aut_val,
                    trecho_reu=trecho_reu_val,
                    status=status_val,
                    forca_probatoria_autor="Planilha de Cálculos e Comprovantes acostados",
                    forca_probatoria_reu=forca_r_val,
                    fundamentacao_preditiva="A impugnação genérica de valores sem apresentação de memória de cálculo desfavorável desqualifica a oposição da ré.",
                    impacto_processual=impacto_val,
                    pagina_autor=self._find_page_number(clean_init, trecho_aut_val),
                    pagina_reu=self._find_page_number(clean_cont, trecho_reu_val) if trecho_reu_val else None,
                )
            )
            tese_counter += 1

        # 2. Mérito Principal
        trecho_aut_mer = localizar(
            trechos_inicial,
            "falha", "defeito", "dano moral", "indeniza", "responsabilidade", "inadimplemento",
            "cobranca indevida", "negativacao", "cancelamento", "atraso",
        )
        trecho_reu_mer = localizar(
            trechos_defesa,
            "exercício regular", "exercicio regular", "mero dissabor",
            "inexistência", "inexistencia", "não há dano", "nao ha dano", "improcedente",
            "improcedencia", "ausencia de ato ilicito", "cobranca devida", "regularidade",
        )

        teses.append(
            PontoControvertido(
                id_tese=f"TESE-{tese_counter:02d}",
                tipo=TipoTese.MERITO,
                tema="Configuração de Falha na Prestação de Serviço e Dano Moral",
                trecho_autor=trecho_aut_mer,
                trecho_reu=trecho_reu_mer,
                status=StatusTese.DIVERGENTE,
                forca_probatoria_autor="Documental - Falha Operacional Comprovada",
                forca_probatoria_reu="Defesa de Mero Dissabor Cotidiano",
                fundamentacao_preditiva="Jurisprudência consolidada do tribunal local reconhece responsabilidade objetiva do prestador de serviços pelo vício na prestação (art. 14 do CDC).",
                impacto_processual="Reiterar em réplica a incidência da Súmula do TJAL e precedentes vinculantes favoráveis à reparação integral.",
                pagina_autor=self._find_page_number(clean_init, trecho_aut_mer),
                pagina_reu=self._find_page_number(clean_cont, trecho_reu_mer),
            )
        )
        tese_counter += 1

        # 3. Prova e Ônus
        if any(w in norm_init for w in ("inversao", "onus da prova", "art. 6", "cdc", "hipossuficien")):
            trecho_aut_onus = localizar(trechos_inicial, "inversão", "inversao", "ônus da prova", "onus da prova", "hipossufici")
            if not trecho_aut_onus:
                trecho_aut_onus = localizar(trechos_inicial, "art. 6", "cdc")
            trecho_reu_onus = localizar(
                trechos_defesa,
                "descabe", "indevida a inversão", "indevida a inversao", "art. 373",
                "não cabe inversão", "nao cabe inversao", "ausencia de hipossuficiencia",
            )
            if trecho_reu_onus:
                status_onus = StatusTese.DIVERGENTE
            else:
                trecho_reu_onus = None
                status_onus = StatusTese.INCONTROVERSO_POR_OMISSAO

            teses.append(
                PontoControvertido(
                    id_tese=f"TESE-{tese_counter:02d}",
                    tipo=TipoTese.PROVA_ONUS,
                    tema="Distribuição do Ônus Probatório e Inversão (CDC)",
                    trecho_autor=trecho_aut_onus,
                    trecho_reu=trecho_reu_onus,
                    status=status_onus,
                    forca_probatoria_autor="Vulnerabilidade Técnica e Econômica Evidente",
                    forca_probatoria_reu="Resistência Genérica ao Estatuto Consumerista" if trecho_reu_onus else "Não Impugnado na Defesa",
                    fundamentacao_preditiva="A verossimilhança das alegações somada à hipossuficiência autoriza a inversão do ônus probatório pelo juízo saneador (art. 357, III CPC).",
                    impacto_processual="Requerer expressamente ao magistrado a fixação da inversão probatória na decisão de saneamento processual.",
                    pagina_autor=self._find_page_number(clean_init, trecho_aut_onus),
                    pagina_reu=self._find_page_number(clean_cont, trecho_reu_onus) if trecho_reu_onus else None,
                )
            )
            tese_counter += 1

        # 4. VARREDURA REVERSA: Fatos Novos da Defesa (Art. 350 CPC) e Preliminares
        if any(w in norm_cont for w in ("prescricao", "decadencia")):
            trecho_reu_presc = localizar(trechos_defesa, "prescri", "decad")
            teses.append(
                PontoControvertido(
                    id_tese=f"TESE-{tese_counter:02d}",
                    tipo=TipoTese.PREJUDICIAL_MERITO,
                    tema="Prejudicial de Prescrição / Decadência",
                    trecho_autor=None,
                    trecho_reu=trecho_reu_presc,
                    status=StatusTese.FATO_NOVO_DEFESA,
                    forca_probatoria_autor="Não Arguido na Petição Inicial (Fato Inédito)",
                    forca_probatoria_reu="Alegação de Decurso de Prazo Legal (Art. 206 CC / Art. 27 CDC)",
                    fundamentacao_preditiva="Defesa indireta de mérito que desloca o contraditório para a manifestação em réplica (art. 350 do CPC).",
                    impacto_processual="Apresentar réplica comprovando causa interruptiva da prescrição ou termo inicial vinculado ao conhecimento do dano.",
                    pagina_autor=None,
                    pagina_reu=self._find_page_number(clean_cont, trecho_reu_presc),
                )
            )
            tese_counter += 1
        elif any(w in norm_cont for w in ("ilegitimidade", "incompetencia", "preliminar", "inepcia", "falta de interesse")):
            trecho_reu_prel = localizar(trechos_defesa, "ilegitimidade", "incompet", "preliminar", "inepcia", "interesse de agir")
            teses.append(
                PontoControvertido(
                    id_tese=f"TESE-{tese_counter:02d}",
                    tipo=TipoTese.PRELIMINAR,
                    tema="Preliminar de Ilegitimidade Passiva ou Vício Processual",
                    trecho_autor=None,
                    trecho_reu=trecho_reu_prel,
                    status=StatusTese.FATO_NOVO_DEFESA,
                    forca_probatoria_autor="Não Constante da Causa de Pedir Inicial",
                    forca_probatoria_reu="Preliminar de Defesa (Art. 337 do CPC)",
                    fundamentacao_preditiva="Pertinência subjetiva da demanda amparada pela teoria da asserção e cadeia de fornecimento solidária (art. 7º, § único, CDC).",
                    impacto_processual="Requerer a rejeição liminar da preliminar com base na responsabilidade solidária da cadeia consumerista.",
                    pagina_autor=None,
                    pagina_reu=self._find_page_number(clean_cont, trecho_reu_prel),
                )
            )
            tese_counter += 1
        elif any(w in norm_cont for w in ("culpa exclusiva", "fato de terceiro", "forca maior", "caso fortuito", "quitacao", "pagamento")):
            trecho_reu_fn = localizar(
                trechos_defesa, "culpa exclusiva", "terceiro", "força maior", "forca maior",
                "fortuito", "quitação", "quitacao", "pagamento",
            )
            teses.append(
                PontoControvertido(
                    id_tese=f"TESE-{tese_counter:02d}",
                    tipo=TipoTese.MERITO,
                    tema="Fato Impeditivo / Modificativo da Obrigação (Art. 350 CPC)",
                    trecho_autor=None,
                    trecho_reu=trecho_reu_fn,
                    status=StatusTese.FATO_NOVO_DEFESA,
                    forca_probatoria_autor="Inexistência de Prévia Oposição na Inicial",
                    forca_probatoria_reu="Alegação de Excludente de Ilicitude",
                    fundamentacao_preditiva="Ônus probatório integralmente carreado à ré nos termos do art. 373, II, do CPC, demandando dilação probatória estrita.",
                    impacto_processual="Impugnar o fato extintivo/modificativo em réplica por falta de lastro documental idôneo.",
                    pagina_autor=None,
                    pagina_reu=self._find_page_number(clean_cont, trecho_reu_fn),
                )
            )
            tese_counter += 1

        total_teses = len(teses)
        total_conv = sum(1 for t in teses if t.status == StatusTese.CONVERGENTE)
        total_div = sum(1 for t in teses if t.status == StatusTese.DIVERGENTE)
        total_omiss = sum(1 for t in teses if t.status == StatusTese.INCONTROVERSO_POR_OMISSAO)
        total_fn = sum(1 for t in teses if t.status == StatusTese.FATO_NOVO_DEFESA)

        resumo_geral = (
            f"Confronto analítico de saneamento processual (art. 357 do CPC): identificadas {total_teses} teses fundamentais, "
            f"com {total_conv} convergência(s), {total_div} divergência(s), "
            f"{total_omiss} fato(s) incontroverso(s) por omissão e {total_fn} fato(s) novo(s) da defesa."
        )

        return ResultadoComparacaoPecas(
            id_comparacao=f"comp-{uuid.uuid4().hex[:8]}",
            numero_processo=numero_processo,
            resumo_controvertido_geral=resumo_geral,
            total_teses=total_teses,
            total_convergencias=total_conv,
            total_divergencias=total_div,
            total_omissoes=total_omiss,
            total_fatos_novos_defesa=total_fn,
            teses=teses,
            texto_higienizado_autor=clean_init,
            texto_higienizado_reu=clean_cont,
        )



class GeminiAIAdapter(AIGatewayPort):
    """
    Adaptador RAG Jurídico para a API do Google Gemini (Google AI Studio - Free Tier).
    Rastreabilidade:
    - ADR-002: Adapter pluggável com barreira LGPD obrigatória pré-chamada e Cache SHA-256.
    - Termos do Free Tier: Tráfego executado exclusivamente sobre texto higienizado (Art. 12 da LGPD).
    """

    _rag_cache: dict[str, dict] = {}
    _MAX_CACHE_SIZE: int = 256

    def __init__(self) -> None:
        self._fallback = LocalDeterministicFallbackAdapter()

    @classmethod
    def clear_cache(cls) -> None:
        """Limpa o cache em memória SHA-256 de respostas do Gemini."""
        cls._rag_cache.clear()

    @staticmethod
    def _apply_rag_payload(
        base_resp: InternalAnalyzeResponse,
        payload: dict,
    ) -> InternalAnalyzeResponse:
        base_resp.resumo_nlp = payload["resumo_nlp"]
        base_resp.analise_preditiva.probabilidade_deferimento = payload["prob"]
        base_resp.analise_preditiva.tese_recomendada = payload["tese_recomendada"]
        base_resp.analise_preditiva.tendencia_juiz = payload["tendencia_juiz"]
        base_resp.analise_preditiva.provedor_ia = payload["provedor_ia"]
        base_resp.auditoria_lgpd.total_cpfs_mascarados += payload["extra_cpf"]
        return base_resp

    def analyze_document(self, request: InternalAnalyzeRequest) -> InternalAnalyzeResponse:
        api_key = settings.GEMINI_API_KEY.strip()
        if not api_key:
            return self._fallback.analyze_document(request)

        # 1. Obter o baseline determinístico local + contexto RAG real do acervo
        base_resp = self._fallback.analyze_document(request)
        sanitized_text, _, _ = AnonimizadorLGPD.sanitize_text(LimpadorTexto.limpar(request.texto_bruto or ""))
        rag_block_raw = build_rag_precedents_context(
            request.contexto_historico,
            base_resp.metadados_extraidos.tema,
            base_resp.metadados_extraidos.magistrado,
            base_resp.metadados_extraidos.comarca,
        )
        rag_block, _, _ = AnonimizadorLGPD.sanitize_text(rag_block_raw)

        # 2. Verificar Cache SHA-256 (texto higienizado + modelo + contexto RAG de precedentes)
        cache_key = hashlib.sha256(
            f"{settings.GEMINI_MODEL}|{sanitized_text[:4000]}|{rag_block}".encode("utf-8")
        ).hexdigest()
        cached = self._rag_cache.get(cache_key)
        if cached is not None:
            return self._apply_rag_payload(base_resp, cached)

        # 3. Montar prompt estruturado de RAG Jurídico sobre texto desidentificado, segmentado por seções
        secoes_gemini = SegmentadorPeticao.segmentar(sanitized_text)
        fatos_prompt = secoes_gemini.dos_fatos[:2000] if secoes_gemini.dos_fatos else sanitized_text[:2000]
        prompt = (
            "Você é um perito jurimétrico especialista em jurisprudência brasileira (TJAL / Tribunais Estaduais).\n"
            "Analise o teor estruturado da petição abaixo (dados pessoais já desidentificados sob a LGPD) "
            "cruzando-o obrigatoriamente com os precedentes similares e métricas estatísticas recuperadas do acervo:\n\n"
            f"--- SEÇÃO: DOS FATOS ---\n{fatos_prompt}\n\n"
            f"--- SEÇÃO: DO DIREITO ---\n{secoes_gemini.do_direito[:1500]}\n\n"
            f"--- SEÇÃO: DOS PEDIDOS ---\n{secoes_gemini.dos_pedidos[:1000]}\n\n"
            f"--- CONTEXTO JURIMÉTRICO E PRECEDENTES SIMILARES DO ACERVO (RAG) ---\n{rag_block}\n"
            "--- FIM DO CONTEXTO RAG ---\n\n"
            "Com base nas teses, pedidos e precedentes reais acima, responda EXCLUSIVAMENTE em formato JSON com as chaves:\n"
            "- resumo_nlp: síntese concisa da causa de pedir e pedidos em até 3 parágrafos objetivos.\n"
            "- tese_recomendada: fundamento legal, súmulas e precedentes consolidados mais aderentes ao caso.\n"
            "- probabilidade_ajustada: float entre 0.15 e 0.95 calibrado pelas evidências do caso e histórico do acervo.\n"
            "- tendencia_juiz: síntese analítica citando o histórico de julgamento e aderência aos precedentes similares."
        )

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        try:
            with httpx.Client(timeout=settings.GEMINI_TIMEOUT_SECONDS) as client:
                res = client.post(url, headers={"x-goog-api-key": api_key}, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            raw_reply = parts[0].get("text", "").strip()
                            if raw_reply.startswith("```"):
                                raw_reply = re.sub(r"^```(?:json)?\s*", "", raw_reply)
                                raw_reply = re.sub(r"\s*```$", "", raw_reply)
                            parsed_json = json.loads(raw_reply)
                            clean_resumo, extra_cpf_resumo, _ = AnonimizadorLGPD.sanitize_text(
                                parsed_json.get("resumo_nlp", base_resp.resumo_nlp)
                            )
                            clean_tese, extra_cpf_tese, _ = AnonimizadorLGPD.sanitize_text(
                                parsed_json.get("tese_recomendada", base_resp.analise_preditiva.tese_recomendada)
                            )
                            clean_tendencia, extra_cpf_tend, _ = AnonimizadorLGPD.sanitize_text(
                                parsed_json.get("tendencia_juiz", base_resp.analise_preditiva.tendencia_juiz)
                            )
                            prob = float(
                                parsed_json.get(
                                    "probabilidade_ajustada",
                                    base_resp.analise_preditiva.probabilidade_deferimento,
                                )
                            )
                            prob = round(max(min(prob, 0.95), 0.15), 2)
                            extra_cpf = extra_cpf_resumo + extra_cpf_tese + extra_cpf_tend

                            cached_entry = {
                                "resumo_nlp": clean_resumo,
                                "prob": prob,
                                "tese_recomendada": clean_tese,
                                "tendencia_juiz": clean_tendencia,
                                "provedor_ia": f"gemini ({settings.GEMINI_MODEL})",
                                "extra_cpf": extra_cpf,
                            }
                            if len(self._rag_cache) >= self._MAX_CACHE_SIZE:
                                oldest_key = next(iter(self._rag_cache))
                                self._rag_cache.pop(oldest_key, None)
                            self._rag_cache[cache_key] = cached_entry

                            return self._apply_rag_payload(base_resp, cached_entry)

                logger.warning(
                    "Gemini API retornou status %d. Acionando fallback determinístico local.",
                    res.status_code,
                )
        except Exception as exc:
            logger.info(
                "Chamada ao Gemini API não concluída (%s). Acionando fallback determinístico local (ADR-002).",
                exc.__class__.__name__,
            )

        return base_resp

    FALLBACK_COMPARADOR_MODELS = (
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
    )

    def comparar_pecas(
        self,
        texto_inicial: str,
        texto_contestacao: str,
        contexto_historico: Optional[ContextoHistoricoSchema] = None,
        numero_processo: Optional[str] = None,
    ) -> ResultadoComparacaoPecas:
        api_key = settings.GEMINI_API_KEY.strip()
        if not api_key:
            return self._fallback.comparar_pecas(texto_inicial, texto_contestacao, contexto_historico, numero_processo)

        norm_init = LocalDeterministicFallbackAdapter._normalizar_peca_com_paginas(texto_inicial or "")
        norm_cont = LocalDeterministicFallbackAdapter._normalizar_peca_com_paginas(texto_contestacao or "")
        sanitized_init, _, _ = AnonimizadorLGPD.sanitize_text(norm_init)
        sanitized_cont, _, _ = AnonimizadorLGPD.sanitize_text(norm_cont)

        prompt = (
            "Você é um Juiz de Direito especialista em Direito Processual Civil atuando na fase de Saneamento e Organização do Processo (Art. 357 do CPC).\n"
            "Realize o confronto analítico bidirecional entre a PETIÇÃO INICIAL e a CONTESTAÇÃO a seguir (ambas devidamente anonimizadas sob a LGPD).\n\n"
            f"=== INÍCIO PETIÇÃO INICIAL ANONIMIZADA ===\n{sanitized_init[:5000]}\n=== FIM PETIÇÃO INICIAL ===\n\n"
            f"=== INÍCIO CONTESTAÇÃO ANONIMIZADA ===\n{sanitized_cont[:5000]}\n=== FIM CONTESTAÇÃO ===\n\n"
            "Diretrizes Obrigatórias:\n"
            "1. Varredura Direta (Autor -> Réu): Identifique convergências, divergências e fatos incontroversos por ausência de impugnação específica (Art. 341 CPC).\n"
            "2. Varredura Reversa (Réu -> Autor): Identifique preliminares e fatos novos impeditivos/modificativos/extintivos da defesa sem correspondência prévia (Art. 350 CPC).\n"
            "3. Enquadre cada tese nos 7 eixos do TipoTese (preliminar, prejudicial_merito, fato_ou_valor, merito, tutela_provisoria, prova_e_onus, pedido_e_valor_causa) e nos 4 status do StatusTese (convergente, divergente, fato_incontroverso_por_omissao, fato_novo_ou_extintivo_reu).\n"
            "4. Extraia citações literais exatas e preencha pagina_autor e pagina_reu com base nas marcações [PÁG XX]. Se uma peça não trouxer trecho correspondente, deixe a citação e a página dessa peça como null.\n"
            "5. Gere impacto_processual objetivo para o advogado em réplica e sintetize o litígio, "
            "evitando previsões de êxito. Siga o schema JSON da resposta."
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": RespostaComparacaoGemini.model_json_schema(),
            },
        }

        modelos_candidatos = list(dict.fromkeys([settings.GEMINI_MODEL, *self.FALLBACK_COMPARADOR_MODELS]))

        try:
            with httpx.Client(timeout=settings.GEMINI_TIMEOUT_SECONDS) as client:
                for modelo in modelos_candidatos:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
                    res = client.post(url, headers={"x-goog-api-key": api_key}, json=payload)
                    if res.is_success:
                        data = res.json()
                        for candidate in data.get("candidates", []):
                            parts = candidate.get("content", {}).get("parts", [])
                            resposta = "".join(part.get("text", "") for part in parts if not part.get("thought")).strip()
                            if not resposta:
                                continue
                            resposta = re.sub(r"^```(?:json)?\s*|\s*```$", "", resposta)
                            comparacao = RespostaComparacaoGemini.model_validate_json(resposta)
                            contagem = Counter(tese.status for tese in comparacao.teses)
                            cnj = CNJ_REGEX.search(sanitized_init) or CNJ_REGEX.search(sanitized_cont)
                            return ResultadoComparacaoPecas(
                                id_comparacao=f"comp-{uuid.uuid4().hex[:8]}",
                                numero_processo=numero_processo or (cnj.group(0) if cnj else None),
                                resumo_controvertido_geral=comparacao.resumo_controvertido_geral,
                                total_teses=len(comparacao.teses),
                                total_convergencias=contagem[StatusTese.CONVERGENTE],
                                total_divergencias=contagem[StatusTese.DIVERGENTE],
                                total_omissoes=contagem[StatusTese.INCONTROVERSO_POR_OMISSAO],
                                total_fatos_novos_defesa=contagem[StatusTese.FATO_NOVO_DEFESA],
                                teses=[
                                    PontoControvertido(
                                        **tese.model_dump(),
                                        id_tese=f"TESE-{indice:02d}",
                                        fundamentacao_preditiva="",
                                    )
                                    for indice, tese in enumerate(comparacao.teses, start=1)
                                ],
                                motor_analise="gemini",
                                texto_higienizado_autor=sanitized_init,
                                texto_higienizado_reu=sanitized_cont,
                            )
                        logger.warning("Modelo Gemini (%s) retornou comparação sem texto.", modelo)
                    elif res.status_code in (429, 500, 502, 503, 504):
                        logger.warning(
                            "Modelo Gemini (%s) retornou HTTP %d (indisponível/sobrecarregado). Tentando próximo modelo...",
                            modelo,
                            res.status_code,
                        )
                        continue
                    else:
                        logger.warning("Gemini retornou HTTP %d no comparador. Acionando análise local.", res.status_code)
                        break
        except Exception as exc:
            logger.warning("Comparação com Gemini não concluída (%s). Acionando análise local.", type(exc).__name__)

        return self._fallback.comparar_pecas(texto_inicial, texto_contestacao, contexto_historico, numero_processo)


class ResilientAIGateway(AIGatewayPort):
    """
    Gateway principal da camada Back-end para os provedores de IA (ADR-001 e ADR-002).
    - Se GEMINI_API_KEY estiver configurada e AI_PROVIDER for gemini ou auto, utiliza Gemini RAG.
    - Se AI_PROVIDER == 'external', tenta comunicação HTTP com o microsserviço ai_engine (:8001).
    - Em caso de timeout, offline ou erro, executa LocalDeterministicFallbackAdapter (RNF-05).
    """

    def __init__(self) -> None:
        self._fallback = LocalDeterministicFallbackAdapter()
        self._gemini = GeminiAIAdapter()

    def analyze_document(self, request: InternalAnalyzeRequest) -> InternalAnalyzeResponse:
        # 1. Se GEMINI_API_KEY estiver configurada e AI_PROVIDER for gemini ou auto, utiliza Gemini RAG
        if settings.GEMINI_API_KEY.strip() and settings.AI_PROVIDER in ("gemini", "auto"):
            return self._gemini.analyze_document(request)

        # 2. Se AI_PROVIDER for external, tenta comunicação HTTP interna com ai_engine
        if settings.AI_PROVIDER == "external":
            endpoint = f"{settings.AI_ENGINE_URL.rstrip('/')}/internal/v1/analyze"
            try:
                with httpx.Client(timeout=settings.AI_ENGINE_TIMEOUT_SECONDS) as client:
                    response = client.post(endpoint, json=request.model_dump())
                    if response.status_code == 200:
                        parsed = InternalAnalyzeResponse.model_validate(response.json())
                        clean_resumo, extra_cpfs_r, _ = AnonimizadorLGPD.sanitize_text(parsed.resumo_nlp)
                        clean_tese, extra_cpfs_t, _ = AnonimizadorLGPD.sanitize_text(
                            parsed.analise_preditiva.tese_recomendada
                        )
                        clean_tendencia, extra_cpfs_td, _ = AnonimizadorLGPD.sanitize_text(
                            parsed.analise_preditiva.tendencia_juiz
                        )
                        parsed.resumo_nlp = clean_resumo
                        parsed.analise_preditiva.tese_recomendada = clean_tese
                        parsed.analise_preditiva.tendencia_juiz = clean_tendencia
                        parsed.auditoria_lgpd.total_cpfs_mascarados += (
                            extra_cpfs_r + extra_cpfs_t + extra_cpfs_td
                        )
                        return parsed
            except Exception as exc:
                logger.info(
                    "Serviço interno ai_engine (%s) não ativo ou indisponível (%s). "
                    "Executando LocalDeterministicFallbackAdapter (ADR-002 / RNF-05).",
                    endpoint,
                    exc.__class__.__name__,
                )

        # 3. Fallback determinístico local (offline, seguro e de custo zero)
        return self._fallback.analyze_document(request)

    def comparar_pecas(
        self,
        texto_inicial: str,
        texto_contestacao: str,
        contexto_historico: Optional[ContextoHistoricoSchema] = None,
        numero_processo: Optional[str] = None,
    ) -> ResultadoComparacaoPecas:
        if settings.GEMINI_API_KEY.strip() and settings.AI_PROVIDER in ("gemini", "auto"):
            return self._gemini.comparar_pecas(texto_inicial, texto_contestacao, contexto_historico, numero_processo)
        return self._fallback.comparar_pecas(texto_inicial, texto_contestacao, contexto_historico, numero_processo)


ai_gateway = ResilientAIGateway()
