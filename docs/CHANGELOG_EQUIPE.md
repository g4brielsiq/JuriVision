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
