# Snapshot Histórico: Protótipo Visual Inicial (v0 - Legal Editorial)

**Data de Arquivamento:** 05/11/2026  
**Contexto:** Fase de Concepção e Setup Visual Inicial — Sprint 1 (Pré-Replanejamento)  
**Equipe:** Equipe Epsilon — Gerência de Projetos (UFAL)

---

## 1. Objetivo deste Snapshot

Este diretório contém a cópia integral e preservada da primeira versão da interface visual do **JuriVision**.

Conforme deliberado no replanejamento estratégico de **05/11/2026**, esta versão foi arquivada para:
1. **Preservar a memória histórica do projeto:** Garantir rastreabilidade de design para a disciplina acadêmica.
2. **Consultas futuras:** Permitir que qualquer membro da equipe ou o professor inspecione o conceito editorial original.
3. **Desacoplamento do MVP:** Permitir que a nova interface ativa em `frontend/index.html` seja refatorada cirurgicamente com foco em dados reais da API, eliminando métricas estáticas e componentes conceituais sem perder o trabalho gráfico anterior.

---

## 2. Conteúdo Preservado

- `index.html`: Estrutura HTML completa com 6 abas de navegação (Visão Geral, Ingestão, Jurimetria, Grafo, Precedentes e Auditoria).
- `app.js`: Lógica original em JavaScript Vanilla com dados de demonstração e mocks.
- `design-tokens.css`: Sistema de variáveis CSS (tokens de cor, tipografia Fraunces/Plus Jakarta Sans, espaçamentos).
- `api.js`: Camada inicial de serviços de integração.

---

## 3. Como Visualizar

Para inspecionar visualmente este protótipo inicial:
1. Dê um duplo clique no arquivo [`index.html`](index.html) diretamente no seu explorador de arquivos; ou
2. Abra-o no navegador de sua preferência (`file:///.../frontend/versions/v0_prototipo_editorial/index.html`).

> **Nota:** Esta versão histórica utiliza dados estáticos de demonstração e não está conectada ao backend FastAPI ativo.
