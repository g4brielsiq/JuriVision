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
| **[`frontend/`](./frontend)** | HTML5 Semântico (`WAI-ARIA 1.2`), Design System CSS (`WCAG 2.2 AA`), ES Modules, Chart.js | `5173` | Interface web *Legal Editorial + Legal Intelligence* (Pesquisa Jurisprudencial, Cartões Documentais, Leitura de Decisão, Análise Jurimétrica e Estudo Comparativo de Petições PDF/CSV). |
| **[`backend/`](./backend)** | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0, `pdfplumber` | `8000` | API Core & Gateway REST, autenticação JWT, barreira local de anonimização LGPD (`AnonimizadorLGPD`), orquestração via `AIProviderAdapter`, persistência relacional e geração de relatórios em PDF. |
| **[`ai_engine/`](./ai_engine)** | Python 3.11+, Motor Estatístico/Heurístico Local, `AIProviderAdapter` | `8001` *(interna)* | Microsserviço isolado de inteligência híbrida (Modelo Estatístico/Heurístico Local com suporte plugável a APIs externas de LLM como Gemini / OpenAI GPT). |
| **`postgres`** | PostgreSQL 16 Alpine | `5432` | Persistência relacional de usuários, processos higienizados, análises preditivas e logs de auditoria LGPD. |

---

## 3. Como Executar o Projeto e Rodar os Testes

### 3.1 Execução via Docker Compose
Copie o arquivo de exemplo [`.env.example`](./.env.example) para `.env` na raiz do repositório e inicie os serviços:

```bash
cp .env.example .env
docker compose up --build
```

* **Interface Web (`frontend`):** `http://localhost:5173`
* **API Core & Documentação OpenAPI/Swagger (`backend`):** `http://localhost:8000/docs`
* **Healthcheck da API (`backend`):** `http://localhost:8000/health`

### 3.2 Execução Local Rápida e Verificação Automatizada (`pytest`)

```bash
# 1. Instalar dependências do Back-end
pip install -r backend/requirements.txt

# 2. Executar a suíte de verificação automatizada (11 testes: CT-01 a CT-09 + Acessibilidade WCAG)
PYTHONPATH=backend pytest backend/tests/ -v
```

---

## 4. Equipe Epsilon (UFAL)

* **Dupla 1 (Front-end e UI/UX):** Emanuele Vitória e Lucas Gabriel
* **Dupla 2 (Back-end e Arquitetura):** Victor Samyr e Gabriel Damião
* **Dupla 3 (Dados e Inteligência Artificial):** Pedro Henrique e Ygor Vasconcelos
* **Dupla 4 (Gerência de Projetos e Requisitos):** Daniel Filipe e Fernando Gabriel

---

## 5. Licença

Distribuído sob a licença MIT. Veja [LICENSE](./LICENSE) para mais informações.
