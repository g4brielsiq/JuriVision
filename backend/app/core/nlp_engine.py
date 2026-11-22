"""
Motor Matemático Local de Processamento de Linguagem Natural (NLP) e Jurimetria Estatística.
Substitui heurísticas fixas por:
- Tokenização jurídica e n-gramas normalizados
- Classificação multi-tema ponderada por léxico jurídico
- Extração dinâmica de magistrado e órgão julgador (comarca/vara)
- Sumarização extrativa por centralidade TF-IDF (ignorando cabeçalhos formais)
- Ranqueamento de precedentes por Similaridade de Cosseno (TF-IDF) + Okapi BM25
- Cálculo preditivo ponderado por similaridade e Intervalo de Confiança de Wilson
"""
from collections import Counter
import math
import re
import unicodedata
from typing import Any, Optional

PT_STOPWORDS = {
    "a",
    "ao",
    "aos",
    "apos",
    "as",
    "ate",
    "com",
    "como",
    "da",
    "das",
    "de",
    "dela",
    "dele",
    "deles",
    "demanda",
    "do",
    "dos",
    "e",
    "ela",
    "ele",
    "em",
    "entre",
    "era",
    "essa",
    "esse",
    "esta",
    "este",
    "face",
    "fls",
    "foi",
    "for",
    "fosse",
    "ha",
    "isso",
    "isto",
    "ja",
    "la",
    "mais",
    "mas",
    "me",
    "mesmo",
    "meu",
    "minha",
    "na",
    "nao",
    "nas",
    "nem",
    "no",
    "nos",
    "nossa",
    "nosso",
    "num",
    "numa",
    "o",
    "os",
    "ou",
    "para",
    "pela",
    "pelas",
    "pelo",
    "pelos",
    "perante",
    "pode",
    "pois",
    "por",
    "qual",
    "quando",
    "que",
    "quem",
    "se",
    "sem",
    "ser",
    "seu",
    "seus",
    "sim",
    "sob",
    "sobre",
    "sua",
    "suas",
    "tambem",
    "tem",
    "ter",
    "teve",
    "toda",
    "todo",
    "todos",
    "um",
    "uma",
    "umas",
    "uns",
    "vai",
    "vez",
    "voce",
    "cpf_anonimizado",
    "rg_anonimizado",
    "doc_anonimizado",
    "email_anonimizado",
    "telefone_anonimizado",
    "cep_anonimizado",
    "endereco_anonimizado",
    "nome_anonimizado",
}

LEGAL_THEME_LEXICON: list[dict[str, Any]] = [
    {
        "tema": "Atraso de Voo / Indenização",
        "default_reu": "Companhia Aérea Linhas Brasil S.A.",
        "tese": (
            "Aplicação prioritária do Código de Defesa do Consumidor (art. 14 do CDC) e Resolução 400 da ANAC, "
            "com configuração de dano moral in re ipsa por atraso/cancelamento de voo ou extravio de bagagem sem assistência material."
        ),
        "weights": {
            "voo": 4.0,
            "atraso_voo": 5.0,
            "cancelamento_voo": 5.0,
            "extravio_bagagem": 5.0,
            "companhia_aerea": 4.5,
            "aerea": 3.5,
            "aereo": 3.5,
            "bagagem": 4.0,
            "passageiro": 3.5,
            "aeroporto": 3.5,
            "anac": 4.0,
            "overbooking": 4.5,
            "embarque": 3.0,
            "conexao": 2.5,
            "assistencia_material": 3.5,
        },
    },
    {
        "tema": "Direito Trabalhista",
        "default_reu": "Tech Softwares e Serviços LTDA",
        "tese": (
            "Aplicação do princípio da primazia da realidade (art. 9º da CLT) e inversão do ônus probatório "
            "quanto aos controles de jornada (Súmula 338 do TST), com reflexos nas verbas rescisórias e FGTS."
        ),
        "weights": {
            "trabalhista": 4.5,
            "direito_trabalhista": 5.0,
            "reclamacao_trabalhista": 5.0,
            "clt": 4.0,
            "fgts": 4.0,
            "tst": 3.5,
            "horas_extras": 4.5,
            "horas_extraordinarias": 4.5,
            "verbas_rescisorias": 4.5,
            "rescisao_indireta": 4.5,
            "vinculo_empregaticio": 4.5,
            "adicional_noturno": 4.0,
            "assedio_moral": 3.5,
            "empregador": 3.5,
            "empregado": 3.5,
            "cartoes_ponto": 4.0,
            "aviso_previo": 3.5,
            "salario": 2.5,
        },
    },
    {
        "tema": "Plano de Saúde",
        "default_reu": "Operadora Unimed Saúde S.A.",
        "tese": (
            "Abusividade da negativa de cobertura de tratamento ou cirurgia prescrita por médico assistente "
            "(art. 35-C da Lei 9.656/98, CDC e mitigação do rol da ANS)."
        ),
        "weights": {
            "plano_saude": 5.0,
            "saude": 3.0,
            "unimed": 4.5,
            "hapvida": 4.5,
            "home_care": 4.5,
            "internacao_domiciliar": 4.5,
            "rol_ans": 4.5,
            "rol_taxativo": 4.5,
            "ans": 3.5,
            "cirurgia": 3.5,
            "tratamento": 3.0,
            "medicamento": 3.5,
            "oncologica": 4.0,
            "carencia": 3.5,
            "hospitalar": 3.0,
            "operadora": 3.0,
            "terapeutico": 3.5,
            "cobertura": 3.0,
        },
    },
    {
        "tema": "Tributário",
        "default_reu": "Fazenda Pública Estadual",
        "tese": (
            "Observância estrita aos princípios da legalidade e anterioridade tributária (art. 150 da CF e CTN), "
            "com afastamento de exação fiscal sobre base de cálculo indevida."
        ),
        "weights": {
            "tributario": 4.5,
            "execucao_fiscal": 5.0,
            "repeticao_indebito": 4.0,
            "icms": 4.5,
            "iss": 4.5,
            "iptu": 4.5,
            "irpf": 4.5,
            "difal": 4.5,
            "fisco": 4.0,
            "fazenda_publica": 4.5,
            "imposto": 3.5,
            "tributo": 4.0,
            "ctn": 4.0,
            "base_calculo": 4.0,
            "debito_fiscal": 4.5,
            "exacao": 3.5,
            "tributaria": 4.0,
        },
    },
    {
        "tema": "Direito Contratual / Obrigações",
        "default_reu": "Construtora e Incorporadora LTDA",
        "tese": (
            "Aplicação dos princípios da boa-fé objetiva e equilíbrio contratual (arts. 421 e 422 do Código Civil), "
            "com revisão ou afastamento de cláusula contratual abusiva."
        ),
        "weights": {
            "contratual": 3.5,
            "rescisao_contratual": 4.5,
            "clausula_abusiva": 4.0,
            "inadimplemento": 4.0,
            "locacao": 4.0,
            "imovel": 3.0,
            "financiamento": 3.0,
            "emprestimo": 3.0,
            "multa_contratual": 4.0,
            "revisao_contratual": 4.5,
            "juros_abusivos": 4.0,
            "compra_venda": 4.0,
        },
    },
    {
        "tema": "Direito Previdenciário / Administrativo",
        "default_reu": "Instituto Nacional do Seguro Social - INSS",
        "tese": (
            "Reconhecimento do direito ao benefício previdenciário ou tutela administrativa mediante comprovação "
            "técnica da qualidade de segurado e dos requisitos legais da Lei 8.213/91."
        ),
        "weights": {
            "inss": 4.5,
            "previdenciario": 4.5,
            "aposentadoria": 4.5,
            "auxilio_doenca": 4.5,
            "beneficio_previdenciario": 5.0,
            "bpc": 4.0,
            "loas": 4.0,
            "incapacidade": 3.5,
            "pericia_medica": 4.0,
            "servidor_publico": 4.0,
            "concurso_publico": 4.5,
            "pensao_morte": 4.5,
        },
    },
    {
        "tema": "Dano Moral",
        "default_reu": "Instituição Financeira Bradesco S.A.",
        "tese": (
            "Responsabilidade civil objetiva do fornecedor de serviços (art. 14 do CDC e Súmula 479/STJ) "
            "e configuração de dano moral in re ipsa por falha na prestação do serviço ou negativação indevida."
        ),
        "weights": {
            "dano_moral": 4.5,
            "negativacao_indevida": 4.5,
            "cobranca_indevida": 4.0,
            "cadastro_inadimplentes": 4.5,
            "serasa": 4.0,
            "spc": 4.0,
            "fraude_bancaria": 4.5,
            "falso_boleto": 4.5,
            "pix": 3.5,
            "cartao_credito": 3.5,
            "seguro_prestamista": 4.0,
            "desvio_produtivo": 4.0,
            "corte_energia": 4.0,
            "in_re_ipsa": 3.5,
            "bancaria": 3.0,
            "banco": 2.5,
            "cdc": 2.0,
            "indenizacao": 2.0,
        },
    },
]

_JUDGE_BAD_FRAGMENTS = (
    "vara",
    "comarca",
    "tribunal",
    "juizado",
    "advogado",
    "oab",
    "autor",
    "reu",
    "processo",
    "maceio",
    "alagoas",
    "direito",
)


def normalize_text(text: str) -> str:
    """Normaliza texto removendo acentos e convertendo para minúsculas ASCII."""
    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii").lower()


def tokenize_legal_text(text: str, include_bigrams: bool = True) -> list[str]:
    """Extrai unigramas e bigramas jurídicos relevantes após remoção de stopwords e placeholders LGPD."""
    norm = normalize_text(text)
    raw_words = re.findall(r"[a-z0-9_]{2,}", norm)
    unigrams = [w for w in raw_words if w not in PT_STOPWORDS and not w.startswith("_")]
    if not include_bigrams or len(unigrams) < 2:
        return unigrams
    bigrams = [f"{unigrams[i]}_{unigrams[i + 1]}" for i in range(len(unigrams) - 1)]
    return unigrams + bigrams


def classify_legal_theme(text: str) -> tuple[str, str, str]:
    """
    Classifica a matéria jurídica do texto por pontuação léxica ponderada sobre unigramas e bigramas.
    Retorna: (tema, tese_recomendada, default_reu).
    """
    tokens = tokenize_legal_text(text, include_bigrams=True)
    counts = Counter(tokens)

    best_entry = LEGAL_THEME_LEXICON[-1]  # fallback seguro: Dano Moral
    best_score = 0.0

    for entry in LEGAL_THEME_LEXICON:
        score = 0.0
        for term, weight in entry["weights"].items():
            freq = counts.get(term, 0)
            if freq > 0:
                score += weight * (1.0 + math.log(freq))
        if score > best_score:
            best_score = score
            best_entry = entry

    return best_entry["tema"], best_entry["tese"], best_entry["default_reu"]


def _is_valid_judge_candidate(candidate: str) -> bool:
    norm = normalize_text(candidate)
    if len(norm) < 4:
        return False
    return not any(bad in norm for bad in _JUDGE_BAD_FRAGMENTS)


def extract_court_and_judge(raw_text: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extrai dinamicamente qualquer magistrado(a) e órgão julgador (vara/comarca) citado no documento,
    sem depender de lista fechada de nomes hardcoded.
    """
    magistrado: Optional[str] = None
    name_body = r"[A-ZÀ-Ú][a-zà-ú]+(?:[ \t]+(?:de|da|do|das|dos|De|Da|Do)?[ \t]*[A-ZÀ-Ú][a-zà-ú]+){1,4}"

    labeled_judge = re.search(
        r"(?i:\b(?:Magistrad[oa]|Ju[íi]z(?:a)?(?:[ \t]+de[ \t]+Direito)?|Relator(?:a)?|Desembargador(?:a)?))\s*:\s*"
        r"((?:Dr\.?|Dra\.?|Des\.?|Min\.?)?[ \t]*" + name_body + r")",
        raw_text,
    )
    if labeled_judge:
        cand = " ".join(labeled_judge.group(1).strip().split())
        if _is_valid_judge_candidate(cand):
            magistrado = cand

    if not magistrado:
        honorific_judge = re.search(
            r"\b((?:Dr\.|Dra\.|Des\.)[ \t]+" + name_body + r")",
            raw_text,
        )
        if honorific_judge:
            cand = " ".join(honorific_judge.group(1).strip().split())
            if _is_valid_judge_candidate(cand):
                magistrado = cand

    comarca: Optional[str] = None
    court_match = re.search(
        r"(?i)\b("
        r"\d+[ªa°][ \t]+Vara[ \t]+[A-Za-zÀ-ú0-9 \t]{3,55}"
        r"|Vara[ \t]+(?:da[ \t]+Fazenda|do[ \t]+Trabalho|Ambiental|C[íi]vel|Criminal|[ÚU]nica|do[ \t]+[ÚU]nico[ \t]+Of[íi]cio|de[ \t]+Fam[íi]lia)[A-Za-zÀ-ú0-9 \t]{0,45}"
        r"|Juizado[ \t]+Especial[A-Za-zÀ-ú0-9 \t]{0,45}"
        r"|\d+[ªa°][ \t]+C[âa]mara[ \t]+[A-Za-zÀ-ú0-9 \t]{3,45}"
        r")",
        raw_text,
    )
    if court_match:
        cand_court = " ".join(court_match.group(1).strip(" ,.;:-").split())
        if len(cand_court) >= 6:
            comarca = cand_court

    return magistrado, comarca


def _is_boilerplate_header(sentence: str) -> bool:
    norm = normalize_text(sentence).strip()
    if len(norm) < 20:
        return True
    header_prefixes = (
        "excelentissimo",
        "exmo",
        "processo:",
        "processo nº",
        "processo n ",
        "magistrado:",
        "magistrada:",
        "comarca:",
        "vara:",
    )
    if norm.startswith(header_prefixes) and len(norm) < 95:
        return True
    if norm.isupper() and len(norm.split()) <= 12:
        return True
    return False


def summarize_legal_text(sanitized_text: str, tema: str, fallback_summary: str) -> str:
    """
    Gera síntese extrativa por centralidade TF-IDF sobre sentenças higienizadas,
    priorizando sentenças com densidade factual jurídica em vez de cabeçalhos formais.
    """
    raw_sentences = [
        " ".join(s.strip().split())
        for s in re.split(r"(?<=[.!?])\s+|\n+", sanitized_text or "")
        if len(s.strip()) > 15
    ]
    if not raw_sentences:
        return fallback_summary

    factual = [s for s in raw_sentences if not _is_boilerplate_header(s)]
    candidates = factual if factual else [s for s in raw_sentences if len(s) > 20]
    if not candidates:
        return fallback_summary

    if len(candidates) <= 2:
        excerpt = " ".join(candidates)
    else:
        doc_tokens = [tokenize_legal_text(s, include_bigrams=False) for s in candidates]
        n_docs = len(doc_tokens)
        df: Counter[str] = Counter()
        for toks in doc_tokens:
            df.update(set(toks))

        scores: list[tuple[int, float]] = []
        for idx, toks in enumerate(doc_tokens):
            if not toks:
                scores.append((idx, 0.0))
                continue
            tf = Counter(toks)
            tfidf_sum = sum(
                (1.0 + math.log(freq)) * (math.log((1.0 + n_docs) / (1.0 + df[term])) + 1.0)
                for term, freq in tf.items()
            )
            density = tfidf_sum / math.sqrt(len(toks) + 1.0)
            scores.append((idx, density))

        top_indices = sorted(
            [idx for idx, _ in sorted(scores, key=lambda x: x[1], reverse=True)[:2]]
        )
        excerpt = " ".join(candidates[i] for i in top_indices)

    if len(excerpt) > 420:
        excerpt = excerpt[:417].rstrip() + "..."
    return f"Síntese processual higienizada ({tema}): {excerpt}"


def compute_wilson_margin(prob: float, n: int, z: float = 1.28) -> float:
    """
    Calcula a meia-largura do Intervalo de Confiança de Wilson para proporção binomial.
    Diminui à medida que a amostra de precedentes similares (n) cresce.
    """
    if n <= 0:
        return 0.25
    p = max(min(prob, 0.99), 0.01)
    z2 = z * z
    denom = 1.0 + (z2 / n)
    radicand = (p * (1.0 - p) + (z2 / (4.0 * n))) / n
    margin = (z * math.sqrt(max(radicand, 0.0))) / denom
    return round(max(min(margin, 0.25), 0.03), 2)


def rank_similar_precedents(
    query_text: str,
    processes: list[Any],
    target_tema: Optional[str] = None,
    target_magistrado: Optional[str] = None,
    top_k: int = 15,
    min_similarity: float = 0.08,
) -> list[dict[str, Any]]:
    """
    Ranqueia precedentes do banco combinando Similaridade de Cosseno (TF-IDF sublinear) e Okapi BM25,
    com afinidade controlada por tema e magistrado quando disponíveis.
    """
    if not processes:
        return []

    query_tokens = tokenize_legal_text(query_text, include_bigrams=True)
    if not query_tokens:
        return []

    docs_tokens: list[list[str]] = []
    for proc in processes:
        pred = getattr(proc, "analise_preditiva", None)
        tese_txt = pred.tese_recomendada if pred else ""
        doc_str = (
            f"{proc.tema or ''} {proc.tema or ''} {proc.comarca or ''} "
            f"{proc.magistrado or ''} {proc.resumo_nlp or ''} {tese_txt or ''}"
        )
        docs_tokens.append(tokenize_legal_text(doc_str, include_bigrams=True))

    n_docs = len(docs_tokens)
    avgdl = max(sum(len(d) for d in docs_tokens) / max(n_docs, 1), 1.0)
    df: Counter[str] = Counter()
    for d in docs_tokens:
        df.update(set(d))

    idf = {term: math.log((1.0 + n_docs) / (1.0 + freq)) + 1.0 for term, freq in df.items()}

    q_tf = Counter(query_tokens)
    q_vec = {
        term: (1.0 + math.log(freq)) * idf.get(term, math.log(1.0 + n_docs) + 1.0)
        for term, freq in q_tf.items()
    }
    q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0

    # Parâmetros padrão Okapi BM25
    k1 = 1.5
    b = 0.75
    bm25_raw_scores: list[float] = []
    cos_scores: list[float] = []

    for d_toks in docs_tokens:
        d_tf = Counter(d_toks)
        dl = max(len(d_toks), 1)
        d_vec = {term: (1.0 + math.log(freq)) * idf[term] for term, freq in d_tf.items() if term in idf}
        d_norm = math.sqrt(sum(v * v for v in d_vec.values())) or 1.0

        dot = sum(q_vec[t] * d_vec[t] for t in q_vec if t in d_vec)
        cos_scores.append(dot / (q_norm * d_norm))

        bm25_score = 0.0
        for term in q_tf:
            if term in d_tf:
                f = d_tf[term]
                term_idf = idf.get(term, 0.0)
                bm25_score += term_idf * ((f * (k1 + 1.0)) / (f + k1 * (1.0 - b + b * (dl / avgdl))))
        bm25_raw_scores.append(bm25_score)

    max_bm25 = max(bm25_raw_scores) if bm25_raw_scores else 0.0
    norm_target_tema = normalize_text(target_tema or "").strip()
    norm_target_juiz = normalize_text(target_magistrado or "").strip()

    ranked: list[dict[str, Any]] = []
    for idx, proc in enumerate(processes):
        bm25_norm = (bm25_raw_scores[idx] / max_bm25) if max_bm25 > 0 else 0.0
        sim = 0.6 * cos_scores[idx] + 0.4 * bm25_norm

        proc_tema_norm = normalize_text(proc.tema or "")
        proc_juiz_norm = normalize_text(proc.magistrado or "")
        if norm_target_tema and (norm_target_tema in proc_tema_norm or proc_tema_norm in norm_target_tema):
            sim += 0.12
        if norm_target_juiz and norm_target_juiz == proc_juiz_norm:
            sim += 0.08

        sim = round(min(sim, 0.99), 4)
        if sim < min_similarity:
            continue

        pred = getattr(proc, "analise_preditiva", None)
        prazo = pred.tempo_estimado_sentenca_meses if pred else 12
        tese = pred.tese_recomendada if pred else ""
        ranked.append(
            {
                "id_processo": proc.id_processo,
                "numero_processo": proc.numero_processo,
                "tema": proc.tema,
                "magistrado": proc.magistrado,
                "resultado": proc.resultado_historico,
                "similaridade": sim,
                "prazo_meses": max(int(prazo), 1),
                "tese": tese or "",
            }
        )

    ranked.sort(key=lambda item: item["similaridade"], reverse=True)
    return ranked[:top_k]


def compute_jurimetria_prediction(
    query_text: str,
    processes: list[Any],
    target_tema: Optional[str] = None,
    target_magistrado: Optional[str] = None,
    top_k: int = 15,
) -> dict[str, Any]:
    """
    Calcula probabilidade ponderada, margem de confiança (Wilson), prazo estimado e
    metadados inferidos a partir dos precedentes similares reais do banco.
    """
    ranked = rank_similar_precedents(
        query_text=query_text,
        processes=processes,
        target_tema=target_tema,
        target_magistrado=target_magistrado,
        top_k=top_k,
        min_similarity=0.08,
    )

    if not ranked:
        return {
            "total_casos_similares": 0,
            "taxa_favoravel_juiz": 0.50,
            "tempo_medio_meses": 12,
            "margem_confianca_calculada": compute_wilson_margin(0.50, 0),
            "tese_precedente_similar": None,
            "magistrado_inferido": None,
            "precedentes_similares": [],
        }

    proc_by_id = {p.id_processo: p for p in processes}
    total_weight = 0.0
    fav_weight = 0.0
    prazo_weight = 0.0
    juiz_weights: Counter[str] = Counter()

    for item in ranked:
        w = max(float(item["similaridade"]), 0.05)
        res_lower = (item["resultado"] or "").lower()
        if res_lower in ("procedente", "acordo"):
            outcome = 1.0
        elif res_lower == "improcedente":
            outcome = 0.0
        else:
            p_obj = proc_by_id.get(item["id_processo"])
            pred_obj = getattr(p_obj, "analise_preditiva", None) if p_obj else None
            outcome = float(pred_obj.probabilidade_deferimento) if pred_obj else 0.5

        total_weight += w
        fav_weight += w * outcome
        prazo_weight += w * item["prazo_meses"]
        if item["magistrado"]:
            juiz_weights[item["magistrado"]] += w

    prob = round(max(min(fav_weight / total_weight, 0.95), 0.15), 2)
    n_similares = len(ranked)
    margem = compute_wilson_margin(prob, n_similares)
    tempo_medio = max(int(round(prazo_weight / total_weight)), 1)
    top_tese = ranked[0]["tese"] if (ranked[0]["similaridade"] >= 0.25 and ranked[0]["tese"]) else None
    magistrado_inferido = juiz_weights.most_common(1)[0][0] if juiz_weights else None

    return {
        "total_casos_similares": n_similares,
        "taxa_favoravel_juiz": prob,
        "tempo_medio_meses": tempo_medio,
        "margem_confianca_calculada": margem,
        "tese_precedente_similar": top_tese,
        "magistrado_inferido": magistrado_inferido,
        "precedentes_similares": ranked,
    }
