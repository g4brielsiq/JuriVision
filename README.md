# JuriVision — Plataforma Analítica e Preditiva de Jurimetria

> **Projeto Acadêmico Avaliativo — Disciplina de Gerência de Projetos (Prof. Rafael De Amorim Silva)**  
> **Universidade Federal de Alagoas (UFAL) — Instituto de Computação (IC) — Equipe Epsilon**

O **JuriVision** é uma plataforma de jurimetria preditiva e organização processual projetada para escritórios de advocacia e departamentos jurídicos. O sistema automatiza a ingestão de petições em PDF e planilhas CSV, aplica anonimização determinística local em conformidade com a **LGPD**, gera resumos executivos factuais via **NLP** e calcula indicadores estatísticos de probabilidade de êxito, tempo médio de tramitação e perfil decisório de magistrados.

---

## 1. Documentação de Engenharia e Governança (Baseline Normativa)

Toda a engenharia do projeto segue os padrões **ISO/IEC/IEEE 12207**, **ISO/IEC/IEEE 29148**, **ISO/IEC/IEEE 42010**, **ISO/IEC 25010 (SQuaRE)**, **UML 2.5 (OMG)**, **ISO/IEC/IEEE 29119** e **CMMI-DEV / MPS.BR**:

* **[ARCHITECTURE.md](./ARCHITECTURE.md):** Especificação arquitetural completa, Stakeholders e Preocupações (*ISO 42010*), Registro de Decisões Arquiteturais (`ADR-001`, `ADR-002`, `ADR-003`), Diagrama de Componentes, Diagrama de Implantação, Modelo Entidade-Relacionamento (`MER/DER`) e Contratos Oficiais de API REST.
* **[docs/MODELING.md](./docs/MODELING.md):** Especificação Formal de Requisitos (`IRP` — `RF-01` a `RF-09`, `RNF-01` a `RNF-08` mapeados na `ISO/IEC 25010` e Regras de Negócio `RN-01` a `RN-04`), Diagramas Comportamentais em **UML 2.5** (Casos de Uso, Atividades, Sequência e Estados) e **Matriz de Rastreabilidade Bidirecional (CMMI REQM / MPS.BR)**.
* **[docs/MANAGEMENT.md](./docs/MANAGEMENT.md):** Plano de Gestão, Governança e Controle do Projeto (Matriz RACI das 4 duplas, EAP/WBS, Gestão da Qualidade com Ishikawa/DoD/PDCA, Gestão de Riscos com EAR, Aquisições *Make or Buy*, Estimativas PERT/EDA e Quadro Orçamentário).
* **[agent.md](./agent.md):** Diretrizes de Auditoria de Qualidade e Engenharia de Software.

---

## 2. Arquitetura do Monorepo

O sistema é estruturado em 4 serviços orquestrados via Docker Compose:

| Serviço / Diretório | Tecnologia Principal | Porta | Responsabilidade |
| :--- | :--- | :---: | :--- |
| **[`frontend/`](./frontend)** | React 18, Vite, Tailwind CSS, Chart.js | `5173` | Interface web analítica (Dashboard de Jurimetria, Upload de PDF/CSV, Base de Conhecimento e Relatórios). |
| **[`backend/`](./backend)** | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0 | `8000` | API Core & Gateway REST, autenticação JWT, orquestração de negócios, persistência relacional e geração de relatórios em PDF. |
| **[`ai_engine/`](./ai_engine)** | Python 3.11, `pdfplumber`, Motor LGPD Local, `AIProviderAdapter` | `8001` *(interna)* | Microsserviço isolado de extração documental, anonimização obrigatória LGPD e inteligência híbrida (Modelo Estatístico/Heurístico Local com suporte plugável a APIs externas de LLM como Gemini / OpenAI GPT). |
| **`postgres`** | PostgreSQL 16 Alpine | `5432` | Persistência relacional de usuários, processos higienizados, análises preditivas e logs de auditoria LGPD. |

---

## 3. Como Executar o Projeto (Docker Compose)

### 3.1 Pré-requisitos
* **Docker** e **Docker Compose** instalados.

### 3.2 Configuração de Variáveis de Ambiente
Copie o arquivo de exemplo [`.env.example`](./.env.example) para `.env` na raiz do repositório:

```bash
cp .env.example .env
```

> **Nota sobre o Motor de IA (`AI_PROVIDER`):** Por padrão, o sistema opera com `AI_PROVIDER=local` (modelo heurístico/estatístico embutido, sem necessidade de chaves externas ou GPU). Para habilitar o enriquecimento via LLM externo (sempre após a anonimização local LGPD), configure `AI_PROVIDER=gemini` (com `GEMINI_API_KEY`) ou `AI_PROVIDER=openai` (com `OPENAI_API_KEY`).

### 3.3 Inicialização dos Containers

```bash
docker compose up --build
```

* **Interface Web (`frontend`):** `http://localhost:5173`
* **API Core & Documentação OpenAPI/Swagger (`backend`):** `http://localhost:8000/docs`
* **Healthcheck da API (`backend`):** `http://localhost:8000/health`

---

## 4. Equipe Epsilon (UFAL)

* **Dupla 1 (Front-end e UI/UX):** Emanuele Vitória e Lucas Gabriel
* **Dupla 2 (Back-end e Arquitetura):** Victor Samyr e Gabriel Damião
* **Dupla 3 (Dados e Inteligência Artificial):** Pedro Henrique e Ygor Vasconcelos
* **Dupla 4 (Gerência de Projetos e Requisitos):** Daniel Filipe e Fernando Gabriel

---

## 5. Licença

Distribuído sob a licença MIT. Veja [LICENSE](./LICENSE) para mais informações.

