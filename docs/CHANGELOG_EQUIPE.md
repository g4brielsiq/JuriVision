# Diário de Bordo e Registro de Desenvolvimento da Equipe (JuriVision)

> **Finalidade deste documento:** Registrar de forma padronizada todas as implementações, decisões arquiteturais, alterações de ambiente e instruções operacionais do projeto.
> Este documento foi estruturado para ser lido tanto pelos **integrantes humanos da Equipe Epsilon** quanto por seus **assistentes e agentes de Inteligência Artificial (Google Antigravity, Cursor, GitHub Copilot, etc.)**, garantindo que qualquer membro consiga reproduzir o ambiente e compreender a evolução do código sem desalinhamentos.

---

## 🎯 Roadmap de Evolução: Eliminação de Atalhos do MVP rumo ao Produto Real (CONAD / SaaS)

A tabela abaixo ordena todas as frentes de evolução técnica **da mais simples à mais complexa**, rastreando o que ainda era atalho/protótipo no MVP acadêmico e o que já foi convertido em funcionalidade real com testes exaustivos:

| Etapa | Frente / Escopo Técnico | Complexidade | O que Substitui (Atalho / Lacuna Anterior) | Status |
| :---: | :--- | :---: | :--- | :---: |
| **1** | **Consistência de Pesquisa, Filtros/Ordenação no Servidor, Exclusão Integrada & PDF Multi-página** | Baixa | Filtro de salvos e ordenação apenas em memória na página atual; seletores de assunto/juiz fixos no HTML; listagem sem `resumo_curto`; rota `DELETE` sem UI; PDF restrito a 1 página. | `[x] CONCLUÍDA` |
| **2** | **Segurança, JWT Obrigatório e Isolamento Multi-usuário** | Baixa / Média | Rotas de upload/leitura sem verificação de Bearer token e gravação fixa em `usuario_id="usr-01"`, misturando documentos de diferentes usuários. | `[x] CONCLUÍDA` |
| **3** | **Endurecimento da Barreira LGPD (Regex Expandido & Detecção em Prosa)** | Média | `AnonimizadorLGPD` restrito a CPF, RG rotulado e linha `Autor: Nome`, sem mascarar e-mails, telefones, endereços ou nomes soltos. | `[x] CONCLUÍDA` |
| **4** | **Motor NLP Local Real e Similaridade Textual (`TF-IDF` / `BM25`)** | Média / Alta | Classificação via 5 `if/else`, resumo pelas 2 primeiras frases, juiz padrão hardcoded (`Dr. Rafael De Amorim`), multiplicador fixo `* 7` e margem fixa `±8%`. | `[x] CONCLUÍDA` |
| **5** | **RAG Jurídico (Gemini + Precedentes Reais), Cache SHA-256, Extrator PDF e `ai_engine:8001`** | Alta | `ai_engine/worker.py` em `sleep(3600)`, Gemini sem contexto dos julgados do banco e extração restrita a operadores `Tj` simples. | `[x] CONCLUÍDA` |
| **6** | **Modelo Freemium / Assinaturas, Cache de Demo e Deploy Cloud (CONAD)** | Alta | Plataforma 100% aberta em `localhost` sem planos (`FREE`/`PRO`), cotas de uso ou hospedagem escalável em nuvem. | `[ ] PENDENTE` |

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

---

### [2026-11-09] — Consolidação de Governança Efetiva: Limpeza de Pastas Inativas e RACI
- **Branch:** `fix/governanca-membros-consolidacao`
- **Responsáveis:** Victor Samyr, Gabriel Damião e Lucas Gabriel (Equipe Efetiva Epsilon)
- **Pacotes da EAP / Requisitos Atendidos:** EAP 1.1 (Governança e RACI), EAP 1.4.1 a 1.4.3 (Full-Stack e IA), EAP 1.5.1 (Garantia de Qualidade).
- **Resumo da Mudança:**
  1. **Consolidação de Governança e Rastreabilidade (`docs/membros/`):**
     - Remoção de pastas de integrantes inativos que não entregaram código na Sprint 1.
     - Centralização formal: **Lucas Gabriel** assume como **Responsável Técnico**, absorvendo front-end/UI/UX, acessibilidade, inteligência de dados/Gemini e engenharia de requisitos; **Victor Samyr** e **Gabriel Damião** consolidam a arquitetura back-end, banco dual, barreira LGPD e cliente DataJud.
     - Restauração do `.gitignore` para o estado anterior padrão limpo (sem regras artificiais de bloqueio de documentação).
     - Atualização do `docs/membros/README.md` e dos diários de bordo individuais dos membros ativos.

- **Arquivos Criados / Modificados:**
  - `.gitignore` - Restaurado para o estado limpo padrão.
  - `docs/membros/README.md` - Quadro de responsabilidades consolidado.
  - `docs/membros/*/CHANGELOG.md` - Diários individuais detalhados dos membros ativos.
  - `docs/CHANGELOG_EQUIPE.md` - Registro oficial consolidado da equipe.

---

### [2026-11-16] — Cadastro e Edição Manual de Processos
- **Branch:** `feat/cadastro-edicao-processos`
- **Autor / Dupla:** Emanuele Vitória (com revisão da Equipe Epsilon)
- **Pacote da EAP / Requisitos:** EAP 1.3.2 (API REST), RF-08, RN-01
- **Resumo da Mudança:** Novas rotas `POST /api/v1/processos` e `PUT /api/v1/processos/{id_processo}` para cadastrar e editar processos sem depender de upload de PDF/CSV. Partes e resumo passam pela barreira `AnonimizadorLGPD` antes de gravar; cada cadastro/edição gera um registro em `LogAuditoriaLGPD`. Somente back-end: a tela de cadastro/edição fica para o front-end.
- **Arquivos Criados / Modificados:**
  - `backend/app/schemas/contracts.py` - Novo schema `ProcessoCadastroRequest` (validação CNJ, resultado e tamanhos).
  - `backend/app/schemas/__init__.py` - Exporta o novo schema.
  - `backend/app/routers/processos.py` - Rotas de cadastro e edição, estimativa heurística da análise preditiva e checagem de número duplicado.
  - `backend/tests/test_cadastro_edicao.py` - 9 novos testes (CT-10 a CT-13).
  - `ARCHITECTURE.md` - Contrato da API na Seção 8.5.1.
- **Como Testar / Executar Localmente:**
  - PowerShell: `$env:PYTHONPATH="backend"; pytest backend/tests/ -v` (30 testes aprovados).
  - Swagger: `http://localhost:8000/docs` → "Processos e Base de Conhecimento" → `POST /api/v1/processos`.
- **Impacto no Ambiente / Novas Variáveis:** Nenhum. Sem novas dependências nem variáveis no `.env`.
- **Notas para Assistentes de IA:**
  - Nunca persistir autor, réu ou resumo sem passar por `AnonimizadorLGPD` (RN-01).
  - O `PUT` é substituição completa: o front-end deve reenviar todos os campos (pode reenviar os nomes já mascarados retornados pelo `GET`).
  - `origem_ingestao = "MANUAL"` identifica processos cadastrados por este fluxo.

### [2026-11-19] — Cadastro de Advogados e Interface de Cadastro/Edição de Julgados com Prévia LGPD
- **Branch:** `FrontEnd/Ygor`
- **Autor / Dupla:** Ygor Vasconcelos
- **Pacote da EAP / Requisitos:** EAP 1.3.2 (API REST), EAP 1.3.3 (Interface Web Front-end), EAP 1.4.1 (Anonimização LGPD), RF-01, RF-08, RN-01
- **Resumo da Mudança:**
  1. **Cadastro de advogados (`POST /api/v1/auth/register`):** validação/normalização de e-mail e OAB (`número/UF`), hash de senha, tratamento de conflitos `409`, proteção contra exposição de senha em erros `422` e formulário integrado à janela de conta (`Criar conta`).
  2. **Interface de cadastro e edição de julgados (`frontend/src/components/julgado-form.js`):** modal acessível integrado a `POST /api/v1/processos` e `PUT /api/v1/processos/{id_processo}`, com retorno de `resultado` e `data_julgamento` em `GET /api/v1/processos/{id_processo}` (`ProcessoDetalhesResponse`) e escape HTML (`escapeHtml`) contra XSS na listagem.
  3. **Prévia de anonimização LGPD em tempo real (`POST /api/v1/processos/anonimizacao/previa`):** aplica a mesma rotina de `AnonimizadorLGPD` usada no salvamento durante a digitação (com *debounce* e `AbortController`), sem persistir rascunhos.
- **Como Testar / Executar Localmente:**
  - PowerShell: `$env:PYTHONPATH="backend"; pytest backend/tests/ -v` (**33 testes aprovados**).
  - Front-end: `cd frontend; npm run build`.
- **Detalhes:** [Contrato do cadastro de advogados](./membros/ygor-vasconcelos/REGISTER_ADVICE.md) e [Seção 3.6 do README](../README.md#36-cadastro-e-edição-de-julgados).

---

### [2026-11-21] — Reformulação do Shell Global e Pesquisa de Precedentes (Guia de Estilo v2)
- **Branch:** `feat/frontend-design-system-v2`
- **Autor / Dupla:** Victor Samyr
- **Pacote da EAP / Requisitos:** EAP 1.2.2 (Código-Fonte Interface Web), EAP 1.5.1 (Garantia de Qualidade / Acessibilidade), RNF-04, RNF-09, RNF-10
- **Resumo da Mudança:**
  1. **Guia de Estilo v2 (`docs/DESIGN_SYSTEM_V2.md`):** formalização da estética *Repertório Jurídico Contemporâneo*, com paleta neutra quente (`#F6F4EF`, `#EFECE5`, `#DFDBD2`, `#C9C3B8`) e tipografia `Source Serif 4` + `IBM Plex Sans` + `JetBrains Mono`.
  2. **Shell global e Pesquisa de Precedentes (`frontend/index.html`, `frontend/src/components/design-tokens.css`, `frontend/src/app.js`):** sidebar clara e silenciosa (`236px`), remoção de estilos *inline*, busca principal inline, painel DataJud com tokens semânticos, fichas jurídicas contínuas com filetes de `1px` e integração com os modais de cadastro/edição de julgados e cadastro de advogados.
- **Como Testar / Executar Localmente:**
  - PowerShell: `$env:PYTHONPATH="backend"; pytest backend/tests/ -v` (**33 testes aprovados**).
  - Front-end: `cd frontend; npm run build`.

---

### [2026-11-21] — Etapa 1: Filtros e Ordenação no Servidor, Exclusão Integrada de Julgados e Relatórios PDF Multi-página
- **Branch:** `dev` (`VictorSamyr/JuriVision-Pro`)
- **Autor / Dupla:** Victor Samyr
- **Pacote da EAP / Requisitos:** Etapa 1 do Roadmap, EAP 1.3.2, EAP 1.3.3, RF-08, RF-09
- **Resumo da Mudança:**
  1. **Filtros e Ordenação no Servidor (`backend/app/routers/processos.py`, `backend/app/schemas/contracts.py`):** adicionados os parâmetros `ordenacao` (`recentes`, `antigas`, `assunto`) e `ids` (lista separada por vírgula para "Decisões Salvas") em `GET /api/v1/processos`, retorno de `resumo_curto` real (`resumo_nlp`) nos itens listados e criação do endpoint `GET /api/v1/processos/filtros` com listas distintas e ordenadas de temas, magistrados e comarcas.
  2. **Relatório PDF Multi-página (`backend/app/routers/relatorios.py`):** `_build_pdf_document` agora pagina automaticamente em blocos de até 45 linhas por página, gerando objetos `/Pages` e `/Page` válidos em PDF 1.4 com rodapé `Pagina X de N`.
  3. **Integração Front-end (`frontend/src/services/api.js`, `frontend/index.html`, `frontend/src/app.js`):** consumo dinâmico de `/api/v1/processos/filtros`, passagem de `ordenacao` e `ids` para o servidor, correção do *drill-down* por juiz/tema no Dashboard e botão `#btn-excluir-julgado` integrado ao endpoint `DELETE /api/v1/processos/{id_processo}`.
- **Arquivos Criados / Modificados:**
  - `backend/app/schemas/contracts.py` e `backend/app/schemas/__init__.py` - Campo `resumo_curto` e schema `FiltrosDisponiveisResponse`.
  - `backend/app/routers/processos.py` - Ordenação e filtro `ids` no servidor, `resumo_curto` e rota `GET /api/v1/processos/filtros`.
  - `backend/app/routers/relatorios.py` - Paginação automática multi-página em `_build_pdf_document`.
  - `frontend/src/services/api.js`, `frontend/index.html` e `frontend/src/app.js` - Integração de filtros dinâmicos, busca/ordenação no servidor e exclusão de julgados.
  - `backend/tests/test_etapa1_consistencia_e_filtros.py` - Suíte exaustiva com 8 novos testes cobrindo toda a Etapa 1.
- **Como Testar / Executar Localmente:**
  - PowerShell: `$env:PYTHONPATH="backend"; .\.venv\Scripts\pytest backend/tests/ -v` (**41 testes aprovados**).
  - Front-end: `cd frontend; npm run build`.

---

### [2026-11-21] — Etapa 2: Segurança JWT, Endpoint `/auth/me` e Isolamento Multi-usuário
- **Branch:** `dev` (`VictorSamyr/JuriVision-Pro`)
- **Autor / Dupla:** Victor Samyr
- **Pacote da EAP / Requisitos:** Etapa 2 do Roadmap, EAP 1.3.2, RF-01, RNF-06 (Segurança / ISO 27001)
- **Resumo da Mudança:**
  1. **Validação JWT e Helpers de Isolamento (`backend/app/core/security.py`):** implementados `get_optional_current_user` (Bearer header ou `?token=`), `get_current_user_strict`, `build_processo_visibility_filter`, `can_read_processo` e `ensure_can_modify_processo`. Qualquer token inválido/expirado/malformado retorna `401`.
  2. **Endpoint `/auth/me` (`backend/app/routers/auth.py`):** nova rota `GET /api/v1/auth/me` protegida por `get_current_user_strict` retornando o perfil do advogado autenticado.
  3. **Isolamento Multi-usuário nos Routers (`processos.py`, `dashboard.py`, `relatorios.py`):** cada advogado enxerga o acervo público institucional (`usr-01`) mais os seus próprios processos privados; terceiros não veem processos privados de outro advogado (`404` / ocultos na busca, filtros e dashboard) e recebem `403` ao tentar alterar ou excluir registros do acervo público base.
  4. **Sessão e Logout no Front-end (`api.js`, `index.html`, `app.js`):** restauração automática da sessão via `/auth/me`, propagação segura de `?token=` na exportação de PDF em nova aba, atualização automática dos painéis após login e botão `#btn-logout-account` (*Encerrar sessão atual*).
- **Arquivos Criados / Modificados:**
  - `backend/app/core/security.py` - Dependências JWT e isolamento de acesso.
  - `backend/app/routers/auth.py` - Endpoint `GET /api/v1/auth/me`.
  - `backend/app/routers/processos.py`, `backend/app/routers/dashboard.py`, `backend/app/routers/relatorios.py` - Aplicação das regras de visibilidade e propriedade.
  - `frontend/src/services/api.js`, `frontend/index.html`, `frontend/src/app.js` - Restauração de sessão, token no download de PDF e logout.
  - `backend/tests/test_etapa2_seguranca_e_isolamento.py` - Suíte exaustiva com 7 novos testes cobrindo JWT, `/auth/me` e isolamento multi-usuário.
- **Como Testar / Executar Localmente:**
  - PowerShell: `$env:PYTHONPATH="backend"; .\.venv\Scripts\pytest backend/tests/ -v` (**48 testes aprovados**).
  - Front-end: `cd frontend; npm run build`.

---

### [2026-11-21] — Etapa 3: Endurecimento da Barreira LGPD (`AnonimizadorLGPD` Expandido e Detecção em Prosa)
- **Branch:** `dev` (`VictorSamyr/JuriVision-Pro`)
- **Autor / Dupla:** Victor Samyr
- **Pacote da EAP / Requisitos:** Etapa 3 do Roadmap, EAP 1.4.1, RF-04, RN-01, RNF-06 (LGPD Art. 12)
- **Resumo da Mudança:**
  1. **Detecção Expandida de PII (`backend/app/core/ai_gateway.py`):** adicionadas expressões auditáveis para e-mails (`EMAIL_REGEX`), telefones/WhatsApp (`PHONE_REGEX`), CEPs (`CEP_REGEX`), documentos extras (`DOC_EXTRA_REGEX` — CNH, CTPS, PIS/PASEP, Passaporte, Título de Eleitor, CNS) e endereços (`ADDRESS_REGEX`), preservando números CNJ sem colisões.
  2. **Detecção de Nomes em Prosa e Variações (`AnonimizadorLGPD`):** suporte a papéis processuais sem dois-pontos (`Autora Maria Clara...`), locuções jurídicas (`movida por`, `ajuizada por`, `em face de`, `contra`), qualificação civil antes de vírgula (`..., brasileiro, casado, inscrito no CPF`), variações parciais (`Sr./Sra. + sobrenome`, prenome composto e sobrenome isolado de partes conhecidas) e extração de partes em prosa (`extract_parties_from_text`).
  3. **Zero Falso Positivo:** `CORPORATE_REGEX` com fronteiras de palavra (`\b`) e `LEGAL_AND_GEO_STOPWORDS` + `GEO_PHRASES` preservam 100% de empresas, órgãos públicos, magistrados e institutos jurídicos.
- **Arquivos Criados / Modificados:**
  - `backend/app/core/ai_gateway.py` - Endurecimento completo de `AnonimizadorLGPD` e integração em `LocalDeterministicFallbackAdapter`.
  - `backend/tests/test_etapa3_barreira_lgpd_expandida.py` - Suíte exaustiva com 6 novos testes cobrindo todos os vetores de PII e zero falsos positivos.
- **Como Testar / Executar Localmente:**
  - PowerShell: `$env:PYTHONPATH="backend"; .\.venv\Scripts\pytest backend/tests/ -v` (**54 testes aprovados**).
  - Front-end: `cd frontend; npm run build`.

---

### [2026-11-21] — Etapa 4: Motor NLP Local Real (`TF-IDF` / `BM25`), Extração Dinâmica e Intervalo de Wilson
- **Branch:** `dev` (`VictorSamyr/JuriVision-Pro`)
- **Autor / Dupla:** Victor Samyr
- **Pacote da EAP / Requisitos:** Etapa 4 do Roadmap, EAP 1.4.3, RF-05, RF-06, RN-02, RN-03
- **Resumo da Mudança:**
  1. **Motor Matemático de NLP (`backend/app/core/nlp_engine.py`):** implementados tokenização com n-gramas jurídicos (`tokenize_legal_text`), classificação multi-tema por pontuação léxica ponderada (`classify_legal_theme` em 7 áreas jurídicas), extração dinâmica de qualquer magistrado e comarca/vara (`extract_court_and_judge`), sumarização extrativa por centralidade TF-IDF ignorando cabeçalhos formais (`summarize_legal_text`), ranqueamento de precedentes por Similaridade de Cosseno TF-IDF + Okapi BM25 (`rank_similar_precedents`) e cálculo de margem estatística real pelo Intervalo de Wilson (`compute_wilson_margin`).
  2. **Contratos e Fluxos Integrados (`contracts.py`, `ai_gateway.py`, `processos.py`):** `LocalDeterministicFallbackAdapter`, `_compute_historical_context`, `_estimar_analise_preditiva` e importação em lote CSV passaram a cruzar o acervo real visível sem o multiplicador artificial `* 7`, sem margem estática `0.08` e sem o juiz padrão hardcoded `Dr. Rafael De Amorim`.
- **Arquivos Criados / Modificados:**
  - `backend/app/core/nlp_engine.py` - Novo motor NLP e estatístico local.
  - `backend/app/schemas/contracts.py` e `backend/app/schemas/__init__.py` - `PrecedenteSimilarSchema` e expansão retrocompatível de `ContextoHistoricoSchema`.
  - `backend/app/core/ai_gateway.py` e `backend/app/routers/processos.py` - Integração completa em upload PDF, CSV e cadastro/edição manual.
  - `backend/tests/test_etapa4_nlp_e_similaridade.py` - Suíte exaustiva com 6 novos testes validando TF-IDF/BM25, extração dinâmica, sumarização, Wilson e fluxos da API.
- **Como Testar / Executar Localmente:**
  - PowerShell: `$env:PYTHONPATH="backend"; .\.venv\Scripts\pytest backend/tests/ -v` (**60 testes aprovados**).
  - Front-end: `cd frontend; npm run build`.

---

### [2026-11-21] — Etapa 5: RAG Jurídico (Gemini + Precedentes Reais), Cache SHA-256, Extrator PDF Expandido e Microsserviço `ai_engine:8001`
- **Branch:** `dev` (`VictorSamyr/JuriVision-Pro`)
- **Autor / Dupla:** Victor Samyr
- **Pacote da EAP / Requisitos:** Etapa 5 do Roadmap, EAP 1.4.3, RF-02, RF-05, RF-06, ADR-001, ADR-002
- **Resumo da Mudança:**
  1. **RAG Jurídico com Precedentes Reais (`backend/app/core/nlp_engine.py`, `backend/app/core/ai_gateway.py`):** criação de `build_rag_precedents_context` e `synthesize_local_rag_tendencia`. O `GeminiAIAdapter` passa a injetar no prompt os Top-5 precedentes similares recuperados via `TF-IDF + BM25` (CNJs, resultados históricos, prazos, teses e Intervalo de Wilson) sempre após a barreira `AnonimizadorLGPD`; no modo offline, `LocalDeterministicFallbackAdapter` também referencia os Top-3 precedentes similares na tendência de julgamento.
  2. **Cache Persistente em Memória SHA-256 (`GeminiAIAdapter`):** deduplicação por hash `SHA-256(modelo + texto_higienizado + contexto_rag)` com limite FIFO de 256 entradas, evitando chamadas repetidas ao Gemini para análises equivalentes.
  3. **Extrator Documental PDF Expandido (`ExtratorDocumental`):** suporte adicional a arrays de texto `[(...)] TJ`, metadados `/ActualText` e `/Contents` e descompressão automática de streams `FlateDecode` via `zlib`.
  4. **Ativação do Microsserviço HTTP `ai_engine:8001` (`ai_engine/worker.py`, `ai_engine/requirements.txt`):** servidor FastAPI/Uvicorn real expondo `GET /health` e `POST /internal/v1/analyze` com suporte ao núcleo do monorepo ou fallback standalone e sanitização LGPD na ida e na volta do `ResilientAIGateway`.
  5. **Planejamento Futuro Multi-Provedor (`ARCHITECTURE.md` — ADR-002):** documentada a expansão futura sobre `AIGatewayPort` para adaptadores **Ollama / OpenAI-API** (`OllamaAIAdapter` / `OpenAICompatibleAdapter` para modelos *self-hosted* como `Qwen 2.5` e `Llama 3.1`), mantendo o foco prático atual em **Gemini RAG + Motor Estatístico Local**.
- **Arquivos Criados / Modificados:**
  - `backend/app/core/nlp_engine.py` - Funções `build_rag_precedents_context` e `synthesize_local_rag_tendencia`.
  - `backend/app/core/ai_gateway.py` - `ExtratorDocumental` expandido, RAG Jurídico com cache SHA-256 no `GeminiAIAdapter`, síntese RAG local e sanitização completa de saída no `ResilientAIGateway`.
  - `ai_engine/worker.py` e `ai_engine/requirements.txt` - Microsserviço FastAPI HTTP funcional na porta `8001`.
  - `ARCHITECTURE.md` - Atualização da `ADR-002` com RAG Jurídico e roadmap arquitetural multi-provedor.
  - `backend/tests/test_etapa5_rag_e_ai_engine.py` - Suíte exaustiva com 6 novos testes cobrindo RAG, cache SHA-256, `ai_engine:8001`, streams PDF e fluxo E2E de upload.
- **Como Testar / Executar Localmente:**
  - PowerShell: `$env:PYTHONPATH="backend"; .\.venv\Scripts\pytest backend/tests/ -v` (**66 testes aprovados**).
  - Front-end: `cd frontend; npm run build`.
