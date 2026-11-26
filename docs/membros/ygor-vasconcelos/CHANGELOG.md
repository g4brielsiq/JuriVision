# Diário de Bordo Individual — Ygor Vasconcelos

- **Integrante:** Ygor Vasconcelos
- **Papel:** Dupla 3 — Dados e Inteligência Artificial / Front-end & Integrações
- **Pacotes da EAP de Referência:** EAP 1.3.3 (Interface Web Front-end), EAP 1.4 (Inteligência e Dados), EAP 1.5.1 (Acessibilidade e Usabilidade - WCAG 2.2 AA / ISO 9241)
- **Projeto:** JuriVision — Plataforma de Jurimetria Preditiva (UFAL)
- **Branch de Trabalho:** `Comparador/Ygor` (anteriormente `FrontEnd/Ygor`)

---

## 📜 Histórico Contínuo de Implementações e Atividades

### [2026-11-19] — Inicialização do Ciclo de Desenvolvimento e Sincronização com `origin/dev`
- **Branch:** `FrontEnd/Ygor`
- **Contexto:** Alinhamento de baseline do repositório local com o estado consolidado da branch `dev` (`8847430`).
- **Atividades Realizadas:**
  1. Leitura minuciosa e auditoria de toda a base documental do projeto (`docs/`, `ARCHITECTURE.md`, `agent.md`).
  2. Sincronização estrita da branch local com as últimas entregas da equipe (cadastro/edição de processos, barreiras LGPD e injeção de token Bearer).
  3. Criação deste Diário de Bordo Individual em conformidade com as exigências de governança da disciplina (Prof. Rafael De Amorim Silva).
- **Status:** Baseline pronta e documentada para início das próximas etapas de desenvolvimento.

### [2026-11-19] - Cadastro de advogados

- **Branch:** `FrontEnd/Ygor`
- A ação **Criar conta** abre o formulário de cadastro na janela de conta, acessível por teclado. O formulário consome a API real e exibe progresso, confirmação e erros.
- A API valida e normaliza os dados, rejeita e-mails e inscrições duplicados e grava a senha como hash. Após o cadastro, o login recebe o e-mail da nova conta.
- O contrato e o exemplo de uso estão em [REGISTER_ADVICE.md](./REGISTER_ADVICE.md). Os testes de contrato cobrem cadastro, login, duplicidade e validação de campos.

### [2026-11-19] - Cadastro e edição de julgados na interface

- **Branch:** `FrontEnd/Ygor`
- A pesquisa ganhou a ação **Cadastrar julgado**, integrada ao `POST /api/v1/processos`. A leitura da decisão ganhou a ação **Editar julgado**, integrada ao `PUT /api/v1/processos/{id}`. O formulário de edição recupera os dados salvos, incluindo resultado e data do julgamento.
- A prévia é atualizada ao editar as partes ou a síntese. O novo endpoint usa a mesma rotina de anonimização do salvamento e processa o rascunho sem gravá-lo.
- **Verificação:** suíte completa do backend e contratos HTTP aprovada com **33 testes (`33 passed` no `pytest`)**, quatro testes estáticos de acessibilidade aprovados e build de produção do frontend (`npm run build`) validado sem erros.
- O fluxo e o exemplo fictício para teste estão no [README](../../../README.md#36-cadastro-e-edição-de-julgados).

### [2026-11-22] - Visualizador Comparativo de Peças Jurídicas (Petição Inicial vs. Contestação)

- **Branch:** `Comparador/Ygor`
- **Contexto:** Implementação do módulo completo de saneamento e organização do processo (Art. 357 do CPC), permitindo o confronto analítico bidirecional entre Petição Inicial e Contestação com jurimetria granular e visualizador lado a lado (*Split-View*).
- **Atividades Realizadas e Entregas por Etapa:**
  1. **Etapa 1 (Fundação & Contratos):**
     - Criação do schema contratual Pydantic v2 em `backend/app/schemas/comparacao.py` (`StatusTese`, `TipoTese`, `PontoControvertido`, `ResultadoComparacaoPecas`).
     - Extensão do `ExtratorDocumental` em `backend/app/core/ai_gateway.py` com extração de PDF página a página injetando marcadores `[PÁG XX]` e segmentação estrutural por macro-seções (Fatos, Preliminares, Mérito, Tutela, Provas, Pedidos).
     - Implementação da rota `POST /api/v1/processos/comparar-pecas` em `backend/app/routers/processos.py` com barreira obrigatória de desidentificação LGPD (`AnonimizadorLGPD.sanitize_text` sob `RN-01`) e validações de integridade (`%PDF-`, limite de 15MB sob `RN-04`/`SEC-05`).
  2. **Etapa 2 (Motor Bidirecional de IA & Fallback Determinístico Local):**
     - Adição do método `comparar_pecas` à interface `AIGatewayPort`.
     - Implementação do motor heurístico local determinístico em `LocalDeterministicFallbackAdapter.comparar_pecas`:
       - Varredura direta (Autor $\rightarrow$ Réu) com extração de datas (`\d{2}/\d{2}/\d{4}`), valores monetários (`R\$`), mérito, inversão do ônus da prova e pedidos, classificando em convergências, divergências e omissões específicas (art. 341 do CPC).
       - Varredura reversa (Réu $\rightarrow$ Autor) identificando preliminares e fatos novos extintivos, impeditivos ou modificativos da defesa (art. 350 do CPC / `fato_novo_ou_extintivo_reu` com `trecho_autor=None`).
     - Implementação do `GeminiAIAdapter.comparar_pecas` com prompt estruturado de Juiz Saneador, saída JSON via `generationConfig` e fallback transparente para o motor local.
  3. **Etapa 3 (Jurimetria Granular por Argumento):**
     - Implementação de `_aplicar_jurimetria_granular` cruzando histórico de decisões do magistrado e temas da comarca armazenados no banco relacional (`Processo`, `AnalisePreditiva`) com a força probatória relativa (`forca_probatoria_autor` vs `forca_probatoria_reu`).
     - Calibragem percentual de procedência por tese no intervalo `[0.0, 100.0]`, com elevação para omissões (presunção relativa de veracidade do art. 341 do CPC) e geração de orientação estratégica em `impacto_processual` para a réplica.
  4. **Etapa 4 (Interface Visual Split-View & Acessibilidade WCAG 2.2 AA):**
     - Inclusão da nova aba "Comparador de Peças" (`#panel-comparador`) na barra lateral com suporte a navegação por teclado (WAI-ARIA Tab Pattern).
     - Componente de upload duplo com drag & drop e botão de demonstração rápida em 1 clique (`btn-demo-comparador`).
     - Visualizador *Split-View* de 3 colunas sincronizadas (`coluna-peticao-inicial`, `coluna-pontos-controvertidos`, `coluna-contestacao`): ao selecionar qualquer tese no feed central, ambas as colunas laterais rolam suavemente (`scrollIntoView`) e destacam o trecho literal confrontado com código de cores semântico.
     - Barra de filtros rápidos por Status da tese e por Eixo Jurídico.
- **Verificação Automatizada:**
  - Suíte de testes do backend executada com **42 testes aprovados (`42 passed` no `pytest`)**, incluindo 9 novos testes em `backend/tests/test_comparador_pecas.py` e preservação integral dos 11 testes originais de regras de negócio (`test_api_contracts.py`).
  - Quatro testes automatizados de acessibilidade (`test_frontend_accessibility.py`) cobrindo WAI-ARIA, WCAG 2.2 AA e contratos REST atualizados.
  - Build de produção do frontend (`npm run build`) validado sem erros em 267ms.

### [2026-11-23] - Disponibilidade da estimativa e identificação do motor no comparador

- **Branch** `Comparador/Ygor`
- O backend passou a calcular a estimativa de procedência com pelo menos cinco julgados do mesmo tema, cadastrados manualmente e com resultado procedente ou improcedente. A amostra exclui o próprio processo comparado. O cálculo usa suavização de Laplace e retirou os percentuais fixos por classificação, incluindo os 100% atribuídos às convergências.
- A API retorna `null` quando o histórico é insuficiente. A interface mostra **Estimativa indisponível** na tese e informa quantos julgados foram encontrados. A média geral só aparece quando todas as teses têm estimativa.
- O campo `motor_analise` identifica quem produziu a comparação. A interface mostra **Gemini** quando a resposta externa foi recebida e validada, ou **Análise local** quando o motor determinístico respondeu, inclusive em caso de fallback.
- **Verificação** — 46 testes aprovados com `pytest`, build de produção aprovado com `npm run build` e estados da estimativa e rótulos dos motores verificados no Chrome com resultados fictícios. Os testes automatizados simularam as respostas do Gemini, incluindo o fallback após erro HTTP.
- A regra de cálculo e o contrato atualizado estão no [plano de implementação](./plano_de_implementa_o_visualizador_comparativo_de_pe_as_jur_dicas.md).

### [2026-11-23] - Resposta estruturada do Gemini no comparador

- O adaptador passou a solicitar o JSON de síntese e teses pelo `responseJsonSchema`. O backend valida as teses e monta o resultado com identificadores, contagens e dados extraídos dos PDFs.
- A autenticação passou a usar o cabeçalho `x-goog-api-key`. Os logs do comparador indicam o status HTTP ou o tipo de erro quando acionam a análise local.
- **Verificação** — 46 testes aprovados. A rota de comparação retornou HTTP 200 com `motor_analise=gemini` e duas teses em um teste com dois PDFs fictícios e o modelo `gemini-3.5-flash-lite`.

### [2026-11-23] - Demonstração guiada do comparador

- **Branch** `Comparador/Ygor`
- A aba **Comparador de Peças** ganhou uma área de demonstração com dois casos fictícios, **Atraso de voo e despesas de hospedagem** e **Cobrança após cancelamento de assinatura**. Cada caso gera uma petição inicial e uma contestação de três páginas e as envia pela mesma rota usada no upload de peças próprias.
- O resultado inclui um guia de leitura por caso, páginas das citações e destaques nos documentos. Os filtros de status e eixo podem ser combinados, informam quantas teses estão visíveis e limpam os destaques quando a combinação fica sem resultados. Uma nova comparação reinicia os filtros.
- **Plano de implementação** — A Etapa 4 passou a incluir os casos demonstrativos, a geração dos PDFs e o roteiro de validação no navegador. A entrega usa o contrato de comparação e as regras de jurimetria já especificados nas Etapas 1 a 3. [Plano de implementação](./plano_de_implementa_o_visualizador_comparativo_de_pe_as_jur_dicas.md#demonstração-guiada)
- **Verificação** — Build de produção aprovado e 46 testes aprovados. No Chrome com o motor local, foram verificados os dois casos, a extração das seis páginas de cada comparação, a seleção de teses por teclado, os filtros combinados, o estado vazio e o upload de peças próprias.
- **Execução local** — O erro `WinError 10048` ocorreu porque a API do JuriVision já respondia na porta `8000`. A instância existente foi reaproveitada, o frontend foi iniciado na porta `5173` e ambos responderam. A intervenção foi operacional, com as portas previstas pelo projeto.

### [2026-11-24] - Integração com `origin/dev`, Limpeza de PDFs Sujos e Fallback Multi-Modelo Gemini (Card #55)

- **Branch:** `Comparador/Ygor` (finalização conjunta com Lucas Gabriel)
- Sincronização com a `dev` (incorporando os módulos `SegmentadorPeticao`/OCR da `#56` e `LimpadorTexto`/`nlp_processual` da `#18`).
- Integração de `_normalizar_peca_com_paginas` e `_extrair_trechos_comparacao` no comparador local para tratar PDFs reais com quebras de linha no meio da frase, hifenização e rodapés do PJe/e-SAJ, além de verificação de impugnação no escopo da sentença.
- Adição de cadeia de fallback entre modelos gratuitos do Gemini (`gemini-2.5-flash` $\rightarrow$ `gemini-2.5-flash-lite` $\rightarrow$ `gemini-2.0-flash`) quando ocorre `HTTP 503`.
- **Verificação:** **97 testes aprovados (`97 passed` no `pytest`)** e build de produção do frontend validado sem erros.

