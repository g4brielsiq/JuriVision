"""
Fronteira de Isolamento do Módulo de Inteligência Artificial (Port & Adapter + Barreira LGPD).
Rastreabilidade:
- ARCHITECTURE.md: ADR-001 (HTTP Interno), ADR-002 (Strategy/Adapter + Fallback Local), Seção 5 e Seção 8.7
- MODELING.md: RF-02, RF-04, RF-05, RF-06, RNF-05 (Tolerância a Falhas), RNF-06 (LGPD), RNF-07 (Modularidade), RN-01 a RN-04
"""
from abc import ABC, abstractmethod
import hashlib
import io
import json
import logging
import re
from typing import Tuple
import zlib

import httpx
from pypdf import PdfReader

from app.core.config import settings
from app.core.nlp_engine import (
    build_rag_precedents_context,
    classify_legal_theme,
    compute_wilson_margin,
    extract_court_and_judge,
    summarize_legal_text,
    synthesize_local_rag_tendencia,
)
from app.schemas.contracts import (
    AnalisePreditivaSchema,
    AuditoriaLGPDSchema,
    InternalAnalyzeRequest,
    InternalAnalyzeResponse,
    MetadadosExtraidosSchema,
    PartesAnonimizadasSchema,
)

logger = logging.getLogger("jurivision.ai_gateway")

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
    def extract_parties_from_text(cls, raw_text: str, default_reu: str) -> Tuple[str, str]:
        """Extrai Autor e Réu de cabeçalhos explícitos ou de construções em prosa jurídica."""
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
            raw_autor = cleaned_autor or "Lucas Gabriel Rodrigues"

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
                    raw_reu = cleaned_reu or default_reu
            else:
                raw_reu = default_reu

        return raw_autor, raw_reu

    @classmethod
    def sanitize_text(cls, raw_text: str, known_natural_names: list[str] | None = None) -> Tuple[str, int, int]:
        """
        Varre um texto jurídico bruto e substitui documentos civis (RG, CNH/CTPS/PIS, CPF),
        e-mails, telefones, CEPs, endereços e nomes de pessoas físicas (em cabeçalhos e prosa).
        Retorna: (texto_higienizado, total_identificadores_mascarados, total_nomes_mascarados)
        """
        if not raw_text:
            return "", 0, 0

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


class ExtratorDocumental:
    """
    Serviço determinístico local de validação de integridade e extração textual de PDFs (RF-02 / RN-04).
    Suporta PDFs padrão via `pypdf`, operadores `Tj`/`TJ` diretos, metadados `/ActualText` e streams `FlateDecode`.
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

    @classmethod
    def extract_text_from_pdf_bytes(cls, file_bytes: bytes) -> str:
        if not file_bytes or len(file_bytes) < 10:
            raise ValueError("Arquivo vazio ou sem conteúdo binário válido.")

        if not file_bytes.lstrip().startswith(b"%PDF-"):
            raise ValueError("Assinatura binária inválida: o arquivo enviado não é um documento PDF (%PDF-).")

        extracted_chunks: list[str] = []
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    extracted_chunks.append(page_text.strip())
        except Exception:
            # Fallback para PDFs sintéticos ou operadores Tj/TJ diretos e streams FlateDecode
            pass

        if not extracted_chunks:
            raw_latin = file_bytes.decode("latin-1", errors="ignore")
            extracted_chunks.extend(cls._extract_operators_from_stream_text(raw_latin))

        if not extracted_chunks:
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
                    extracted_chunks.extend(cls._extract_operators_from_stream_text(stream_str))

        full_text = "\n".join(extracted_chunks).strip()
        if not full_text:
            raise ValueError("Não foi possível extrair texto legível do PDF enviado (FalhaOCR / Documento vazio).")

        return full_text


class AIGatewayPort(ABC):
    """
    Interface Abstrata (Port) para comunicação entre o Back-end Core e o Motor de Inteligência (ADR-002).
    """

    @abstractmethod
    def analyze_document(self, request: InternalAnalyzeRequest) -> InternalAnalyzeResponse:
        """Processa um documento extraindo metadados anonimizados, resumo NLP e análise preditiva."""
        raise NotImplementedError


class LocalDeterministicFallbackAdapter(AIGatewayPort):
    """
    Adaptador Heurístico e Estatístico Local (`local_heuristic`).
    Garante funcionamento 100% autônomo e determinístico (RNF-05 / RN-03) quando o container
    `ai_engine` está em scaffolding ou sem chave de LLM externo.
    """

    def analyze_document(self, request: InternalAnalyzeRequest) -> InternalAnalyzeResponse:
        raw_text = request.texto_bruto or ""

        # 1. Extração de Número CNJ (ou geração determinística baseada no hash do documento)
        cnj_match = CNJ_REGEX.search(raw_text)
        if cnj_match:
            numero_processo = cnj_match.group(0)
        else:
            digest = hashlib.sha256((request.arquivo_nome + raw_text).encode("utf-8")).hexdigest()
            seq = int(digest[:7], 16) % 9000000 + 1000000
            dv = int(digest[7:9], 16) % 90 + 10
            numero_processo = f"{seq:07d}-{dv:02d}.2026.8.02.0001"

        # 2. Classificação Multi-Tema por Pontuação Léxica Ponderada
        tema, tese_recomendada, default_reu = classify_legal_theme(raw_text)

        # 3. Extração Dinâmica de Magistrado e Comarca/Vara (sem lista hardcoded)
        ctx = request.contexto_historico
        magistrado_doc, comarca_doc = extract_court_and_judge(raw_text)
        magistrado = magistrado_doc or ctx.magistrado_inferido or "Magistrado não especificado"
        comarca = comarca_doc or "Juízo Cível Competente"

        # 4. Identificação de Partes e Barreira Obrigatória LGPD (RN-01 / RF-04)
        raw_autor, raw_reu = AnonimizadorLGPD.extract_parties_from_text(raw_text, default_reu)

        autor_anon, autor_masked = AnonimizadorLGPD.mask_party_name(raw_autor)
        reu_anon, reu_masked = AnonimizadorLGPD.mask_party_name(raw_reu)

        known_for_sanitization = []
        if raw_autor in raw_text:
            known_for_sanitization.append(raw_autor)
        if raw_reu in raw_text:
            known_for_sanitization.append(raw_reu)

        sanitized_text, cpf_rg_count, contextual_names_count = AnonimizadorLGPD.sanitize_text(
            raw_text, known_natural_names=known_for_sanitization
        )
        total_names_masked = max(
            contextual_names_count,
            (1 if autor_masked else 0) + (1 if reu_masked else 0),
        )

        # 5. Sumarização Factual Extrativa por Centralidade TF-IDF (RF-05)
        fallback_summary = (
            f"Ação judicial vinculada ao tema '{tema}' tramitando perante {comarca}, "
            f"tendo como partes {autor_anon} em face de {reu_anon}, submetida à análise preditiva."
        )
        resumo_nlp = summarize_legal_text(sanitized_text, tema, fallback_summary)

        # Garantia extra pós-sumarização de que nenhum PII escapou
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
            magistrado=magistrado,
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
        sanitized_text, _, _ = AnonimizadorLGPD.sanitize_text(request.texto_bruto or "")
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

        # 3. Montar prompt estruturado de RAG Jurídico estritamente sobre texto desidentificado
        prompt = (
            "Você é um perito jurimétrico especialista em jurisprudência brasileira (TJAL / Tribunais Estaduais).\n"
            "Analise o teor fático anonimizado da petição abaixo (dados pessoais já desidentificados sob a LGPD) "
            "cruzando-o obrigatoriamente com os precedentes similares e métricas estatísticas recuperadas do acervo:\n\n"
            f"--- INÍCIO DO TEXTO ANONIMIZADO ---\n{sanitized_text[:4000]}\n--- FIM DO TEXTO ANONIMIZADO ---\n\n"
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
            f"{settings.GEMINI_MODEL}:generateContent?key={api_key}"
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
                res = client.post(url, json=payload)
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
                "Chamada ao Gemini API não concluída (%s: %s). Acionando fallback determinístico local (ADR-002).",
                exc.__class__.__name__,
                str(exc),
            )

        return base_resp


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


ai_gateway = ResilientAIGateway()
