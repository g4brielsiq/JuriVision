# JuriVision — Contexto Técnico, Arquitetura e Estado Atual do Projeto

> **Instruções para o ChatGPT:**  
> Você está atuando como Arquiteto de Software, Engenheiro Full-Stack e Consultor Técnico da **Equipe Epsilon** no projeto acadêmico **JuriVision**. Leia atentamente este documento para compreender integralmente o domínio do problema, a arquitetura de software, as decisões arquiteturais (ADRs), o estado atual do repositório, as branches ativas e os invariantes de conformidade (LGPD). Utilize este contexto como a fonte da verdade para orientar, auditar e gerar código nas próximas interações.

---

## 1. Identificação do Projeto e Contexto Acadêmico

* **Nome Oficial:** JuriVision — Plataforma de Pesquisa Jurisprudencial, Jurimetria e Análise Comparativa de Petições.
* **Disciplina:** Gerência de Projetos (Prof. Rafael De Amorim Silva).
* **Instituição:** Universidade Federal de Alagoas (UFAL) — Instituto de Computação (IC).
* **Equipe de Desenvolvimento (Equipe Epsilon — 8 integrantes em 4 duplas):**
  * **Dupla 1 (Front-end e UI/UX):** Emanuele Vitória e Lucas Gabriel
  * **Dupla 2 (Back-end e Arquitetura):** Victor Samyr e Gabriel Damião
  * **Dupla 3 (Dados e Inteligência Artificial):** Pedro Henrique e Ygor Vasconcelos
  * **Dupla 4 (Gerência de Projetos e Requisitos):** Daniel Filipe e Fernando Gabriel
* **Política de Custos:** **Projeto acadêmico com custo financeiro real ZERO**. Qualquer valor orçamentário presente na documentação de governança (`docs/MANAGEMENT.md`) é puramente hipotético para fins pedagógicos. O software deve ser capaz de rodar 100% localmente sem consumo de APIs pagas.

---

## 2. Visão do Produto e Problema de Negócio

### O Problema
Escritórios de advocacia perdem centenas de horas na triagem manual de petições extensas em PDF, enfrentam dificuldades para cruzar jurisprudência e muitas vezes tomam decisões estratégicas baseadas em intuição, sem dados estatísticos objetivos sobre o histórico decisório de juízes e varas.

### A Solução (JuriVision)
Uma plataforma web *LegalTech* que:
1. **Ingere documentos:** Suporta upload de petições iniciais em **PDF** (via `pdfplumber`) e importação em lote via planilhas **CSV**.
2. **Higieniza dados sob a LGPD:** Aplica barreira local determinística para mascarar dados sensíveis de pessoas físicas (CPFs, RGs e nomes) antes de qualquer persistência ou análise.
3. **Extrai fatos e sintetiza:** Gera resumos fáticos estruturados da lide.
4. **Calcula métricas de Jurimetria:** Taxa histórica de deferimento por magistrado, tempo médio de tramitação e projeções comparativas com denominadores transparentes.
5. **Apresenta dados em interface jurídica editorial:** Design sóbrio com pesquisa jurisprudencial em destaque, cartões de leitura de decisão e exportação de relatórios em **PDF**.

---

## 3. Decisões Arquiteturais Formais (ADRs)

A evolução do projeto é regida por 3 Decisões Arquiteturais formais consolidadas no `ARCHITECTURE.md`:

* **`ADR-001` — Comunicação Direta Síncrona HTTP/REST entre Serviços:**
  * *Contexto:* Diagramas conceituais antigos citavam filas assíncronas (Redis/RabbitMQ), o que aumentava a complexidade operacional desnecessariamente.
  * *Decisão:* Comunicação direta via HTTP/REST entre o Backend API Gateway (`:8000`) e o Microsserviço de IA (`ai_engine:8001`) na rede interna Docker, eliminando filas intermediárias.
* **`ADR-002` — Padrão *Port & Adapter* com Fallback Local Determinístico:**
  * *Contexto:* Dependência de chaves de LLMs externas (OpenAI/Gemini) violaria a política de custo zero e causaria falhas em ambientes offline.
  * *Decisão:* O Backend utiliza a interface `AIProviderAdapter`. Por padrão, executa o modo `AI_PROVIDER=local` (motor heurístico/estatístico determinístico local). O suporte a microsserviço ou LLMs externas é plugável sem alterar o núcleo da API.
* **`ADR-003` — Encapsulamento de Persistência e Portabilidade Relacional (PostgreSQL + SQLite):**
  * *Contexto:* Nem todos os desenvolvedores possuem Docker ou PostgreSQL configurados na máquina local.
  * *Decisão:* Apenas o Backend conecta-se ao banco de dados relacional. A aplicação possui resiliência automática: se o PostgreSQL (Docker) não estiver disponível, o backend ativa automaticamente o fallback em **SQLite local (`jurivision_local.sqlite3`)** com *seed* idempotente de dados iniciais.

---

## 4. Estado Real de Implementação

O projeto superou a fase de *scaffolding* e possui uma **aplicação funcional de ponta a ponta** já testada e homologada:

### Back-end API Core (Python 3.11+ / FastAPI / SQLAlchemy 2.0 / Pydantic v2)
* **Endpoints Implementados e Ativos:**
  * `POST /api/v1/auth/login`: Autenticação do advogado com retorno de token JWT e perfil OAB.
  * `GET /api/v1/dashboard/metricas`: Métricas agregadas de jurimetria, taxas de êxito e volume por tema.
  * `GET /api/v1/processos`: Consulta paginada com busca textual e filtros dinâmicos por tema, magistrado e resultado.
  * `GET /api/v1/processos/{id}`: Detalhe completo de um processo higienizado e sua análise.
  * `POST /api/v1/processos/upload-pdf`: Upload multipart de petição PDF, validação binária `%PDF-`, extração, anonimização LGPD e inferência heurística.
  * `POST /api/v1/processos/upload-csv`: Ingestão em lote de decisões em planilha CSV.
  * `GET /api/v1/relatorios/processo/{id}/pdf`: Geração dinâmica de relatório analítico em stream binário `application/pdf`.
  * `GET /health`: Verificação de saúde da API.
* **Modelo Entidade-Relacionamento (ORM):** 4 tabelas relacionais implementadas (`usuarios`, `processos`, `analises_ia`, `logs_auditoria_lgpd`).
* **Seed Automático:** Banco pré-populado com usuário de teste (`advogado@escritorio.com` / `senhaSegura123`) e 10 processos realistas do Tribunal de Justiça de Alagoas (TJAL).

### Front-end Web (HTML5 Semântico / CSS Design Tokens / ES Modules / Chart.js)
* **Direção Visual:** *Legal Editorial + Legal Intelligence* (paleta em Azul Profundo `#20364A`, Marfim `#F6F4EF`, tipografia `Source Serif 4` + `Inter`). Zero dependência de Tailwind CDN ou FontAwesome.
* **Componentes Principais:**
  * Câmara de Pesquisa de Precedentes e Jurisprudência em primeiro plano.
  * Cartões Documentais de Decisão e visualização alternativa em Tabela Comparativa.
  * Folha Individual de Leitura de Decisão (largura ideal de 65–75 caracteres).
  * Painel de Análise Jurimétrica com gráficos (Chart.js) contendo denominadores explícitos e filtros interativos por clique.
  * Modal acessível de Análise de Petição (Dropzone nativa acessível para PDF/CSV).
* **Acessibilidade e Usabilidade:** 100% aderente a **W3C WCAG 2.2 Nível AA** e **WAI-ARIA 1.2** (navegação por teclado com setas nas abas, contraste certificado, tabelas acessíveis ocultas para leitores de tela em cada gráfico).

### Suíte de Testes Automatizados (ISO/IEC/IEEE 29119)
* **Status:** **11 testes automatizados em Pytest — 100% de aprovação (11 passed)**.
* **Cobertura:**
  * Casos de Teste `CT-01` a `CT-09` (Autenticação JWT, Upload PDF, Injeção CSV, Barreira LGPD, Métricas, Filtros, Relatório PDF).
  * Verificações de acessibilidade e design tokens (`RNF-04`, `RNF-09`, `RNF-10`).

---

## 5. Invariantes Críticos e Regras de Segurança

1. **Barreira Local LGPD (`RN-01`):** É expressamente proibido persistir no banco ou enviar a qualquer serviço externo de IA textos contendo CPFs, RGs ou nomes de partes civis sem passar pelo `AnonimizadorLGPD` (`backend/app/core/ai_gateway.py`). O mascaramento gera um hash `SHA-256` auditado.
2. **Arquivos Protegidos:** O repositório possui arquivos de especificação de baseline (`ARCHITECTURE.md`, `docs/MANAGEMENT.md`, `docs/MODELING.md`). Nenhuma modificação neles deve ser feita sem alinhamento prévio.
3. **Privacidade por Design:** Não criar rotas que exponham dados brutos ou contornem a autenticação JWT.

---

## 6. Estrutura de Branches e Versionamento (Git-Flow)

* **`main`:** Branch raiz / baseline original estável. **Protegida contra commits diretos.**
* **`feat/backend-core-arquitetura`:** Branch onde o colega Victor Samyr consolidou a evolução do backend, testes e reengenharia de UX/UI.
* **`feat/sprint1-integracao-dev` (BRANCH ATIVA ATUAL):** Branch de trabalho atual criada para as novas implementações da equipe, garantindo rastreabilidade e segurança.
* **Registro de Mudanças:** O arquivo [`docs/CHANGELOG_EQUIPE.md`](./docs/CHANGELOG_EQUIPE.md) é o diário oficial onde cada entrega é documentada para os desenvolvedores e seus assistentes de IA.

---

## 7. Como Executar e Testar o Projeto no Ambiente Local

### Pré-requisitos
* Python 3.11 ou superior
* Node.js 18 ou superior

### Passo a Passo

```powershell
# 1. Executar os 11 testes automatizados (PowerShell)
$env:PYTHONPATH="backend"; .venv\Scripts\pytest backend/tests/ -v

# 2. Iniciar a API Backend (FastAPI com fallback automático em SQLite)
.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --port 8000
# -> Documentação Swagger: http://localhost:8000/docs

# 3. Iniciar a Interface Frontend (em outro terminal)
cd frontend
npm run dev
# -> Aplicação Web: http://localhost:5173
```

* **Credenciais padrão para login:**
  * **E-mail:** `advogado@escritorio.com`
  * **Senha:** `senhaSegura123`

---

## 8. Diretrizes para Você (ChatGPT) ao Apoiar Este Projeto

Quando o usuário solicitar código, refatoração, análises ou documentação:
1. **Respeite o Design System Oficial:** Não proponha bibliotecas genéricas (Tailwind via CDN, Bootstrap, FontAwesome). Use os design tokens existentes em `frontend/src/components/design-tokens.css`.
2. **Mantenha a Compatibilidade Dual (PostgreSQL + SQLite):** Código SQLAlchemy deve funcionar perfeitamente em ambos os dialetos.
3. **Preserve a Barreira LGPD:** Toda lógica que manipule petições deve respeitar a ordem: *Upload $\rightarrow$ Extração $\rightarrow$ Anonimização LGPD $\rightarrow$ Predição/Persistência*.
4. **Documente Sempre:** Ao propor uma nova feature, formate a explicação técnica de modo a alimentar o `docs/CHANGELOG_EQUIPE.md` seguindo o padrão da equipe.
5. **Seja Fiel aos Padrões ISO e WCAG:** Mantenha acessibilidade semântica e contratos REST explícitos.
