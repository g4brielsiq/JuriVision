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
