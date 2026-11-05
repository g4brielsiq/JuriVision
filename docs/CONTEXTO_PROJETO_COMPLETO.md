# JuriVision — Contexto Técnico, Arquitetural e Operacional Completo do Projeto

> **Instrução de Uso para o ChatGPT / LLM:**  
> Você está atuando como co-arquiteto de software, engenheiro sênior e consultor técnico do projeto **JuriVision**.  
> Este documento contém **todo o contexto histórico, normativo, arquitetural e o estado atual do repositório**. Utilize-o como fonte única da verdade para entender as decisões tomadas, a esteira de desenvolvimento, as restrições inegociáveis de governança (LGPD, normas ISO e WCAG) e como auxiliar a equipe na implementação dos próximos passos sem quebrar o ecossistema existente.

---

## 1. Visão Geral do Projeto e Contexto Acadêmico

### 1.1 Identificação
* **Nome do Sistema:** **JuriVision** (Plataforma de Pesquisa Jurisprudencial, Jurimetria e Análise Comparativa de Petições).
* **Instituição:** Universidade Federal de Alagoas (UFAL) — Instituto de Computação (IC).
* **Disciplina:** Gerência de Projetos (Prof. Rafael De Amorim Silva).
* **Equipe de Desenvolvimento:** **Equipe Epsilon** (8 integrantes organizados em 4 duplas com papéis delimitados por Matriz RACI):
  * **Dupla 1 — Front-end e UI/UX:** Emanuele Vitória e Lucas Gabriel (`frontend/`)
  * **Dupla 2 — Back-end e Arquitetura:** Victor Samyr e Gabriel Damião (`backend/`)
  * **Dupla 3 — Dados e Inteligência Artificial:** Pedro Henrique e Ygor Vasconcelos (`ai_engine/`)
  * **Dupla 4 — Gerência de Projetos e Requisitos:** Daniel Filipe e Fernando Gabriel (`docs/`, governança)
* **Regra Orçamentária:** A planilha orçamentária do projeto (R\$ 80.260,00 em `docs/MANAGEMENT.md`) é **estritamente hipotética** para fins de avaliação acadêmica de gestão de custos. **Nenhum gasto financeiro real é autorizado**. Toda a infraestrutura e recursos de IA devem ser capazes de rodar em modo local/gratuito.

### 1.2 O Problema de Negócio
Advogados e escritórios jurídicos enfrentam uma sobrecarga crítica com a leitura manual de petições extensas (geralmente PDFs de 40 a 100+ páginas), além da falta de previsibilidade estatística sobre o perfil decisório de magistrados em varas e comarcas específicas. O JuriVision resolve isso através de:
1. **Ingestão Híbrida:** Upload de peças em PDF (fluxo principal) e importação em lote via planilhas CSV.
2. **Barreira Local Obrigatória de Privacidade (LGPD):** Mascaramento determinístico de dados pessoais sensíveis (CPFs, RGs, nomes de partes civis) **antes** de qualquer persistência em banco ou envio a motores de inteligência artificial.
3. **Extração Documental e Síntese Factual (NLP):** Leitura de petições com geração de resumo factual do processo.
4. **Jurimetria Descritiva e Preditiva:** Cálculo transparente da taxa de procedência/deferimento por juiz, tempo médio de tramitação em meses e estimativa estatística de êxito para novas ações.
5. **Pesquisa Jurisprudencial e Biblioteca:** Consulta contextualizada por magistrado, comarca ou tema, visualização individual de leitura da decisão e exportação de relatórios analíticos em **PDF**.

---

## 2. Linha do Tempo: O que Passamos e Como Chegamos Aqui

### Fase 0 — O Scaffolding Inicial Preliminar (`main`)
* O repositório começou apenas com documentos de especificação (`ARCHITECTURE.md`, `docs/MANAGEMENT.md`, `docs/MODELING.md`), um esqueleto mínimo de pastas (`frontend/`, `backend/`, `ai_engine/`), um arquivo `index.html` estático de protótipo visual e um `docker-compose.yml` para 4 serviços.
* **Problemas e divergências da Fase 0:**
  * O `README.md` chamava o projeto de "JurisAI", enquanto o código usava "JuriVision".
  * Os diagramas em `docs/MODELING.md` descreviam uma fila assíncrona de mensagens (Redis/RabbitMQ) que não existia no `docker-compose.yml`.
  * O backend continha apenas uma rota de verificação (`/health`) e pastas vazias. Não havia banco relacional configurado nem regras de negócio.
  * O protótipo visual em `frontend/index.html` usava Tailwind via CDN e dados mockados com `setTimeout(3000)`, simulando o upload de arquivos sem comunicação real com a API.

### Fase 1 — Reengenharia e Implementação Core (`feat/backend-core-arquitetura`)
Liderada pelo integrante Victor Samyr (Dupla 2), esta etapa implementou de ponta a ponta a arquitetura de software, a modelagem de dados e a suíte de testes normativos:
1. **Registro de Decisões Arquiteturais (ADRs):**
   * **`ADR-001` (Eliminação da Fila Fantasma):** Comunicação síncrona HTTP/REST direta entre Backend e microsserviço de IA (porta interna `8001`), eliminando a dependência do Redis.
   * **`ADR-002` (Padrão Port & Adapter para IA):** O backend consome IA através da interface `AIProviderAdapter`. Por padrão, opera como `AI_PROVIDER=local` (motor heurístico/estatístico local determinístico), permitindo que todo o sistema funcione **100% offline e com custo zero** de APIs externas.
   * **`ADR-003` (Encapsulamento de Banco & Fallback SQLite):** Apenas o backend se conecta ao banco de dados relacional. Para evitar bloqueios em máquinas que não possuem o Docker Desktop instalado, o backend possui mecanismo de resiliência: se o PostgreSQL não estiver acessível, ele aciona automaticamente um banco local **SQLite (`jurivision_local.sqlite3`)** e semeia (*seed*) dados iniciais com 10 decisões do TJAL.
2. **Back-end Core Completo (FastAPI):**
   * Implementação de **8 endpoints REST oficiais** cobrindo autenticação JWT (`/api/v1/auth/login`), métricas jurimétricas (`/api/v1/dashboard/metricas`), upload de PDF (`/api/v1/processos/upload-pdf`), upload em lote de CSV (`/api/v1/processos/upload-csv`), busca e detalhes (`/api/v1/processos`) e exportação de relatório PDF (`/api/v1/relatorios/processo/{id}/pdf`).
   * Modelagem relacional via **SQLAlchemy 2.0**: tabelas `usuarios`, `processos`, `analises_ia` e `logs_auditoria_lgpd`.
   * **Barreira LGPD (`AnonimizadorLGPD`):** Anonimizador determinístico por Regex que higieniza documentos e gera hash criptográfico `SHA-256` para auditoria.
3. **Engenharia de UX/UI (*Legal Editorial + Legal Intelligence*):**
   * A interface do usuário foi reformulada para o padrão visual de LegalTechs institucionais (como Harvey AI e Linear): tipografia editorial sóbria (`Source Serif 4` + `Inter`), paleta clara institucional (azul profundo `#20364A`, marfim editorial `#F6F4EF`), foco no fluxo *"Pesquisa antes de Visualização"*, cartões documentais de decisão, visualizador de leitura de sentença e gráficos com **denominadores explícitos** (transparência metodológica).
   * **Acessibilidade estrita:** Adequação total às normas **W3C WCAG 2.2 Nível AA** e **WAI-ARIA 1.2** (navegação por teclado, rótulos semânticos, tabelas acessíveis para gráficos).
4. **Verificação Automatizada (ISO/IEC/IEEE 29119):**
   * Criação de 11 suítes de testes em `pytest` cobrindo fluxos de sucesso, erros `401`/`422`, integridade da barreira LGPD e acessibilidade do frontend.

### Fase 2 — Homologação e Isolamento da Branch de Desenvolvimento (Estado Atual)
* Criamos o ambiente virtual `.venv` no Python 3.12 local e executamos os testes automatizados: **11/11 testes aprovados (`100% passed`) em 9.14s**.
* Para seguir as boas práticas de Git-Flow e não comprometer nem a `main` nem a branch de entrega de arquitetura, criamos uma nova branch de trabalho:
  👉 **`feat/sprint1-integracao-dev`**
* Instituímos o diário de bordo contínuo em [`docs/CHANGELOG_EQUIPE.md`](./docs/CHANGELOG_EQUIPE.md).

---

## 3. Arquitetura de Software e Estrutura do Repositório

### 3.1 Estrutura de Pastas do Monorepo
```text
JuriVision/
├── .env                              # Configurações de ambiente local (ignorado pelo Git)
├── .env.example                      # Modelo com variáveis de exemplo
├── .gitignore                        # Regras de exclusão (.env, .venv, node_modules, caches)
├── ARCHITECTURE.md                   # Especificação técnica (ISO 42010, ADRs 001-003, MER/DER, Contratos REST)
├── README.md                         # Guia oficial de instalação, execução e testes
├── docker-compose.yml                # Orquestrador dos 4 serviços (frontend, backend, ai_engine, postgres)
├── docs/
│   ├── CHANGELOG_EQUIPE.md           # Diário de bordo contínuo para humanos e IAs
│   ├── COMPARATIVO_EVOLUCAO_ARQUITETURAL.md # Relatório comparativo (main vs branch evoluída)
│   ├── MANAGEMENT.md                 # Governança (RACI, EAP/WBS, Ishikawa, PDCA, PERT/EDA, EAR)
│   ├── MODELING.md                   # Requisitos Formais IRP (ISO 29148), UML 2.5 e Rastreabilidade
│   └── diagramas/                    # Diagramas estáticos compilados (.gitkeep)
├── frontend/
│   ├── index.html                    # Interface SPA Legal Editorial + Legal Intelligence (WCAG 2.2 AA)
│   ├── package.json                  # Dependências e scripts do frontend
│   ├── package-lock.json             # Travamento de versões npm
│   ├── Dockerfile                    # Container Node.js 20 Alpine
│   └── src/
│       ├── app.js                    # Controlador da interface, navegação de abas e gráficos Chart.js
│       ├── components/
│       │   └── design-tokens.css     # Design System editorial (variáveis de cor, tipografia e espaçamento)
│       ├── pages/                    # (.gitkeep para organização modular futura)
│       └── services/
│           └── api.js                # Cliente HTTP para integração com os endpoints FastAPI
├── backend/
│   ├── Dockerfile                    # Container Python 3.11-slim
│   ├── requirements.txt              # Dependências oficiais (FastAPI, SQLAlchemy, PyPDF, Pytest, etc.)
│   ├── app/
│   │   ├── main.py                   # Ponto de entrada FastAPI, CORS e inclusão de routers
│   │   ├── core/
│   │   │   ├── config.py             # Configurações centralizadas e leitura de variáveis de ambiente
│   │   │   ├── database.py           # Engine SQLAlchemy 2.0 com suporte a PostgreSQL e SQLite local
│   │   │   ├── security.py           # Hashing de senhas e geração/validação de tokens JWT
│   │   │   ├── ai_gateway.py         # Barreira LGPD, Extrator PDF/CSV e AIProviderAdapter (ADR-002)
│   │   │   └── seed.py               # População automática e idempotente de processos do TJAL
│   │   ├── models/
│   │   │   └── entities.py           # Modelos ORM: Usuario, Processo, AnaliseIA, LogAuditoriaLGPD
│   │   ├── schemas/
│   │   │   └── contracts.py          # Contratos Pydantic v2 (Login, Upload, Dashboard, Processos)
│   │   └── routers/
│   │       ├── auth.py               # POST /api/v1/auth/login
│   │       ├── dashboard.py          # GET /api/v1/dashboard/metricas
│   │       ├── processos.py          # Upload PDF/CSV, busca de processos e detalhe por ID
│   │       └── relatorios.py         # GET /api/v1/relatorios/processo/{id}/pdf (Stream PDF)
│   └── tests/
│       ├── conftest.py               # Fixtures de teste e client HTTP
│       ├── test_api_contracts.py     # Casos de teste CT-01 a CT-09 (API, LGPD, Upload, Relatório)
│       └── test_frontend_accessibility.py # Testes automatizados de WCAG 2.2 AA e WAI-ARIA 1.2
└── ai_engine/
    ├── Dockerfile                    # Container Python 3.11-slim
    ├── requirements.txt              # Dependências do worker
    ├── worker.py                     # Microsserviço de processamento inteligente (porta interna 8001)
    ├── pipelines/                    # Módulos para OCR, spaCy e NLP
    ├── models/                       # Modelos preditivos
    └── data/                         # Bases de teste mockadas
```

### 3.2 Diagrama de Fluxo de Dados e Segurança
```mermaid
flowchart TD
    User["Advogado / Navegador (Porta 5173)"] -->|1. Envia PDF/CSV ou Requisita Dados| API["FastAPI Gateway (Porta 8000)"]
    API -->|2. Validação de Token JWT| Security["Módulo de Segurança (security.py)"]
    API -->|3. Fluxo de Ingestão de Documento| Extrator["ExtratorDocumental (PyPDF / CSV)"]
    Extrator -->|Texto Bruto| LGPD["Barreira Local Obrigatória LGPD (AnonimizadorLGPD)"]
    LGPD -->|Gera Hash SHA-256 e Log de Auditoria| AuditDB[("Tabela logs_auditoria_lgpd")]
    LGPD -->|Texto Higienizado sem CPFs/Nomes| Adapter["AIProviderAdapter (ADR-002)"]
    Adapter -->|Modo Local Determinístico| LocalAI["LocalDeterministicFallbackAdapter"]
    Adapter -.->|Modo Remoto (Opcional)| RemoteAI["AI Engine HTTP :8001 / LLM Externa"]
    LocalAI -->|Gera Resumo NLP e Score Jurimétrico| API
    API -->|4. Persiste Processo Higienizado| DB[("Banco Relacional (PostgreSQL ou SQLite)")]
    API -->|5. Retorna JSON ou Stream de PDF| User
```

---

## 4. Requisitos do Sistema e Contratos da API

### 4.1 Requisitos Funcionais (IRP — `docs/MODELING.md`)
* **`RF-01` — Autenticação e Gestão de Sessão:** Login via `POST /api/v1/auth/login` com emissão de token JWT Bearer.
* **`RF-02` — Ingestão de Petições em PDF:** Upload multipart de PDF (`POST /api/v1/processos/upload-pdf`), validação de cabeçalho binário `%PDF-` e extração de texto.
* **`RF-03` — Ingestão em Lote via CSV:** Upload de CSV estruturado (`POST /api/v1/processos/upload-csv`).
* **`RF-04` — Barreira de Anonimização LGPD (`RN-01`):** Mascaramento de dados sensíveis antes de qualquer armazenamento ou envio à IA.
* **`RF-05` — Síntese Factual Automatizada:** Extração de tema, partes anonimizadas e resumo dos fatos.
* **`RF-06` — Análise Estatística e Predição Jurídica:** Cálculo de probabilidade de êxito e estimativa de tempo até sentença baseado no histórico do magistrado.
* **`RF-07` — Dashboard Analítico de Jurimetria:** `GET /api/v1/dashboard/metricas` com taxa global de êxito, tempo médio e agrupamento por juiz e por tema.
* **`RF-08` — Consulta Jurisprudencial e Filtros:** `GET /api/v1/processos` com filtros por tema, magistrado, resultado e busca textual.
* **`RF-09` — Exportação de Relatórios Estratégicos:** `GET /api/v1/relatorios/processo/{id}/pdf` gerando relatório binário em PDF para download.

### 4.2 Credenciais Padrão de Teste (Seed)
* **E-mail:** `advogado@escritorio.com`
* **Senha:** `senhaSegura123`
* **Advogado associado:** Dr. Lucas Gabriel (OAB 12345/AL)

---

## 5. Como Executar o Projeto Localmente

### Opção A — Execução Direta Local (Sem Docker, com Fallback SQLite)
Esta é a forma mais rápida e recomendada para desenvolvimento:

1. **Ativar o ambiente virtual e rodar os testes:**
   ```powershell
   # No Windows (PowerShell):
   $env:PYTHONPATH="backend"; .venv\Scripts\pytest backend/tests/ -v
   ```
2. **Iniciar o Back-end (FastAPI):**
   ```powershell
   .venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --port 8000
   ```
   > Documentação interativa Swagger: **`http://localhost:8000/docs`**
3. **Iniciar o Front-end (Vite):**
   ```powershell
   cd frontend
   npm run dev
   ```
   > Plataforma acessível em: **`http://localhost:5173`**

### Opção B — Execução Orquestrada via Docker Compose
Se o Docker Desktop estiver instalado e ativo:
```bash
docker compose up --build
```
> Sobe os 4 contêineres: Frontend (`:5173`), Backend (`:8000`), AI Engine (`:8001`) e PostgreSQL (`:5432`).

---

## 6. Diretrizes e Regras Inegociáveis para o ChatGPT

Ao sugerir código, arquitetar novas funcionalidades ou auxiliar na refatoração:

1. 🛡️ **Preserve o Invariante Crítico da LGPD (`RN-01`):**  
   Sob nenhuma hipótese permita que textos contendo CPFs, RGs ou nomes de partes reais sejam salvos diretamente no banco ou enviados a qualquer provedor de IA. O processamento deve obrigatoriamente transitar pelo `AnonimizadorLGPD` (`backend/app/core/ai_gateway.py`).
2. 🔄 **Respeite o Suporte Híbrido a Banco de Dados (`ADR-003`):**  
   O backend precisa continuar funcionando tanto com PostgreSQL quanto com SQLite local. Não introduza dialetos SQL ou tipos proprietários que quebrem o SQLite no ambiente de desenvolvimento local.
3. 🤖 **Mantenha o Fallback Local de IA (`ADR-002`):**  
   Não obrigue o uso de chaves pagas de APIs externas (Gemini/OpenAI). O sistema deve funcionar perfeitamente com `AI_PROVIDER=local` para manter a conformidade com a regra de custo financeiro zero da disciplina acadêmica.
4. 🎨 **Respeite a Direção de Arte *Legal Editorial* e Acessibilidade:**  
   Não reintroduza Tailwind via CDN nem bibliotecas de ícones pesadas no frontend. Mantenha os tokens de design do arquivo `design-tokens.css` (`Source Serif 4` + `Inter`, paleta sóbria institucional) e garanta que qualquer novo componente cumpra rigorosamente a norma **WCAG 2.2 Nível AA** (labels semânticos, contraste adequado e navegação completa por teclado).
5. 📝 **Mantenha o Diário de Bordo Atualizado:**  
   Sempre oriente o desenvolvedor a registrar implementações relevantes no arquivo [`docs/CHANGELOG_EQUIPE.md`](./docs/CHANGELOG_EQUIPE.md), informando requisitos atendidos, comandos para teste e orientações para os assistentes de IA dos demais colegas.
6. 🌿 **Política de Branches (Git-Flow):**  
   Nunca sugira commits diretos na `main`. A branch de trabalho atual é a **`feat/sprint1-integracao-dev`**.
