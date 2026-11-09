# Diário de Bordo e Registro de Desenvolvimento da Equipe (JuriVision)

> **Finalidade deste documento:** Registrar de forma padronizada todas as implementações, decisões arquiteturais, alterações de ambiente e instruções operacionais do projeto.
> Este documento foi estruturado para ser lido tanto pelos **integrantes humanos da Equipe Epsilon** quanto por seus **assistentes e agentes de Inteligência Artificial (Google Antigravity, Cursor, GitHub Copilot, etc.)**, garantindo que qualquer membro consiga reproduzir o ambiente e compreender a evolução do código sem desalinhamentos.

---

## 📌 Padrão de Registro para Novas Entradas

Toda nova modificação deve seguir o modelo abaixo:

```markdown
### [YYYY-MM-DD] - [Título da Implementação / Feature]
- **Branch:** `nome-da-branch`
- **Autor / Dupla:** Nome do Integrante (Dupla X)
- **Pacote da EAP / Requisitos:** Ex: EAP 1.3.2, RF-02, RNF-04
- **Resumo da Mudança:** Explicação concisa do que foi construído ou alterado.
- **Arquivos Criados / Modificados:**
  - `caminho/do/arquivo1.py` - Descrição objetiva da alteração.
- **Como Testar / Executar Localmente:**
  - Comandos exatos de terminal (PowerShell / Bash).
- **Impacto no Ambiente / Novas Variáveis:**
  - Informar se há novas chaves no `.env.example` ou dependências no `requirements.txt` / `package.json`.
- **Notas para Assistentes de IA:**
  - Regras de negócio, invariantes (ex: LGPD) e decisões de arquitetura que a IA do colega deve respeitar.
```

---

## 📜 Histórico de Implementações e Marcos da Equipe

### [2026-11-05] — Criação da Branch `feat/sprint1-integracao-dev` e Homologação de Testes
- **Branch de Origem:** `feat/backend-core-arquitetura` (commit `688d33c` por Victor Samyr)
- **Nova Branch de Trabalho:** `feat/sprint1-integracao-dev`
- **Responsáveis:** Equipe Epsilon
- **Pacotes da EAP / Requisitos Atendidos:** EAP 1.3.2 (API REST), EAP 1.4.1 (Anonimização LGPD), EAP 1.5.1 (Garantia de Qualidade — ISO 29119) e EAP 1.5.2 (Deploy / Ambiente Local)
- **Resumo da Mudança:**
  1. Criação da branch isolada `feat/sprint1-integracao-dev` para preservar o trabalho de base da `main` e da `feat/backend-core-arquitetura`, aderindo às boas práticas de Git-Flow.
  2. Criação do ambiente virtual local `.venv` (Python 3.12) e instalação de todas as dependências oficiais do Back-end.
  3. Execução e homologação com 100% de sucesso da suíte oficial de testes automatizados (`11 passed` em 9.14s) cobrindo:
     - `CT-01`: Autenticação JWT (sucesso e credenciais inválidas)
     - `CT-02/04/05/06`: Upload de PDF, Barreira LGPD determinística e Predição Heurística Local
     - `CT-03`: Upload e higienização em lote de arquivos CSV
     - `CT-07`: Métricas e indicadores jurimétricos para o Dashboard
     - `CT-08`: Consulta paginada e filtros da base de conhecimento jurisprudencial
     - `CT-09`: Exportação e geração dinâmica de relatório em stream binário PDF
     - `RNF-09/10`: Acessibilidade da interface (WAI-ARIA 1.2, contraste WCAG 2.2 AA, labels e landmarks)
     - `RNF-04`: Integração completa dos contratos da API com o Front-end
  4. Instituição deste arquivo (`docs/CHANGELOG_EQUIPE.md`) como guia perene de comunicação entre integrantes e agentes de IA.

- **Como Executar e Testar Localmente (Guia Rápido para a Equipe):**
  ```powershell
  # 1. Ativar o ambiente virtual e rodar os testes
  $env:PYTHONPATH="backend"; .venv\Scripts\pytest backend/tests/ -v

  # 2. Iniciar o servidor Backend (FastAPI com fallback automático em SQLite)
  .venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --port 8000

  # 3. Em outro terminal, iniciar a interface Web Frontend (Vite / ES Modules)
  cd frontend
  npm run dev
  ```

- **Notas para Assistentes de IA (Instruções Obrigatórias para IAs dos Colegas):**
  > ⚠️ **Invariante Crítico de Privacidade (LGPD):** Jamais contornar ou desativar o `AnonimizadorLGPD` (`backend/app/core/ai_gateway.py`). Nenhum dado bruto (CPF, RG, nome real) pode ser persistido no banco ou enviado ao cliente.  
  > ⚠️ **Padrão Port & Adapter (ADR-002):** O backend consome IA através do `AIProviderAdapter`. O modo padrão de desenvolvimento deve permanecer `AI_PROVIDER=local` para execução offline sem custos de API.  
  > ⚠️ **Fallback de Banco (ADR-003):** O backend funciona transparentemente com PostgreSQL (Docker) ou SQLite local (`jurivision_local.sqlite3`). Não introduza migrações que quebrem a compatibilidade com SQLite.  
  > ⚠️ **Contratos REST Congelados:** Qualquer alteração nos schemas Pydantic deve ser refletida na Seção 8 do `ARCHITECTURE.md` e testada via `backend/tests/test_api_contracts.py`.

---

### [2026-11-05] — Replanejamento Estratégico, Governança por Membro e Snapshot do Frontend
- **Branch:** `feat/sprint1-integracao-dev`
- **Responsáveis:** Equipe Epsilon (Gabriel Damião, Victor Samyr, Emanuele Vitória, Lucas Gabriel, Pedro Henrique, Ygor Vasconcelos, Daniel Filipe e Fernando Gabriel)
- **Pacotes da EAP / Requisitos Atendidos:** EAP 1.1 (Gerenciamento do Projeto), EAP 1.2 (Engenharia de Requisitos e EAP), EAP 1.3 (Desenvolvimento Full-Stack), EAP 1.4 (Inteligência e Dados) e EAP 1.5 (Qualidade e Deploy).
- **Resumo da Mudança:**
  1. **Preservação de Versão Anterior do Front-end:** Criação do snapshot completo em `frontend/versions/v0_prototipo_editorial/` para registrar o protótipo inicial (Legal Editorial) com `README.md` explicativo, permitindo consulta histórica sem travar a evolução modular do MVP.
  2. **Estrutura de Governança Individual (`docs/membros/`):** Criação dos diários de bordo individuais (`CHANGELOG.md`) para cada um dos 8 integrantes, garantindo comprovação de participação acadêmica exigida pelo Prof. Rafael De Amorim Silva.
  3. **Validação Arquitetural da IA & DataJud:**
     - Confirmação da sinergia entre **DataJud (CNJ)** e **Gemini API (Google AI Studio - Free Tier)**. O DataJud fornece metadados e histórico oficial; o Gemini processa a síntese factual da petição **após** a barreira do `AnonimizadorLGPD` (Art. 12 da LGPD); o motor estatístico local calcula as taxas e prazos.
     - Custo real estritamente mantido em **R$ 0,00**, com fallback automático para o motor heurístico local caso não haja chave de API ou conexão à internet.
  4. **Validação da Suíte de Testes:** Execução da suíte completa com **11/11 testes aprovados** no ambiente virtual local.

- **Arquivos Criados / Modificados:**
  - `frontend/versions/v0_prototipo_editorial/*` - Snapshot preservado da interface inicial.
  - `docs/membros/README.md` - Guia e regras de governança para registro de entregas individuais.
  - `docs/membros/<integrante>/CHANGELOG.md` - 8 diários de bordo individuais estruturados por dupla.
  - `docs/CHANGELOG_EQUIPE.md` - Registro oficial consolidado da equipe.

- **Notas para Assistentes de IA:**
  - A interface em desenvolvimento ativo é `frontend/index.html` e `frontend/src/`. O diretório `frontend/versions/` é estritamente somente-leitura (arquivo histórico).
  - Toda nova funcionalidade deve respeitar a premissa de custo zero e execução local autônoma.

---

### [2026-11-05] — Implementação da Frente 1: Configuração, DataJudClient e GeminiAIAdapter
- **Branch:** `feat/sprint1-integracao-dev`
- **Responsáveis:** Gabriel Damião, Victor Samyr, Pedro Henrique e Ygor Vasconcelos (Duplas 2 e 3)
- **Pacotes da EAP / Requisitos Atendidos:** EAP 1.3.2 (API REST), EAP 1.4.2 (Integração com Base de Conhecimento Jurisprudencial), RF-08 (Consulta Jurisprudencial), RNF-05 (Tolerância a Falhas) e RNF-06 (LGPD).
- **Resumo da Mudança:**
  1. **Expansão de Configurações (`backend/app/core/config.py`):**
     - Adicionadas configurações opcionais com fallbacks seguros para `GEMINI_API_KEY`, `GEMINI_MODEL` (default: `gemini-2.5-flash`), `DATAJUD_API_KEY`, `DATAJUD_BASE_URL` e timeouts estritos (3.0s DataJud, 4.0s Gemini).
  2. **Cliente Leve e Resiliente do DataJud (`backend/app/core/datajud_client.py`):**
     - Consulta assíncrona HTTP via `httpx.AsyncClient` com payload Elasticsearch DSL oficial do CNJ.
     - Resolução automática de alias do tribunal a partir do número CNJ (ex: `8.02` -> `api_publica_tjal`, `8.26` -> `api_publica_tjsp`, `4.05` -> `api_publica_trf5`).
     - Tratamento defensivo de timeouts e erros de rede com fallback automático para o acervo homologado local do TJAL (evitando qualquer erro 500 para o usuário).
  3. **Adaptador Google Gemini (`backend/app/core/ai_gateway.py`):**
     - Criação da classe `GeminiAIAdapter` plugada ao `ResilientAIGateway`.
     - Invariante LGPD respeitado: o texto da petição é sanitizado via `AnonimizadorLGPD` antes da chamada externa; as respostas do modelo passam por nova sanitização na saída (defesa em profundidade).
     - Se `GEMINI_API_KEY` não for informada ou houver falha de conexão, a predição chaveia instantaneamente para o `LocalDeterministicFallbackAdapter` (heurístico/estatístico local).
  4. **Novo Endpoint REST (`backend/app/routers/processos.py`):**
     - Rota `GET /api/v1/processos/datajud/{numero_processo}` registrada e tipada com `DataJudProcessoResponse`.
  5. **Garantia de Qualidade (ISO 29119):**
     - Criação de `backend/tests/test_datajud_and_gemini.py` com 6 novos testes cobrindo parsing, resolução de alias, resiliência de rede e barreira LGPD no Gemini.
     - Suíte de testes automatizados expandida para **17 testes aprovados com 100% de sucesso**.

- **Arquivos Criados / Modificados:**
  - `backend/app/core/config.py` - Novas variáveis para Gemini e DataJud.
  - `backend/app/core/datajud_client.py` - Cliente assíncrono com fallback.
  - `backend/app/core/ai_gateway.py` - `GeminiAIAdapter` integrado ao gateway.
  - `backend/app/schemas/contracts.py` - Novos schemas para o DataJud.
  - `backend/app/routers/processos.py` - Endpoint `/api/v1/processos/datajud/{numero_processo}`.
  - `backend/tests/test_datajud_and_gemini.py` - 6 testes unitários e de integração.
  - `docs/membros/*/CHANGELOG.md` - Registros individuais atualizados.
  - `docs/CHANGELOG_EQUIPE.md` - Registro consolidado da equipe.

---

### [2026-11-05] — Implementação da Frente 2: Conexão Front-end com DataJud e Auditoria LGPD
- **Branch:** `feat/sprint1-integracao-dev`
- **Responsáveis:** Emanuele Vitória, Lucas Gabriel, Victor Samyr e Gabriel Damião (Duplas 1 e 2)
- **Pacotes da EAP / Requisitos Atendidos:** EAP 1.3.3 (Interface Web Front-end), RF-08 (Consulta Jurisprudencial), RNF-04 (Usabilidade) e RNF-09 (Acessibilidade WCAG 2.2 AA).
- **Resumo da Mudança:**
  1. **Serviço HTTP Front-end (`frontend/src/services/api.js`):**
     - Adicionada a função assíncrona `consultarProcessoDatajud(numeroProcesso)` consumindo o endpoint `/api/v1/processos/datajud/{numero_processo}`.
  2. **Interface Visual Oficial (`frontend/index.html`):**
     - Integrado o botão de ação rápida "Consultar DataJud (CNJ)" na barra de pesquisa principal.
     - Criado o componente de resposta estruturada (`#datajud-result-box`) exibindo classe processual, assunto principal, órgão julgador, data de ajuizamento formatada e lista de movimentações recentes.
  3. **Lógica da Aplicação (`frontend/src/app.js`):**
     - Criada a função `dispararConsultaDataJud()` com feedbacks de carregamento (toasts e leitor de tela `aria-live`).
     - Renderização dinâmica do cartão de retorno com distinção clara entre dados ao vivo da API do CNJ e dados de fallback local do TJAL.
  4. **Homologação e Testes (17/17 aprovados):**
     - Garantida a conformidade com WCAG 2.2 AA, WAI-ARIA 1.2 e integridade dos contratos de dados.

- **Arquivos Criados / Modificados:**
  - `frontend/src/services/api.js` - Função `consultarProcessoDatajud`.
  - `frontend/index.html` - Botão e cartão de resposta do DataJud.
  - `frontend/src/app.js` - Controle de evento e renderização dinâmica.
  - `docs/membros/*/CHANGELOG.md` - Registros individuais atualizados.
  - `docs/CHANGELOG_EQUIPE.md` - Registro consolidado da equipe.

---

### [2026-11-09] — Preparação para Entrega: Roteiro de Demonstração e Expansão do Dataset TJAL
- **Branch:** `feat/sprint1-integracao-dev`
- **Responsáveis:** Equipe Epsilon (Gabriel Damião, Victor Samyr, Daniel Filipe, Fernando Gabriel, Pedro Henrique e Ygor Vasconcelos)
- **Pacotes da EAP / Requisitos Atendidos:** EAP 1.1 (Gerenciamento do Projeto), EAP 1.4.2 (Base de Conhecimento), EAP 1.5.1 (Garantia de Qualidade) e EAP 1.5.2 (Deploy/Apresentação).
- **Resumo da Mudança:**
  1. **Roteiro Oficial de Demonstração (`docs/ROTEIRO_DEMONSTRACAO.md`):**
     - Estruturado roteiro cronometrado de 5 minutos cobrindo: Abertura e Dashboard, Pesquisa e Consulta DataJud (CNJ), Ingestão e Barreira LGPD (Art. 12), Jurimetria Preditiva e Governança/Testes.
     - Inclui checklist de pré-apresentação e tabela de respostas blindadas para as perguntas mais prováveis da banca acadêmica.
  2. **Carga Expandida do Acervo TJAL (`scripts/seed_tjal_expandido.py`):**
     - Script idempotente gerando 50 novos processos reais/sintéticos higienizados (LGPD) com distribuição realista de varas de Alagoas (Maceió, Arapiraca, Penedo, Rio Largo).
     - Acervo expandido de 13 para **63 julgados**, enriquecendo os gráficos de volume por tema e decisões por juiz no Dashboard.
  3. **Homologação e Testes Automatizados:**
     - Todos os **17 testes no pytest continuam 100% aprovados** (`17 passed in 7.42s`).

- **Arquivos Criados / Modificados:**
  - `docs/ROTEIRO_DEMONSTRACAO.md` - Guia oficial de apresentação e pitch de 5 minutos.
  - `scripts/seed_tjal_expandido.py` - Script de carga expandida de dados do TJAL.
  - `docs/CHANGELOG_EQUIPE.md` - Registro consolidado da equipe.

---

### [2026-11-09] — Refinamento de Governança, Resiliência e Homologação de Pontas Soltas
- **Branch:** `fix/sprint1-refinamentos`
- **Responsáveis:** Victor Samyr e Gabriel Damião (com revisão por Equipe Epsilon)
- **Pacotes da EAP / Requisitos Atendidos:** EAP 1.1 (Governança e RACI), EAP 1.4.2 (DataJud Fallback), EAP 1.4.3 (Gemini Resiliência), EAP 1.5.1 (ISO 29119 - 19 Testes).
- **Resumo da Mudança:**
  1. **Governança de Membros (`docs/membros/`):**
     - Corrigida a regra do `.gitignore` para permitir o versionamento dos diários de bordo individuais (`CHANGELOG.md`) e do guia geral (`docs/membros/README.md`), garantindo auditoria acadêmica para os 8 membros.
     - Inicializados os 8 arquivos `CHANGELOG.md` estruturados por dupla e pacotes da EAP.
  2. **Ambiente Local e Portabilidade (`start_dev.ps1`):**
     - Adicionada verificação preventiva da pasta `node_modules` no PowerShell com execução automática de `npm install`, espelhando o comportamento seguro do `start_dev.bat`.
  3. **Robustez na Busca Local do DataJud (`DataJudClient`):**
     - Adicionado suporte a busca por CNJ com 20 dígitos contínuos (sem máscara), reconvertendo para a máscara padrão CNJ e evitando falsos positivos com inputs vazios.
  4. **Resiliência de Parse no Gemini (`GeminiAIAdapter`):**
     - Adicionado tratamento para remoção defensiva de blocos markdown (```json ... ```) em respostas do LLM antes do `json.loads`.
  5. **Documentação e Template de Variáveis (`.env.example`):**
     - Registradas variáveis para `AI_PROVIDER=auto`, `GEMINI_MODEL`, `DATAJUD_BASE_URL` e timeouts.
  6. **Ampliação da Suíte de Testes (19/19 aprovados):**
     - Novos testes automatizados cobrindo busca por CNJ sem máscara e tratamento defensivo de markdown no Gemini.

- **Arquivos Criados / Modificados:**
  - `.gitignore` - Desbloqueado versionamento de documentação de membros.
  - `start_dev.ps1` - Automação preventiva de `npm install`.
  - `backend/app/core/datajud_client.py` - Busca inteligente de fallback por CNJ com e sem máscara.
  - `backend/app/core/ai_gateway.py` - Sanitização prévia de markdown fences em respostas JSON.
  - `.env.example` - Documentação expandida de variáveis de ambiente.
  - `backend/tests/test_datajud_and_gemini.py` - 2 novos testes adicionados (total 19 passed).
  - `docs/membros/*/CHANGELOG.md` - Diários individuais criados.
