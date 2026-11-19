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
