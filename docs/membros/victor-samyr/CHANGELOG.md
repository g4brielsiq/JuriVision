# Diário de Bordo Individual — Victor Samyr

- **Integrante:** Victor Samyr
- **Papel:** Engenharia de Back-end, Arquitetura & Governança de Dados (Dupla 2)
- **Pacotes da EAP de Referência:** EAP 1.3.1 (Armazenamento), EAP 1.3.2 (API REST Core), EAP 1.4.1 (Barreira LGPD) e ADR-001/ADR-002/ADR-003
- **Projeto:** JuriVision — Plataforma de Jurimetria Preditiva e Pesquisa de Precedentes (UFAL)

---

## 📜 Histórico de Contribuições (Sprint 1 - MVP)

### [2026-11-05] — Arquitetura da API Core, Banco Dual e Barreira Determinística LGPD
- **Branch de Atuação:** `feat/backend-core-arquitetura`
- **Atividades Realizadas:**
  - Definição arquitetural da API Core REST com FastAPI e contratos estritos via Pydantic v2.
  - Implementação do mecanismo de banco dual com resiliência automática entre PostgreSQL 16 (Docker) e SQLite local (`jurivision_local.sqlite3`) conforme ADR-003.
  - Criação do componente determinístico `AnonimizadorLGPD` (`backend/app/core/ai_gateway.py`), garantindo que nenhum dado sensível (CPF, RG, nomes de partes civis) seja persistido ou enviado a serviços externos sem higienização irreversível (Art. 12 da LGPD).
  - Implementação dos endpoints de ingestão e predição: `POST /api/v1/processos/upload-pdf`, `POST /api/v1/processos/upload-csv`, `GET /api/v1/dashboard/metricas` e `GET /api/v1/relatorios/processo/{id}/pdf`.
  - Construção da suíte de testes de contratos da API (`backend/tests/test_api_contracts.py`), homologando CT-01 a CT-09.

### [2026-11-09] — Refinamento de Resiliência, Governança e Homologação
- **Branch de Atuação:** `fix/governanca-membros-consolidacao`
- **Atividades Realizadas:**
  - Ajuste na lógica de busca de fallback local do `DataJudClient` para suportar consultas com CNJ contínuo de 20 dígitos sem pontuação e blindagem de consultas nulas/inválidas.
  - Tratamento defensivo no `GeminiAIAdapter` para remoção automática de markdown fences em respostas JSON do LLM.
  - Consolidação da governança da equipe ativa e reestruturação dos diários de bordo para avaliação acadêmica.
- **Status:** Entregue com 100% dos testes aprovados no pytest (19 de 19 testes).

### [2026-11-21] — Reformulação do Shell Global e Pesquisa de Precedentes (Guia de Estilo v2)
- **Branch de Atuação:** `feat/frontend-design-system-v2`
- **Atividades Realizadas:**
  - Especificação do Guia de Estilo v2 (`docs/DESIGN_SYSTEM_V2.md` — *Repertório Jurídico Contemporâneo*), calibrando tokens para neutros quentes (`#F6F4EF`, `#EFECE5`, `#DFDBD2`, `#C9C3B8`) e substituindo `Inter` por `IBM Plex Sans`.
  - Refatoração do shell global (`frontend/index.html` e `frontend/src/components/design-tokens.css`): sidebar clara (`236px`), remoção do monograma e estilos *inline*, cabeçalho enxuto (`48px`) e fichas de decisão contínuas sem caixas redundantes.
  - Integração e compatibilização do Guia v2 com os modais de cadastro/edição de julgados e cadastro de advogados da branch `dev` (PR #9).
- **Status:** Build de produção do frontend aprovado (`npm run build`) e **33 de 33 testes automatizados** aprovados no pytest.

### [2026-11-21] — Etapa 1 (JuriVision-Pro): Filtros/Ordenação no Servidor, Exclusão Integrada e PDF Multi-página
- **Branch de Atuação:** `dev` (`pro` — `VictorSamyr/JuriVision-Pro`)
- **Atividades Realizadas:**
  - Estruturação do Roadmap Mestre (Etapas 1 a 6) em `docs/CHANGELOG_EQUIPE.md`.
  - Evolução de `GET /api/v1/processos` com ordenação no banco (`recentes`, `antigas`, `assunto`), filtro server-side por `ids` e retorno de `resumo_curto`, além do novo endpoint `GET /api/v1/processos/filtros`.
  - Evolução de `_build_pdf_document` em `backend/app/routers/relatorios.py` para paginação automática multi-página em PDF 1.4.
  - Integração completa no front-end (`api.js`, `index.html`, `app.js`), incluindo carregamento dinâmico de filtros e exclusão de julgados (`DELETE /api/v1/processos/{id_processo}`) na folha de leitura.
  - Criação da suíte `backend/tests/test_etapa1_consistencia_e_filtros.py` com 8 testes exaustivos da Etapa 1.
- **Status:** Build do frontend (`npm run build`) e **41 de 41 testes automatizados** aprovados no pytest.

### [2026-11-21] — Etapa 2 (JuriVision-Pro): Segurança JWT, Endpoint `/auth/me` e Isolamento Multi-usuário
- **Branch de Atuação:** `dev` (`pro` — `VictorSamyr/JuriVision-Pro`)
- **Atividades Realizadas:**
  - Implementação de `get_optional_current_user`, `get_current_user_strict`, `build_processo_visibility_filter`, `can_read_processo` e `ensure_can_modify_processo` em `backend/app/core/security.py`.
  - Criação do endpoint `GET /api/v1/auth/me` em `backend/app/routers/auth.py` e aplicação do isolamento multi-tenant em `processos.py`, `dashboard.py` e `relatorios.py`.
  - Integração no front-end (`api.js`, `index.html`, `app.js`) com restauração de sessão autenticada, propagação de `?token=` para relatórios PDF privados e botão `#btn-logout-account`.
  - Criação da suíte `backend/tests/test_etapa2_seguranca_e_isolamento.py` com 7 testes exaustivos.
- **Status:** Build do frontend (`npm run build`) e **48 de 48 testes automatizados** aprovados no pytest.
