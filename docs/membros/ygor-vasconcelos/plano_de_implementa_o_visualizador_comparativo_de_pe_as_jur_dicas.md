# Plano de Implementação: Visualizador Comparativo de Peças Jurídicas (Petição Inicial vs. Contestação)

> **Projeto JuriVision** — Plataforma de Pesquisa Jurisprudencial e Jurimetria  
> **Módulo:** Visualizador Comparativo de Peças Processuais (Saneamento, Convergências, Divergências e Probabilidade de Procedência)  
> **Status:** Plano de implementação revisado em 23/11/2026 para refletir o cálculo jurimétrico, a identificação do motor no resultado e a demonstração guiada.

---

## 1. Visão Geral e Objetivo

O objetivo deste módulo é permitir que advogados e equipes jurídicas realizem o upload simultâneo de duas peças fundamentais de um processo (**Petição Inicial** e **Contestação**) para realizar uma análise completa de saneamento processual (art. 357 do CPC) e preparação de réplica:

1. **Identificar automaticamente os pontos controvertidos e incontroversos** ao longo de **7 eixos jurídicos** (Preliminares, Prejudiciais de Mérito, Fatos/Cronologia/Valores, Mérito, Tutelas Provisórias, Provas/Ônus e Pedidos Finais).
2. **Classificar cada ponto confrontado** em:
   * **Convergente (`convergente`):** Ambas as partes concordam expressamente;
   * **Divergente (`divergente`):** O réu impugnou especificamente a alegação, data, valor ou pedido do autor;
   * **Incontroverso por Omissão (`fato_incontroverso_por_omissao`):** O réu não impugnou especificamente o argumento ou pedido do autor (art. 341 do CPC, desconsiderando negativa geral);
   * **Fato Novo / Extintivo da Defesa (`fato_novo_ou_extintivo_reu`):** O réu alegou fato impeditivo, modificativo ou extintivo inédito (art. 350 do CPC, ex.: pagamento, compensação, culpa de terceiro) sem correspondência prévia na inicial.
3. **Gerar orientação processual acionável (`impacto_processual`)** e exibir uma estimativa de procedência por tese quando houver histórico suficiente para o tema.
4. **Exibir a comparação em uma interface visual lado a lado (*Split-View*)**, sincronizada, com filtros por eixo jurídico e status e identificação do motor que produziu o resultado.

---

## 2. Stack Tecnológica Selecionada

A escolha das tecnologias alinha as necessidades jurídicas do estudo de caso com a arquitetura já estabelecida no repositório JuriVision:

| Camada | Tecnologia | Justificativa Técnica no JuriVision |
| :--- | :--- | :--- |
| **Parsing e Extração de PDF** | `pdfplumber` + `PyMuPDF` (`fitz`) | `pdfplumber` já está instalado e ativo no backend do JuriVision. Permite extração página a página com injeção de marcadores `[PÁG XX]`, segmentação por seções e coordenadas $(x, y)$ para mapear trechos com exatidão. |
| **Privacidade & LGPD** | `AnonimizadorLGPD` (Motor interno em Regex + Hash SHA-256) | Invariante inegociável do projeto (`RN-01`). Higieniza CPFs, RGs e nomes de pessoas físicas **antes** do envio a qualquer LLM ou banco de dados, preservando datas, valores monetários e normas legais. |
| **Núcleo de IA e NLP** | **Google Gemini API** (Gemini 2.5 Flash / Pro) via `AIProviderAdapter` | Janela de contexto longa ideal para varredura bidirecional (Autor $\rightarrow$ Réu e Réu $\rightarrow$ Autor) em uma única chamada. O modo local (`AI_PROVIDER=local`) permanece como fallback determinístico para custo zero e testes offline. |
| **Tipagem e Contrato Estruturado** | `Pydantic v2` (*Structured Outputs*) | Garante que a IA retorne um JSON rígido e validado (`response_schema`), utilizando `Field(description=...)` para orientar a classificação jurídica e citações literais. |
| **Backend & API Gateway** | **Python 3.11+ / FastAPI** | Framework oficial do projeto: rápido, tipado, assíncrono e integrado à documentação OpenAPI / Swagger (`/docs`). |
| **Orquestração Assíncrona** | FastAPI `BackgroundTasks` + Server-Sent Events (SSE) / Polling estruturado | Permite acompanhar o processamento de 15 a 30 segundos das peças sem inflar a arquitetura com serviços externos pesados (conforme `ADR-001`). |
| **Motor de Jurimetria** | `SQLAlchemy 2.0` + base de julgados | Usa o histórico de desfechos cadastrados manualmente para o mesmo tema da tese, com amostra mínima e suavização de Laplace. |
| **Frontend Web** | **HTML5 Semântico + Vanilla ES Modules + CSS Design Tokens** (*Legal Editorial*) | Segue a arquitetura leve e acessível já padronizada no JuriVision (**W3C WCAG 2.2 Nível AA**), evitando overhead de build desnecessário. |
| **Visualização Split-View** | Componente Customizado de 3 Colunas Sincronizadas (com `scrollIntoView` e *highlights*) | Permite navegar pelos textos em paralelo, filtrando por eixo jurídico/status e destacando trechos literais com códigos de cores semânticos. |

---

## 3. Arquitetura do Fluxo de Dados (Pipeline)

```mermaid
flowchart TD
    A["Upload dos 2 PDFs<br/>(Inicial e Contestação)"] --> B["Validação de Integridade<br/>MIME & Assinatura %PDF-"]
    B --> C["Extração Textual + Tags [PÁG XX]<br/>(pdfplumber / PyMuPDF)"]
    C --> D["Barreira LGPD Obrigatória<br/>(AnonimizadorLGPD)"]
    D --> E["Segmentação Estrutural via Regex<br/>(Fatos, Preliminares, Mérito, Tutela, Provas, Pedidos)"]
    E --> F["Motor de IA (AIProviderAdapter)<br/>Varredura Bidirecional (Gemini / Fallback Local)"]
    F --> G["Schema Pydantic (7 Eixos Jurídicos):<br/>- Convergente / Divergente<br/>- Omissão (Art. 341) / Fato Novo Réu (Art. 350)"]
    G --> H["Estimativa por tema<br/>Histórico suficiente ou estimativa indisponível"]
    H --> I["Resultado da comparação<br/>Impacto processual e motor usado"]
    I --> J["Interface Split-View (Frontend 3 Colunas)<br/>Filtros, destaques e rótulo do motor"]
```

---

## 4. Estrutura de Dados Contratada (Schemas Pydantic)

O contrato de dados (`backend/app/schemas/comparacao.py`) garante que tanto a IA quanto a interface trabalhem com cobertura jurídica completa para saneamento e réplica:

```python
from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class StatusTese(str, Enum):
    CONVERGENTE = "convergente"
    DIVERGENTE = "divergente"
    INCONTROVERSO_POR_OMISSAO = "fato_incontroverso_por_omissao"
    FATO_NOVO_DEFESA = "fato_novo_ou_extintivo_reu"

class TipoTese(str, Enum):
    PRELIMINAR = "preliminar"
    PREJUDICIAL_MERITO = "prejudicial_merito"
    FATO_CRONOLOGIA = "fato_ou_valor"
    MERITO = "merito"
    TUTELA_PROVISORIA = "tutela_provisoria"
    PROVA_ONUS = "prova_e_onus"
    PEDIDO = "pedido_e_valor_causa"

class PontoControvertido(BaseModel):
    id_tese: str = Field(
        description="Identificador único sequencial, ex: 'TESE-01'."
    )
    tipo: TipoTese = Field(
        description="Categoria jurídica estrita entre os 7 eixos de análise processual."
    )
    tema: str = Field(
        description="Título curto e objetivo (ex: 'Data do Inadimplemento', 'Inversão do Ônus da Prova', 'Prescrição Trienal')."
    )
    trecho_autor: Optional[str] = Field(
        default=None,
        description="Citação literal exata extraída da Petição Inicial (sem alterar palavras). Deve ser null apenas se status='fato_novo_ou_extintivo_reu'."
    )
    trecho_reu: Optional[str] = Field(
        default=None,
        description="Citação literal exata extraída da Contestação. Deve ser null apenas se status='fato_incontroverso_por_omissao'."
    )
    status: StatusTese = Field(
        description="Classificação do confronto conforme arts. 341 e 350 do CPC."
    )
    forca_probatoria_autor: str = Field(
        description="Avaliação objetiva do lastro probatório do autor neste ponto (ex: 'Documental Robusta - Contrato Assinado')."
    )
    forca_probatoria_reu: str = Field(
        description="Avaliação objetiva do lastro probatório do réu neste ponto (ex: 'Mera Alegação Retórica' ou 'Não Impugnado')."
    )
    probabilidade_procedencia_pct: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Estimativa baseada no histórico do tema. Null se o histórico for insuficiente."
    )
    fundamentacao_preditiva: str = Field(
        description="Informa a base da estimativa ou quantos julgados comparáveis foram encontrados."
    )
    impacto_processual: str = Field(
        description="Orientação prática acionável em 1 frase para o advogado (ex: 'Requerer reconhecimento de fato incontroverso em réplica')."
    )
    pagina_autor: Optional[int] = Field(
        default=None,
        description="Número inteiro da página extraído da tag [PÁG XX] da Petição Inicial."
    )
    pagina_reu: Optional[int] = Field(
        default=None,
        description="Número inteiro da página extraído da tag [PÁG XX] da Contestação."
    )

class ResultadoComparacaoPecas(BaseModel):
    id_comparacao: str
    numero_processo: Optional[str] = None
    resumo_controvertido_geral: str = Field(
        description="Síntese executiva do litígio, principais pontos controvertidos e riscos processuais."
    )
    total_teses: int
    total_convergencias: int
    total_divergencias: int
    total_omissoes: int
    total_fatos_novos_defesa: int
    score_geral_favorabilidade_autor_pct: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Média das estimativas das teses, disponível quando todas têm base histórica."
    )
    motor_analise: Literal["gemini", "local"] = "local"
    teses: List[PontoControvertido]
    criado_em: datetime
```

---

## 5. Roteiro de Execução Passo a Passo (Fases)

Para garantir qualidade, estabilidade e conformidade com os testes automatizados, o desenvolvimento segue **4 etapas incrementais**:

### 🔹 Etapa 1: Backend, Pré-processador & Contratos de Dados (Fundação)
* Criar os schemas Pydantic atualizados em `backend/app/schemas/comparacao.py`.
* Implementar o pré-processador de PDF (`pdfplumber`/`PyMuPDF`) com injeção de marcadores `[PÁG XX]` e segmentação por macro-seções (`Fatos`, `Preliminares`, `Mérito`, `Tutela`, `Provas`, `Pedidos`).
* Criar o router `POST /api/v1/processos/comparar-pecas` aceitando dois uploads `multipart/form-data` (`peticao_inicial` e `contestacao`) com validação MIME e assinatura `%PDF-`.
* Integrar com o `AnonimizadorLGPD` para sanitização imediata de ambas as peças.
* Desenvolver testes automatizados em `pytest` cobrindo validações de entrada, erros `422` e resposta com mock estruturado.

### 🔹 Etapa 2: Motor de Extração Bidirecional e Confronto (IA / NLP)
* Estender o `AIProviderAdapter` com o método `comparar_pecas(texto_inicial, texto_contestacao)`.
* Configurar o prompt estruturado (*Juiz Saneador - art. 357 CPC*) com saída JSON conforme `responseJsonSchema`. O contrato externo `RespostaComparacaoGemini` contém a síntese e as teses extraídas.
  * **Varredura Direta (Autor $\rightarrow$ Réu):** Identifica convergências, divergências e omissões de impugnação específica (ignorando negativa geral) nos 7 eixos jurídicos.
  * **Varredura Reversa (Réu $\rightarrow$ Autor):** Captura fatos impeditivos, modificativos ou extintivos inéditos trazidos pela defesa (`fato_novo_ou_extintivo_reu`).
* Implementar o fallback local determinístico (`AI_PROVIDER=local`) baseado em Regex (datas `\d{2}/\d{2}/\d{4}`, valores monetários `R\$`, preliminares, prescrição, ônus da prova e pedidos) para execução 100% offline nos testes da suíte `pytest`.
* Gerar no backend os identificadores, a contagem das teses e as estimativas. Registrar `gemini` em `motor_analise` após validar a resposta externa e `local` quando a comparação vem do motor determinístico, inclusive em caso de indisponibilidade.

### 🔹 Etapa 3: Motor de Probabilidade de Procedência por Argumento
* Calcular a estimativa no backend para ambos os motores. Comparar o tema da tese com o tema dos julgados, normalizando maiúsculas, minúsculas e espaços.
* Considerar apenas processos cadastrados manualmente com desfecho **Procedente** ou **Improcedente**. Excluir da amostra o próprio processo comparado. O cadastro manual evita usar desfechos gerados automaticamente no fluxo de PDF ou preenchidos por padrão na importação CSV.
* Usar uma amostra mínima de **cinco julgados do mesmo tema**. Abaixo desse mínimo, retornar `null` em `probabilidade_procedencia_pct` e informar o tamanho da amostra em `fundamentacao_preditiva`.
* Quando houver histórico suficiente, calcular `100 × (julgados procedentes + 1) / (total de julgados + 2)`, com arredondamento para uma casa decimal. O percentual é uma referência histórica do tema. A classificação da tese, incluindo convergência, não altera o cálculo nem atribui êxito automático.
* Preencher `score_geral_favorabilidade_autor_pct` com a média das estimativas somente quando a comparação tiver teses e todas elas tiverem estimativa. Nos demais casos, retornar `null`.

### 🔹 Etapa 4: Interface de Comparação Lado a Lado (Frontend Split-View)
* Criar a nova visualização/aba na SPA: **"Comparador de Peças"**.
* Área de upload duplo com drag-and-drop para Petição Inicial e Contestação.
* Painel de visualização lado a lado (*Split-View*) em **3 colunas sincronizadas**:
  * **Coluna Esquerda:** Petição Inicial higienizada com navegação por página e *highlights*.
  * **Coluna Central:** Feed interativo de `PontoControvertido` com filtros por **Eixo Jurídico (`TipoTese`)** e **Status (`StatusTese`)**, rótulo da classificação, estimativa de êxito e alerta de `impacto_processual`. Exibir **Estimativa indisponível** sem barra percentual quando a API retornar `null`, acompanhada da justificativa.
  * **Coluna Direita:** Contestação higienizada com navegação por página e *highlights*.
* Ao clicar em um card central, ambas as colunas laterais rolam suavemente (`scrollIntoView`) até os respectivos trechos literais confrontados (`trecho_autor` e `trecho_reu`).
* Acessibilidade completa (**W3C WCAG 2.2 Nível AA**) com navegação por teclado e rótulos semânticos.
* No resumo, exibir **Gemini** ou **Análise local** conforme `motor_analise`. Mostrar a média das estimativas quando disponível e **Estimativa indisponível** nos demais casos.

#### Demonstração guiada

* Oferecer dois casos fictícios na aba **Comparador de Peças**. O cenário de atraso de voo permite conferir convergências sobre data e despesa, divergência sobre a assistência, omissão sobre o ônus da prova e a alegação de força maior. O cenário de cobrança após cancelamento permite confrontar data e valor e localizar a alegação de ilegitimidade passiva.
* Gerar uma petição inicial e uma contestação de três páginas por caso e enviar ambas pela rota `POST /api/v1/processos/comparar-pecas`. Usar o motor configurado na API e identificar o resultado com o caso e o CNJ fictício.
* Acompanhar o resultado com um guia por caso. Ao selecionar uma tese por clique ou teclado, indicar as páginas citadas e destacar os trechos disponíveis. Informar a quantidade de teses após combinar os filtros de status e eixo, sinalizar combinações vazias e reiniciar os filtros a cada nova comparação.
* Validar no navegador os dois cenários com o motor local, conferindo a extração das páginas, as citações, a navegação por teclado, os filtros combinados e o retorno ao fluxo de upload de peças próprias.

---

## 6. Governança e Salvaguardas do Projeto

1. **Custo Zero:** A chamada externa de LLM utilizará a camada gratuita da Google Gemini API (ou o motor local determinístico do JuriVision), garantindo aderência à diretriz orçamentária do projeto UFAL.
2. **Segurança e LGPD:** Nenhuma palavra de documento sem anonimização prévia chegará à camada de processamento de linguagem natural ou persistência.
3. **Não-Regressão:** A suíte existente de 11 testes automatizados continuará 100% verde durante e após todas as alterações.
