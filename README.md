# JuriVision — Plataforma de Pesquisa Jurisprudencial e Jurimetria para Advocacia

> **Projeto Acadêmico Avaliativo — Disciplina de Gerência de Projetos (Prof. Rafael De Amorim Silva)**  
> **Universidade Federal de Alagoas (UFAL) — Instituto de Computação (IC) — Equipe Epsilon**

O **JuriVision** é uma plataforma de pesquisa jurisprudencial, jurimetria e análise comparativa de petições projetada para advogados, escritórios de advocacia e equipes jurídicas. O sistema organiza decisões judiciais com metadados estruturados, aplica higienização determinística local em conformidade com a **LGPD**, extrai sínteses factuais e apresenta indicadores jurimétricos com transparência metodológica, denominadores explícitos e exportação de relatórios analíticos em **PDF**.

---

## 📌 Destaque: Relatório Comparativo de Evolução (Versão Inicial vs. Versão Evoluída)

Para consultar um mapeamento completo de todas as mudanças arquiteturais (`ADR-001` a `ADR-003`), correções de modelagem `UML 2.5`, implementação do Back-end Core, isolamento da IA, testes automatizados (`pytest`) e reformulação de UX/UI (*Legal Editorial + Legal Intelligence*), acesse diretamente:

👉 **[`docs/COMPARATIVO_EVOLUCAO_ARQUITETURAL.md`](./docs/COMPARATIVO_EVOLUCAO_ARQUITETURAL.md)** — *Relatório Técnico Comparativo de Evolução Arquitetural, Funcional e de UX/UI (`main` vs. `feat/backend-core-arquitetura`)*

---

## 1. Documentação de Engenharia e Governança (Baseline Normativa)

Toda a engenharia do projeto segue os padrões **ISO/IEC/IEEE 12207**, **ISO/IEC/IEEE 29148**, **ISO/IEC/IEEE 42010**, **ISO/IEC 25010 (SQuaRE)**, **UML 2.5 (OMG)**, **ISO 9241**, **W3C WCAG 2.2 AA**, **ISO/IEC/IEEE 29119** e **CMMI-DEV / MPS.BR**:

* **[docs/COMPARATIVO_EVOLUCAO_ARQUITETURAL.md](./docs/COMPARATIVO_EVOLUCAO_ARQUITETURAL.md):** Comparativo executivo e técnico detalhando tudo o que evoluiu entre a versão inicial do repositório e a versão atual certificada.
* **[ARCHITECTURE.md](./ARCHITECTURE.md):** Especificação arquitetural completa, Stakeholders e Preocupações (*ISO 42010*), Registro de Decisões Arquiteturais (`ADR-001`, `ADR-002`, `ADR-003`), Diagrama de Componentes, Diagrama de Implantação, Modelo Entidade-Relacionamento (`MER/DER`) e Contratos Oficiais de API REST.
* **[docs/MODELING.md](./docs/MODELING.md):** Especificação Formal de Requisitos (`IRP` — `RF-01` a `RF-09`, `RNF-01` a `RNF-10` mapeados na `ISO/IEC 25010`, `ISO 9241` e `WCAG 2.2 AA`, Regras de Negócio `RN-01` a `RN-04` e Seção 2.4 de Engenharia de UX/UI), Diagramas Comportamentais em **UML 2.5** (Casos de Uso, Atividades, Sequência e Estados) e **Matriz de Rastreabilidade Bidirecional (CMMI REQM / MPS.BR)**.
* **[docs/MANAGEMENT.md](./docs/MANAGEMENT.md):** Plano de Gestão, Governança e Controle do Projeto (Matriz RACI das 4 duplas, EAP/WBS, Gestão da Qualidade com Ishikawa/DoD/PDCA, Gestão de Riscos com EAR, Aquisições *Make or Buy*, Estimativas PERT/EDA e Quadro Orçamentário).
* **[agent.md](./agent.md):** Diretrizes de Auditoria de Qualidade, Engenharia de Software e Direção Visual (*Legal Editorial + Legal Intelligence*).

---

## 2. Arquitetura do Monorepo

O sistema é estruturado em 4 serviços orquestrados via Docker Compose:

| Serviço / Diretório | Tecnologia Principal | Porta | Responsabilidade |
| :--- | :--- | :---: | :--- |
| **[`frontend/`](./frontend)** | HTML5 Semântico (`WAI-ARIA 1.2`), Design System CSS (`WCAG 2.2 AA`), ES Modules, Chart.js | `5173` | Interface web (Landing Page, Pesquisa de Precedentes + DataJud, Leitura Documental, Análise Jurimétrica, Análise de Petição PDF/CSV, Comparador de Peças e fluxo Freemium `FREE`/`PRO`). |
| **[`backend/`](./backend)** | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0, `pdfplumber` | `8000` | API Core & Gateway REST, autenticação JWT multiusuário, barreira local LGPD (`AnonimizadorLGPD`), motor NLP/RAG (`TF-IDF` + `Okapi BM25`), integração DataJud (CNJ), Comparador de Peças e relatórios PDF. |
| **[`ai_engine/`](./ai_engine)** | Python 3.11+, Motor Estatístico/Heurístico Local, `AIProviderAdapter` | `8001` *(interna)* | Microsserviço isolado de inteligência híbrida (opcional via `AI_PROVIDER=external`; por padrão o back-end opera com o motor determinístico local ou com Google Gemini via `AI_PROVIDER=auto`). |
| **`postgres`** | PostgreSQL 16 Alpine | `5432` | Persistência relacional de usuários, processos higienizados, análises preditivas e logs de auditoria LGPD. |

---

## 3. Como Executar o Projeto e Rodar os Testes

### 3.1 Pré-requisitos
Para executar o projeto em ambiente local de desenvolvimento, são necessários:
* **Python 3.11+** (com gerenciador `pip`)
* **Node.js 18+** e **npm**
* *(Opcional)* **Docker e Docker Compose** (caso prefira rodar os containers isolados com PostgreSQL)

---

### 3.2 Execução Local Direta (Recomendada / Sem Docker)

Esta modalidade executa o **Back-end** e o **Front-end** diretamente no seu sistema operacional. O Back-end possui mecanismo de resiliência e portabilidade (*ADR-003*): se o PostgreSQL não estiver ativo, ele aciona automaticamente o fallback em banco relacional local **SQLite** (`jurivision_local.sqlite3`) e inicia com a base limpa (`SEED_DEMO_DATA=false` por padrão), pronta para receber dados reais via **DataJud (CNJ)**, cadastro manual, CSV ou upload de PDFs. Caso deseje iniciar um ambiente vazio com os dados demonstrativos, defina `SEED_DEMO_DATA=true` no arquivo `.env`.

#### Passo 1: Instalar as Dependências

Abra o terminal na raiz do projeto (`JuriVision/`):

```bash
# 1. Dependências do Back-end (Python)
pip install -r backend/requirements.txt

# 2. Dependências do Front-end (Node.js)
cd frontend
npm install
cd ..
```

#### Passo 2: Iniciar a API Core (Back-end)

Em um terminal na raiz do projeto:

* **No Windows (PowerShell):**
  ```powershell
  python -m uvicorn app.main:app --app-dir backend --reload --port 8000
  ```
* **No Linux / macOS (Bash):**
  ```bash
  uvicorn app.main:app --app-dir backend --reload --port 8000
  ```

> O Back-end estará disponível em: `http://localhost:8000`  
> Documentação interativa Swagger: `http://localhost:8000/docs`

#### Passo 3: Iniciar a Interface Web (Front-end)

Em um segundo terminal:

```bash
cd frontend
npm run dev
```

> A interface estará disponível no navegador em: **`http://localhost:5173`**

---

### 3.3 Execução via Docker Compose (Todos os Serviços Orquestrados)

Caso possua o Docker e Docker Compose instalados e deseje subir o ecossistema completo (Frontend + Backend + PostgreSQL 16 Alpine + AI Engine):

1. Crie o arquivo `.env` a partir do modelo:
   * **Linux / macOS:** `cp .env.example .env`
   * **Windows (PowerShell):** `Copy-Item .env.example .env`
2. Construa as imagens e suba os containers:
   ```bash
   docker compose up --build
   ```

---

### 3.4 Credenciais de Acesso e Modo Demonstração (`SEED_DEMO_DATA`)

Por padrão (`SEED_DEMO_DATA=false`), a plataforma inicia sem usuários pré-cadastrados para que cada advogado crie sua própria conta em **Criar conta** (iniciando no plano `FREE` com 3 análises gratuitas de PDF, podendo alternar para `PRO` no modal de assinatura) ou navegue livremente como visitante.

Caso habilite `SEED_DEMO_DATA=true` no `.env` em um banco vazio, o startup cria 10 julgados demonstrativos e a seguinte conta institucional de teste (plano `PRO`):

| Campo | Valor Padrão |
| :--- | :--- |
| **E-mail** | `advogado@escritorio.com` |
| **Senha** | `senhaSegura123` |
| **Advogado** | Lucas Gabriel |
| **Inscrição OAB** | `12345/AL` |

---

### 3.5 Verificação e Testes Automatizados (`pytest` — ISO/IEC/IEEE 29119)

Para rodar os **150 casos de teste automatizados** (contratos de API REST, saneamento de dados presumidos, integração DataJud/Gemini, segurança JWT multiusuário, barreira LGPD expandida, motor NLP/BM25, RAG, Freemium/Cloud, Comparador de Peças, OCR/seções e conformidade WCAG 2.2 AA / WAI-ARIA — executados em SQLite temporário isolado pelo `conftest.py`):

* **No Windows (PowerShell):**
  ```powershell
  cd backend ; python -m pytest -v
  ```
* **No Linux / macOS (Bash):**
  ```bash
  cd backend && pytest -v
  ```

---

### 3.6 Cadastro e edição de julgados

1. Em **Pesquisa de precedentes**, clique em **Cadastrar julgado** e informe o número CNJ, o assunto, o magistrado, as partes e a ementa ou síntese. O órgão julgador e a data do julgamento são opcionais.
2. Confira a **Prévia de anonimização** enquanto preenche os campos. O servidor aplica às partes e à síntese a mesma rotina usada no salvamento, sem gravar o rascunho.
3. Clique em **Salvar julgado**. Para alterar um registro, abra a decisão na pesquisa e clique em **Editar julgado**. O formulário recupera os dados salvos, incluindo o resultado e a data, e atualiza a prévia ao alterar as partes ou a síntese.

A prévia deve mascarar o nome da autora e o CPF, preservando a razão social da ré. O contrato das rotas está na seção 8.5.1 da [documentação de arquitetura](./ARCHITECTURE.md#851-cadastro-e-edição-manual-de-processos-rf-08-rn-01).

## 4. Equipe Epsilon (UFAL)

* **Dupla 1 (Front-end e UI/UX):** Emanuele Vitória e Lucas Gabriel
* **Dupla 2 (Back-end e Arquitetura):** Victor Samyr e Gabriel Damião
* **Dupla 3 (Dados e Inteligência Artificial):** Pedro Henrique e Ygor Vasconcelos
* **Dupla 4 (Gerência de Projetos e Requisitos):** Daniel Filipe e Fernando Gabriel

---

## 5. Licença

Distribuído sob a licença MIT. Veja [LICENSE](./LICENSE) para mais informações.
