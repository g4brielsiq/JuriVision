"""
Módulo de Processamento de Documentos e NLP Processual — JuriVision (Card #18).

Responsável por transformar o texto bruto extraído de uma petição em informações estruturadas:
1. Limpeza e normalização do texto (LimpadorTexto)
2. Identificação das informações processuais (ExtratorInformacoesProcessuais)
3. Classificação por assunto com pontuação e confiança (ClassificadorAssunto)
4. Identificação de características processuais (ExtratorCaracteristicas)
5. Geração de resumo extrativo estruturado (GeradorResumo)

Princípios:
- Determinístico, local e sem dependências externas (RNF-05).
- NUNCA inventa dados: quando algo não é encontrado, retorna o marcador "Não identificado"
  e registra o campo em `campos_nao_identificados`.
- Não substitui a barreira LGPD: o resumo e os pedidos são gerados a partir de texto já
  higienizado pelo AnonimizadorLGPD (RN-01).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import hashlib
import re
import unicodedata
from typing import Optional

from app.schemas.contracts import CaracteristicasProcessuaisSchema, SecoesPeticaoSchema

NAO_IDENTIFICADO = "Não identificado"
NAO_IDENTIFICADA = "Não identificada"
NAO_CLASSIFICADO = "Não classificado"
PREFIXO_SEM_CNJ = "SEM-CNJ-"

CNJ_FORMATADO = re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")
CNJ_SEM_MASCARA = re.compile(r"(?<!\d)(\d{7})(\d{2})(\d{4})(\d)(\d{2})(\d{4})(?!\d)")


def sem_acento(texto: str) -> str:
    """Remove acentos e converte para minúsculas (usado só para comparação, nunca para exibição)."""
    normalizado = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in normalizado if unicodedata.category(c) != "Mn").lower()


def _titulo(texto: str) -> str:
    """Converte TEXTO EM CAIXA ALTA para Título, preservando preposições em minúsculas."""
    letras = [c for c in (texto or "") if c.isalpha() and c not in "ªº"]
    if not letras or sum(c.isupper() for c in letras) / len(letras) < 0.8:
        return texto
    minusculas = {"de", "da", "do", "das", "dos", "e", "em", "a", "o", "por", "para", "com"}
    palavras = texto.lower().split()
    return " ".join(p if (i > 0 and p in minusculas) else p[:1].upper() + p[1:] for i, p in enumerate(palavras))


# ==============================================================================
# 1. Limpeza e normalização do texto
# ==============================================================================
class LimpadorTexto:
    """Remove ruídos típicos de PDFs jurídicos sem alterar o conteúdo da petição."""

    MARCADOR_PAGINA = re.compile(
        r"^\s*(?:(?:p[áa]gina|p[áa]g\.?|fls?\.?|folha)\s*\d+(?:\s*(?:de|/)\s*\d+)?|-?\s*\d{1,3}\s*-?|\d{1,3}\s*/\s*\d{1,3})\s*$",
        re.IGNORECASE,
    )
    RODAPE_SISTEMA = re.compile(
        r"(?i)(documento assinado digitalmente|assinado eletronicamente|c[óo]digo de verifica[çc][ãa]o|"
        r"para conferir o original|https?://\S+|www\.\S+|e-saj|pje\s*-\s*processo judicial eletr[ôo]nico|"
        r"este documento (?:foi|é) (?:gerado|cópia))"
    )

    ITEM_ENUMERADO = re.compile(r"^(?:[a-z]|\d{1,2}|[ivx]{1,4})[\)\.]\s|^[-•]\s", re.IGNORECASE)

    @staticmethod
    def _eh_titulo(linha: str) -> bool:
        letras = [c for c in linha if c.isalpha()]
        return bool(letras) and len(linha) <= 120 and sum(c.isupper() for c in letras) / len(letras) >= 0.8

    @classmethod
    def limpar(cls, texto: str) -> str:
        if not texto:
            return ""

        texto = unicodedata.normalize("NFC", texto)
        texto = texto.replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ").replace("\t", " ")
        texto = re.sub(r"[​‌‍﻿]", "", texto)

        # Junta palavras hifenizadas na quebra de linha: "indeni-\nzação" -> "indenização"
        texto = re.sub(r"([A-Za-zÀ-ú])-\n\s*([a-zà-ú])", r"\1\2", texto)

        linhas = [re.sub(r" {2,}", " ", l).strip() for l in texto.split("\n")]

        # Cabeçalhos/rodapés repetidos (mesma linha curta aparecendo 3+ vezes)
        contagem = Counter(l for l in linhas if 8 <= len(l) <= 120)
        repetidas = {l for l, n in contagem.items() if n >= 3}

        filtradas: list[str] = []
        for linha in linhas:
            if linha in repetidas:
                continue
            if linha and cls.MARCADOR_PAGINA.match(linha):
                continue
            if linha and cls.RODAPE_SISTEMA.search(linha) and len(linha) <= 160:
                continue
            filtradas.append(linha)

        # Reconstrói parágrafos: une linhas quebradas no meio da frase (próxima linha começa com minúscula)
        resultado: list[str] = []
        for linha in filtradas:
            if (
                resultado
                and linha
                and resultado[-1]
                and linha[0].islower()
                and not resultado[-1].endswith((".", ":", ";", "!", "?"))
                and not cls.ITEM_ENUMERADO.match(linha)
                and not cls._eh_titulo(resultado[-1])
            ):
                resultado[-1] = f"{resultado[-1]} {linha}"
            else:
                resultado.append(linha)

        limpo = "\n".join(resultado)
        limpo = re.sub(r"\n{3,}", "\n\n", limpo)
        return limpo.strip()


# ==============================================================================
# 2. Identificação das informações processuais
# ==============================================================================
@dataclass
class InformacoesProcessuais:
    numero_processo: str
    magistrado: str
    comarca: str
    autor: Optional[str]
    reu: Optional[str]
    classe_processual: Optional[str]
    campos_nao_identificados: list[str] = field(default_factory=list)


class ExtratorInformacoesProcessuais:
    """Identifica número CNJ, magistrado, vara/comarca, partes e classe processual por padrões textuais."""

    MAGISTRADO = [
        re.compile(r"(?im)^\s*(?:magistrad[oa]|ju[íi]z(?:a)?(?:\s+de\s+direito)?|relator(?:a)?)\s*:\s*([^\n]{3,80})$"),
        re.compile(
            r"(?i)\b(?:MM\.?\s*)?ju[íi]z(?:a)?(?:\s+de\s+direito)?\s*,?\s*((?:Dr|Dra)\.?\s+[A-ZÀ-Ú][A-Za-zÀ-ú]+(?:\s+(?:de|da|do|dos|das|[A-ZÀ-Ú][A-Za-zÀ-ú]+)){1,5})"
        ),
    ]
    VARA = re.compile(
        r"(?i)(\d{1,2}\s*(?:ª|º|°|a|o)?\.?\s*(?:vara|juizado\s+especial)\s+[^\n,;]{3,70}|juizado\s+especial\s+[^\n,;]{3,70}|vara\s+(?:do\s+trabalho|[úu]nica)\s+[^\n,;]{0,50})"
    )
    COMARCA = re.compile(r"(?i)\bcomarca\s+de\s+([A-Za-zÀ-ú][A-Za-zÀ-ú\s\-]{2,40})")
    AUTOR = [
        re.compile(r"(?im)^\s*(?:autor(?:a)?|requerente|reclamante|impetrante|exequente)\s*:\s*([^\n,;]{3,80})"),
    ]
    REU = [
        re.compile(r"(?im)^\s*(?:r[ée]u|r[ée]|requerid[oa]|reclamad[oa]|impetrad[oa]|executad[oa])\s*:\s*([^\n,;]{3,80})"),
        re.compile(r"(?i)\bem\s+face\s+d[eoa]s?\s+([A-ZÀ-Ú][^\n,;]{2,80}?)(?:,|\s+pessoa\s+jur|\s+inscrit|\s+CNPJ|\n|$)"),
    ]
    CLASSE = re.compile(
        r"(?im)^\s*((?:a[çc][ãa]o|reclama[çc][ãa]o\s+trabalhista|mandado\s+de\s+seguran[çc]a|execu[çc][ãa]o\s+fiscal|embargos)\b[^\n]{0,110})$"
    )
    LIXO_FINAL = re.compile(r"[\s\-–—:,;/]+$")

    @classmethod
    def _limpar_valor(cls, valor: str) -> str:
        valor = re.sub(r"\s{2,}", " ", valor).strip()
        valor = cls.LIXO_FINAL.sub("", valor)
        # Remove ponto final, exceto em abreviações como "S.A." e "Ltda."
        if valor.endswith(".") and not re.search(r"(?i)(?:\b[a-z]\.|ltda\.|cia\.|me\.|epp\.)$", valor):
            valor = valor[:-1].rstrip()
        return valor

    @classmethod
    def numero_processo(cls, texto: str, arquivo_nome: str = "") -> tuple[str, bool]:
        achado = CNJ_FORMATADO.search(texto)
        if achado:
            return achado.group(0), True
        sem_mascara = CNJ_SEM_MASCARA.search(texto)
        if sem_mascara:
            g = sem_mascara.groups()
            return f"{g[0]}-{g[1]}.{g[2]}.{g[3]}.{g[4]}.{g[5]}", True
        # Identificador interno determinístico, claramente marcado como NÃO sendo um número CNJ
        digest = hashlib.sha256(f"{arquivo_nome}|{texto}".encode("utf-8")).hexdigest()[:10].upper()
        return f"{PREFIXO_SEM_CNJ}{digest}", False

    @classmethod
    def magistrado(cls, texto: str) -> Optional[str]:
        for padrao in cls.MAGISTRADO:
            achado = padrao.search(texto)
            if achado:
                valor = cls._limpar_valor(achado.group(1))
                if len(valor) >= 5 and not re.search(r"(?i)\bvara\b|\bcomarca\b|\bjuizado\b", valor):
                    return _titulo(valor)
        return None

    @classmethod
    def comarca(cls, texto: str) -> Optional[str]:
        vara = cls.VARA.search(texto)
        if vara:
            valor = cls._limpar_valor(vara.group(1))
            valor = re.sub(r"(?i)\s*[-–/]\s*(?:al|alagoas)$", "", valor)
            valor = _titulo(valor[:90])
            valor = re.sub(r"(?i)^(\d{1,2})\s*(?:a|ª|º|°|o)?\.?\s*vara", r"\1ª Vara", valor)
            return re.sub(r"(?i)^(\d{1,2})\s*(?:a|ª|º|°|o)?\.?\s*juizado", r"\1º Juizado", valor)
        comarca = cls.COMARCA.search(texto)
        if comarca:
            valor = cls._limpar_valor(comarca.group(1))
            valor = re.sub(r"(?i)\s*[-–/]\s*(?:al|alagoas)$", "", valor)
            return f"Comarca de {_titulo(valor)}"
        return None

    @classmethod
    def _primeiro(cls, padroes: list[re.Pattern], texto: str) -> Optional[str]:
        for padrao in padroes:
            achado = padrao.search(texto)
            if achado:
                valor = cls._limpar_valor(achado.group(1))
                if len(valor) >= 3:
                    return valor
        return None

    @classmethod
    def classe_processual(cls, texto: str) -> Optional[str]:
        achado = cls.CLASSE.search(texto[:4000])
        if not achado:
            return None
        valor = cls._limpar_valor(achado.group(1))
        return _titulo(valor) if len(valor) >= 8 else None

    @classmethod
    def extrair(cls, texto: str, arquivo_nome: str = "") -> InformacoesProcessuais:
        nao_identificados: list[str] = []

        numero, numero_ok = cls.numero_processo(texto, arquivo_nome)
        if not numero_ok:
            nao_identificados.append("numero_processo")

        magistrado = cls.magistrado(texto)
        if not magistrado:
            nao_identificados.append("magistrado")

        comarca = cls.comarca(texto)
        if not comarca:
            nao_identificados.append("comarca")

        autor = cls._primeiro(cls.AUTOR, texto)
        if not autor:
            nao_identificados.append("autor")

        reu = cls._primeiro(cls.REU, texto)
        if not reu:
            nao_identificados.append("reu")

        return InformacoesProcessuais(
            numero_processo=numero,
            magistrado=magistrado or NAO_IDENTIFICADO,
            comarca=comarca or NAO_IDENTIFICADA,
            autor=autor,
            reu=reu,
            classe_processual=cls.classe_processual(texto),
            campos_nao_identificados=nao_identificados,
        )


# ==============================================================================
# 3. Classificação por assunto
# ==============================================================================
@dataclass
class Classificacao:
    tema: str
    confianca: float
    termos_encontrados: list[str]
    tese_recomendada: str


class ClassificadorAssunto:
    """
    Classificador por pontuação de termos ponderados (sem acentos, case-insensitive).
    Os nomes de tema já usados no projeto foram mantidos para não fragmentar o dashboard.
    """

    TEMAS: dict[str, dict[str, int]] = {
        "Atraso de Voo / Indenização": {
            "voo": 3, "companhia aerea": 3, "aeroporto": 2, "bagagem": 3, "passageiro": 2,
            "overbooking": 3, "embarque": 2, "cancelamento do voo": 3, "transporte aereo": 3,
        },
        "Direito Trabalhista": {
            "reclamacao trabalhista": 4, "acao trabalhista": 3, "trabalhista": 2, "clt": 3, "horas extras": 3, "verbas rescisorias": 3, "fgts": 3,
            "reclamante": 2, "reclamada": 2, "empregador": 2, "vinculo empregaticio": 3, "aviso previo": 2,
            "justa causa": 2, "carteira de trabalho": 2, "trabalh": 1,
        },
        "Plano de Saúde": {
            "plano de saude": 4, "operadora": 2, "negativa de cobertura": 3, "cobertura": 1, "cirurgia": 2,
            "home care": 3, "rol da ans": 3, "tratamento medico": 2, "internacao": 2, "unimed": 3,
            "hapvida": 3, "amil": 3, "medico assistente": 2,
        },
        "Tributário": {
            "tribut": 3, "icms": 3, "iptu": 3, "ipva": 3, "execucao fiscal": 4, "fazenda publica": 2,
            "credito tributario": 3, "divida ativa": 3, "imposto": 2, "fisco": 2,
        },
        "Direito Previdenciário": {
            "inss": 4, "aposentadoria": 3, "auxilio-doenca": 3, "auxilio doenca": 3, "beneficio por incapacidade": 3,
            "bpc": 3, "loas": 3, "previdenciari": 3, "segurado": 2, "pensao por morte": 3,
        },
        "Direito de Família": {
            "pensao alimenticia": 4, "alimentos": 2, "guarda": 2, "divorcio": 4, "uniao estavel": 3,
            "regulamentacao de visitas": 3, "alimentando": 3, "genitor": 2,
        },
        "Direito Bancário": {
            "emprestimo consignado": 3, "consignado": 2, "juros abusivos": 3, "revisional": 3,
            "tarifa bancaria": 3, "capitalizacao de juros": 3, "financiamento": 2, "cartao de credito": 2,
            "contrato bancario": 3,
        },
        "Direito do Consumidor": {
            "vicio do produto": 3, "produto defeituoso": 3, "servico nao contratado": 3, "cobranca indevida": 2,
            "telefonia": 2, "entrega": 1, "compra": 1, "fornecedor": 1, "codigo de defesa do consumidor": 1,
        },
        "Dano Moral": {
            "negativacao": 3, "negativado": 3, "serasa": 3, "spc": 2, "protesto indevido": 3,
            "inscricao indevida": 3, "cadastro de inadimplentes": 3, "protecao ao credito": 3, "dano moral": 1,
            "danos morais": 1,
        },
    }

    TESES: dict[str, str] = {
        "Atraso de Voo / Indenização": (
            "Aplicação prioritária do Código de Defesa do Consumidor (art. 14 do CDC) e jurisprudência "
            "consolidada sobre dano moral in re ipsa por falha na prestação de assistência material ao passageiro."
        ),
        "Direito Trabalhista": (
            "Inversão do ônus da prova quanto aos controles de jornada (Súmula 338 do TST) e "
            "reconhecimento de verbas rescisórias incontroversas."
        ),
        "Plano de Saúde": (
            "Abusividade de negativa de cobertura de tratamento prescrito por médico assistente "
            "(Súmula 102 do TJ e CDC)."
        ),
        "Tributário": (
            "Observância estrita aos princípios da anterioridade e legalidade tributária, com "
            "afastamento de exigência fiscal sobre base de cálculo indevida."
        ),
        "Direito Previdenciário": (
            "Comprovação da qualidade de segurado e da carência, com análise da prova pericial "
            "e documental sobre a incapacidade ou o tempo de contribuição (Lei 8.213/91)."
        ),
        "Direito de Família": (
            "Observância do binômio necessidade-possibilidade (art. 1.694 do Código Civil) e "
            "do melhor interesse da criança e do adolescente."
        ),
        "Direito Bancário": (
            "Revisão de cláusulas contratuais abusivas à luz do CDC (Súmula 297 do STJ) e "
            "limitação de encargos à taxa média de mercado divulgada pelo Banco Central."
        ),
        "Direito do Consumidor": (
            "Responsabilidade objetiva do fornecedor por vício ou falha na prestação do serviço "
            "(arts. 14 e 18 do CDC) e repetição do indébito em dobro (art. 42, parágrafo único)."
        ),
        "Dano Moral": (
            "Responsabilidade civil objetiva do fornecedor de serviços (art. 14 do CDC) e "
            "configuração de falha na prestação do serviço com dever de indenizar."
        ),
        NAO_CLASSIFICADO: (
            "Tema não identificado automaticamente. Recomenda-se revisão manual da petição para "
            "definição da tese jurídica aplicável."
        ),
    }

    PONTUACAO_MINIMA = 2

    @classmethod
    def _contar(cls, termo: str, texto: str) -> int:
        # Termos curtos (siglas) exigem palavra inteira; termos longos ou radicais aceitam substring
        if len(termo) <= 4:
            return len(re.findall(rf"\b{re.escape(termo)}\b", texto))
        return texto.count(termo)

    @classmethod
    def classificar(cls, texto: str) -> Classificacao:
        base = sem_acento(texto)
        pontuacoes: dict[str, int] = {}
        termos_por_tema: dict[str, list[str]] = {}
        for tema, termos in cls.TEMAS.items():
            total = 0
            achados = []
            for termo, peso in termos.items():
                ocorrencias = cls._contar(termo, base)
                if ocorrencias:
                    total += peso * min(ocorrencias, 3)
                    achados.append(termo)
            pontuacoes[tema] = total
            termos_por_tema[tema] = achados

        melhor = max(pontuacoes, key=lambda t: pontuacoes[t])
        if pontuacoes[melhor] < cls.PONTUACAO_MINIMA:
            return Classificacao(NAO_CLASSIFICADO, 0.0, [], cls.TESES[NAO_CLASSIFICADO])

        soma = sum(pontuacoes.values()) or 1
        confianca = round(pontuacoes[melhor] / soma, 2)
        return Classificacao(melhor, confianca, termos_por_tema[melhor], cls.TESES[melhor])


# ==============================================================================
# 4. Características processuais
# ==============================================================================
class ExtratorCaracteristicas:
    SINAIS: dict[str, tuple[str, ...]] = {
        "tutela_urgencia": ("tutela de urgencia", "tutela antecipada", "tutela provisoria", "liminar", "inaudita altera pars"),
        "justica_gratuita": ("justica gratuita", "gratuidade da justica", "gratuidade de justica", "assistencia judiciaria gratuita", "art. 98 do cpc"),
        "danos_morais": ("danos morais", "dano moral", "dano extrapatrimonial"),
        "danos_materiais": ("danos materiais", "dano material", "lucros cessantes", "danos emergentes", "repeticao do indebito", "restituicao"),
        "inversao_onus_prova": ("inversao do onus da prova", "art. 6o, viii", "art. 6º, viii"),
        "prioridade_tramitacao": ("prioridade de tramitacao", "prioridade na tramitacao", "tramitacao prioritaria", "estatuto do idoso", "art. 1.048"),
    }
    VALOR_CAUSA = re.compile(
        r"(?i)(?:d[áa]-se\s+[àa]\s+causa\s+o\s+valor\s+de|atribui-se\s+[àa]\s+causa\s+o\s+valor\s+de|valor\s+da\s+causa\s*:?)\s*R\$\s*([\d\.]+(?:,\d{2})?)"
    )
    ITEM_PEDIDO = re.compile(r"(?:^|\n)\s*(?:[a-z]\)|\d{1,2}[\.\)]|[ivx]{1,4}\)|[-•])\s+", re.IGNORECASE)

    @classmethod
    def valor_causa(cls, texto: str) -> Optional[float]:
        achado = cls.VALOR_CAUSA.search(texto)
        if not achado:
            return None
        bruto = achado.group(1).replace(".", "").replace(",", ".")
        try:
            return round(float(bruto), 2)
        except ValueError:
            return None

    @classmethod
    def pedidos(cls, secao_pedidos: str) -> list[str]:
        if not secao_pedidos or not secao_pedidos.strip():
            return []
        # Ignora o fecho da petição (valor da causa, "Nestes termos", "Pede deferimento"...)
        fecho = re.search(
            r"(?i)(?:^|[\.\n]\s*)(?:d[áa]-se\s+[àa]\s+causa|atribui-se\s+[àa]\s+causa|nestes\s+termos|termos\s+em\s+que|pede\s+deferimento)",
            secao_pedidos,
        )
        if fecho:
            secao_pedidos = secao_pedidos[: fecho.start() + 1]
        partes = cls.ITEM_PEDIDO.split("\n" + secao_pedidos)
        itens = [re.sub(r"\s+", " ", p).strip(" ;.") for p in partes]
        itens = [i for i in itens if len(i) >= 10]
        if len(itens) <= 1:
            itens = [re.sub(r"\s+", " ", p).strip(" ;.") for p in secao_pedidos.split(";")]
            itens = [i for i in itens if len(i) >= 10]
        # Descarta o texto introdutório ("Diante do exposto, requer:") quando houver itens
        if len(itens) > 1 and itens[0].lower().rstrip(":").endswith(("requer", "requer-se", "pede")):
            itens = itens[1:]
        return [i[:300] for i in itens[:15]]

    @classmethod
    def extrair(cls, texto: str, secoes_higienizadas: Optional[SecoesPeticaoSchema], classe: Optional[str]) -> CaracteristicasProcessuaisSchema:
        base = sem_acento(texto)
        sinais = {nome: any(sem_acento(t) in base for t in termos) for nome, termos in cls.SINAIS.items()}
        pedidos = cls.pedidos(secoes_higienizadas.dos_pedidos if secoes_higienizadas else "")
        return CaracteristicasProcessuaisSchema(
            classe_processual=classe,
            valor_causa=cls.valor_causa(texto),
            pedidos=pedidos,
            **sinais,
        )


# ==============================================================================
# 5. Resumo extrativo estruturado
# ==============================================================================
class GeradorResumo:
    """
    Monta um resumo a partir do texto JÁ HIGIENIZADO: identificação da ação, fatos mais
    relevantes (frases pontuadas por termos do tema, datas e valores) e principais pedidos.
    """

    LIMITE = 900

    @staticmethod
    def _frases(texto: str) -> list[str]:
        return [f.strip() for f in re.split(r"(?<=[.!?])\s+|\n+", texto or "") if len(f.strip()) > 25]

    @classmethod
    def _frases_relevantes(cls, frases: list[str], termos: list[str], quantidade: int = 2) -> list[str]:
        if len(frases) <= quantidade:
            return frases
        pontuadas = []
        for i, frase in enumerate(frases):
            base = sem_acento(frase)
            pontos = sum(2 for t in termos if t in base)
            pontos += 1 if re.search(r"\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2} de [a-z]+ de \d{4}", base) else 0
            pontos += 1 if "r$" in base else 0
            pontos += max(0, 2 - i) * 0.5  # leve preferência pelas primeiras frases
            pontuadas.append((pontos, i, frase))
        escolhidas = sorted(pontuadas, key=lambda x: (-x[0], x[1]))[:quantidade]
        return [f for _, _, f in sorted(escolhidas, key=lambda x: x[1])]

    @classmethod
    def gerar(
        cls,
        *,
        texto_higienizado: str,
        secoes: Optional[SecoesPeticaoSchema],
        classificacao: Classificacao,
        caracteristicas: CaracteristicasProcessuaisSchema,
        autor: Optional[str],
        reu: Optional[str],
        comarca: str,
    ) -> str:
        abertura = caracteristicas.classe_processual or "Ação judicial"
        if classificacao.tema != NAO_CLASSIFICADO:
            abertura += f" ({classificacao.tema})"
        if autor and reu:
            abertura += f" proposta por {autor} em face de {reu}"
        elif reu:
            abertura += f" proposta em face de {reu}"
        if comarca not in (NAO_IDENTIFICADA, NAO_IDENTIFICADO):
            abertura += f", perante {comarca}"
        partes = [abertura + "."]

        fonte_fatos = secoes.dos_fatos if secoes and secoes.dos_fatos else texto_higienizado
        fatos = cls._frases_relevantes(cls._frases(fonte_fatos), classificacao.termos_encontrados)
        if fatos:
            trecho = " ".join(f if len(f) <= 260 else f[:257] + "..." for f in fatos)
            partes.append(f"Fatos: {trecho}")

        if caracteristicas.pedidos:
            principais = "; ".join(p if len(p) <= 140 else p[:137] + "..." for p in caracteristicas.pedidos[:3])
            partes.append(f"Pedidos: {principais}.")

        extras = []
        if caracteristicas.tutela_urgencia:
            extras.append("pedido de tutela de urgência")
        if caracteristicas.justica_gratuita:
            extras.append("pedido de justiça gratuita")
        if caracteristicas.valor_causa is not None:
            valor = f"{caracteristicas.valor_causa:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            extras.append(f"valor da causa de R$ {valor}")
        if extras:
            partes.append("Consta " + ", ".join(extras) + ".")

        resumo = " ".join(partes)
        if len(resumo) > cls.LIMITE:
            resumo = resumo[: cls.LIMITE - 3].rstrip() + "..."
        return resumo
