# Diário de Bordo Individual — Ygor Vasconcelos

- **Integrante:** Ygor Vasconcelos
- **Papel:** Dupla 3 — Dados e Inteligência Artificial / Front-end & Integrações
- **Pacotes da EAP de Referência:** EAP 1.3.3 (Interface Web Front-end), EAP 1.4 (Inteligência e Dados), EAP 1.5.1 (Acessibilidade e Usabilidade - WCAG 2.2 AA / ISO 9241)
- **Projeto:** JuriVision — Plataforma de Jurimetria Preditiva (UFAL)
- **Branch de Trabalho:** `FrontEnd/Ygor`

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
