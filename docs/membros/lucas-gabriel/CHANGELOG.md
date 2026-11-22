# Diário de Bordo Individual — Lucas Gabriel

- **Integrante:** Lucas Gabriel
- **Papel:** Responsável Técnico, Engenharia Front-end, Dados & Inteligência Artificial
- **Pacotes da EAP de Referência:** EAP 1.1 (Gerência do Projeto), EAP 1.2 (Requisitos e EAP), EAP 1.3.3 (Interface Web Front-end), EAP 1.4.1 (Barreira LGPD), EAP 1.4.3 (Motor Preditivo e Gemini NLP), EAP 1.5.1 (Garantia de Qualidade e Acessibilidade)
- **Projeto:** JuriVision — Plataforma de Jurimetria Preditiva e Pesquisa de Precedentes (UFAL)

---

## 📜 Histórico de Contribuições (Sprint 1 - MVP)

### [2026-11-05] — Arquitetura Front-end (Legal Editorial), Acessibilidade e Integração com API Core
- **Branch de Atuação:** `feat/sprint1-integracao-dev`
- **Atividades Realizadas:**
  - **Liderança Técnica e Interface do Usuário (Centralização da Camada de Front-end):**
    - Concepção, design e implementação do front-end SPA em JavaScript Vanilla com Vite e Chart.js na direção visual *Legal Editorial + Legal Intelligence*.
    - Desenvolvimento dos cartões documentais de decisão, tabela comparativa de precedentes, folha individual de leitura e modal acessível de ingestão documental (PDF e CSV).
    - Implementação de conformidade estrita com **W3C WCAG 2.2 Nível AA** e **WAI-ARIA 1.2** (navegação completa por teclado, contraste verificado e tabelas ocultas acessíveis para leitores de tela em cada gráfico).
    - Criação da suíte automatizada de acessibilidade e integração em `backend/tests/test_frontend_accessibility.py` (RNF-04, RNF-09, RNF-10).
  - **Consolidação de Inteligência Artificial e Dados (Absorção das atividades de Dados/IA):**
    - Integração do componente `GeminiAIAdapter` (`backend/app/core/ai_gateway.py`) para síntese de teses jurídicas e resumo factual via Google AI Studio (Gemini 2.5 Flash Free Tier) a custo real R$ 0,00.
    - Validação prática da barreira determinística do `AnonimizadorLGPD` sobre o tráfego enviado à IA externa e na higienização da resposta recebida.
    - Suporte à esteira de ingestão e testes de resiliência e fallback offline para o motor estatístico local.
  - **Governança, Requisitos e EAP (Absorção das atividades de Requisitos e Qualidade):**
    - Alinhamento de escopo da Sprint 1 cobrindo os requisitos RF-01 a RF-09 e RNF-01 a RNF-10.
    - Acompanhamento da matriz de rastreabilidade entre requisitos, contratos Pydantic e suíte de testes (ISO 29119).
    - Preservação da memória visual da versão inicial em `frontend/versions/v0_prototipo_editorial/`.

### [2026-11-09] — Integração DataJud no Front-end, Automação do Ambiente e Homologação
- **Branch de Atuação:** `feat/sprint1-integracao-dev` / `fix/governanca-membros-consolidacao`
- **Atividades Realizadas:**
  - Conexão do serviço `consultarProcessoDatajud` em `frontend/src/services/api.js`.
  - Construção do componente visual `#datajud-result-box` no `frontend/index.html` e lógica de renderização dinâmica em `frontend/src/app.js`.
  - Ajuste no script automatizado `start_dev.ps1` com checagem preventiva de dependências Node (`npm install`).
  - Homologação da suíte completa de 19 testes automatizados com 100% de aprovação.
- **Status:** Entregue e homologado com sucesso.

### [2026-11-22] — Refinamentos de Precisão Jurídica, Similares Reais, Isolamento de Testes e Coleta Automática DataJud (Cards #27, #35, #62 e #64)
- **Branches de Atuação:** `feat/sprint2-backend-precisao-testes` (PR #12) e `feat/datajud-coleta-automatica`
- **Atividades Realizadas:**
  - **Homologação Visual Integrada (`dev` → `main` | Card #62):** condução dos testes visuais dos fluxos de conta, cadastro/edição de julgados com prévia LGPD e Guia de Estilo v2 (Etapa 1), seguida da abertura e merge do PR #11 na `main`.
  - **Precisão Jurídica, Processos Semelhantes Reais e Isolamento do Banco de Testes (Cards #35 e #64):**
    - Isolamento do banco SQLite em ambiente de testes (`backend/tests/conftest.py`) para proteger `jurivision_local.sqlite3`.
    - Implementação da busca real de precedentes semelhantes (`GET /api/v1/processos/{id_processo}/similares`), eliminando multiplicadores estáticos (`* 7` e `42`) e exibindo a natureza da estimativa heurística vs. IA na interface.
    - Adição de filtros por `comarca` e `tribunal` em `GET /api/v1/processos` e validação estrita de tokens JWT (`GET /api/v1/auth/me`).
  - **Coleta Automática em Lote e Atualização da Base via DataJud (Card #27):**
    - Implementação de `DataJudClient.coletar_lote_jurisprudencia()` e `extrair_registro_para_acervo()` em `backend/app/core/datajud_client.py`.
    - Criação do endpoint `POST /api/v1/processos/datajud/sincronizar` com higienização determinística `AnonimizadorLGPD` (`RN-01`) e atualização idempotente da base histórica.
    - Integração do botão **"Sincronizar lote DataJud"** na Pesquisa de Precedentes e ampliação da suíte para **39 testes automatizados aprovados**.
- **Status:** Entregue e homologado com sucesso.

