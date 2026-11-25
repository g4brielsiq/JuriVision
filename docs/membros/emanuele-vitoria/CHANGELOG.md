# Diário de Bordo Individual — Emanuele Vitória

- **Integrante:** Emanuele Vitória
- **Papel:** Dupla 1 — Front-end e UI/UX
- **Pacotes da EAP de Referência:** EAP 1.3.3 (Interface Web Front-end) e RNF-04/RNF-09 (Usabilidade e Acessibilidade)
- **Projeto:** JuriVision — Plataforma de Jurimetria Preditiva (UFAL)

---

## 📜 Histórico de Contribuições (Sprint 1)

### [2026-11-05] — Entrega e Validação do MVP (Sprint 1)
- **Branch de Atuação:** `feat/sprint1-integracao-dev`
- **Atividades Realizadas:**
- Concepção e implementação da direção visual Legal Editorial + Legal Intelligence.
- Desenvolvimento dos cartões documentais de decisão e tabela comparativa na visualização de resultados.
- Garantia de acessibilidade semântica WCAG 2.2 AA e WAI-ARIA 1.2 nos componentes visuais.
- **Status:** Entregue e homologado com 100% de testes automatizados aprovados.

### [2026-11-16] — Cadastro e Edição Manual de Processos (Back-end)
- **Branch de Atuação:** `feat/cadastro-edicao-processos`
- **Atividades Realizadas:**
- Implementação das rotas `POST /api/v1/processos` e `PUT /api/v1/processos/{id}` com anonimização LGPD obrigatória.
- Criação de 9 testes automatizados (CT-10 a CT-13) e documentação do contrato na Seção 8.5.1 do `ARCHITECTURE.md`.
- **Status:** Aguardando revisão (PR para `dev`).

### [2026-11-24] — Processamento de Documentos e NLP (Card #18)
- **Branch de Atuação:** `Processamento-de-documentos-e-NLP/manu`
- **Atividades Realizadas:**
- Criação do módulo `nlp_processual.py`: limpeza de texto, identificação de informações processuais, classificação por assunto com confiança, características processuais e resumo estruturado.
- Remoção dos dados fictícios que eram preenchidos quando a informação não existia no documento.
- Criação de 31 testes automatizados (CT-NLP-01 a CT-NLP-07), conjunto de petições anotadas e script de avaliação de qualidade.
- **Status:** Em desenvolvimento local (ainda sem PR).
