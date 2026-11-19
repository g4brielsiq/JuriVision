# Governança de Contribuição Individual — Equipe Epsilon (JuriVision)

**Disciplina:** Gerência de Projetos — Universidade Federal de Alagoas (UFAL)  
**Professor Avaliador:** Rafael De Amorim Silva  
**Data de Consolidação:** 09/11/2026 (Consolidação do MVP — Sprint 1)

---

## 1. Finalidade deste Diretório

Em conformidade com as diretrizes da disciplina de Gerência de Projetos, este diretório centraliza os **registros individuais de atividade, desenvolvimento e responsabilidade técnica dos integrantes ativos** da Equipe Epsilon que efetivamente implementaram e entregaram o MVP da Plataforma JuriVision.

Este documento tem valor avaliativo para:
1. Comprovar a participação e entrega contínua dos membros no projeto.
2. Mapear de forma inequívoca os pacotes da EAP, decisões arquiteturais e commits aos seus respectivos autores.
3. Documentar a consolidação e absorção de responsabilidades técnicas pela equipe ativa.

---

## 2. Quadro de Responsabilidade Técnica da Equipe Efetiva

Diante da ausência de contribuições práticas por parte de integrantes previstos na concepção teórica inicial, a totalidade do escopo do MVP (Engenharia de Requisitos, Arquitetura, Full-Stack, Barreira LGPD, Integrações DataJud/Gemini e Qualidade) foi integralmente conduzida, implementada e homologada pelos **3 integrantes ativos** abaixo:

| Integrante | Papel no Projeto | Pacotes da EAP de Atuação | Diário Individual |
| :--- | :--- | :--- | :--- |
| **Victor Samyr** | Engenharia de Back-end, Arquitetura & Governança de Dados | EAP 1.3.1 (Armazenamento), EAP 1.3.2 (API Core), EAP 1.4.1 (Barreira LGPD) | [`victor-samyr/CHANGELOG.md`](./victor-samyr/CHANGELOG.md) |
| **Gabriel Damião** | Engenharia de Back-end, Integração DataJud & Demonstração | EAP 1.3.2 (API REST), EAP 1.4.2 (Integração DataJud), EAP 1.5.2 (Deploy) | [`gabriel-damiao/CHANGELOG.md`](./gabriel-damiao/CHANGELOG.md) |
| **Lucas Gabriel** | Responsável Técnico, Engenharia Front-end, Dados & IA | EAP 1.1/1.2 (Gerência/Requisitos), EAP 1.3.3 (UI/UX), EAP 1.4.3 (Gemini/NLP), EAP 1.5.1 (Acessibilidade) | [`lucas-gabriel/CHANGELOG.md`](./lucas-gabriel/CHANGELOG.md) |

---

## 3. Absorção de Responsabilidades e Centralização Técnica

Conforme deliberado na consolidação oficial da equipe:
- **Camada de Front-end, Experiência do Usuário, Requisitos e IA:** O integrante **Lucas Gabriel** assumiu formalmente como **Responsável Técnico**, centralizando a arquitetura e execução da interface (*Legal Editorial + Legal Intelligence*), a conformidade com WCAG 2.2 AA / WAI-ARIA 1.2, a esteira de dados/NLP (Google AI Studio - Gemini Free Tier) e o alinhamento com a EAP/matriz RACI.
- **Camada de Back-end, Persistência e Integrações Oficiais:** Os integrantes **Victor Samyr** e **Gabriel Damião** conduziram e implementaram o núcleo da API FastAPI, a conformidade determinística da Barreira LGPD (Art. 12 da Lei 13.709/2018), a resiliência dual do banco de dados (PostgreSQL + SQLite) e o cliente oficial assíncrono para a API Pública do DataJud (CNJ/TJAL).

---

## 4. Estrutura dos Diários de Bordo Individuais

Cada integrante mantém seu histórico detalhado em sua respectiva pasta, registrando tarefas, branches, commits e impactos na qualidade do software.
