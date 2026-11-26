# Roteiro de Apresentação e Tour pelo JuriVision (3 Apresentadores)

> **Formato:** Até **15 min** de apresentação + **5 min** para dúvidas e comentários  
> **Foco principal:** Produto desenvolvido (proposta, dor do negócio e demonstração ao vivo)

---

## Visão Geral e Cronograma (15 min + 5 min Q&A)

| Tempo | Duração | Etapa e Foco | Responsável |
| :---: | :---: | :--- | :---: |
| **00:00 – 01:45** | 1m45 | **Dor do Negócio e Proposta de Valor** (sem slide pesado; direto na abertura do sistema) | **Apresentador 1** |
| **01:45 – 04:30** | 2m45 | **Tour Parte 1:** Landing Page, Onboarding Freemium, Pesquisa, LGPD ao vivo, DataJud e PDF | **Apresentador 1** |
| **04:30 – 09:00** | 4m30 | **Tour Parte 2:** Análise Jurimétrica (KPIs sem distorção, gráficos e *drill-down*) | **Apresentador 2** |
| **09:00 – 12:00** | 3m00 | **Tour Parte 3:** Análise de Petição (Pipeline 6 etapas, LGPD, RAG local e fluxo `FREE → PRO`) | **Apresentador 3** |
| **12:00 – 14:15** | 2m15 | **Tour Parte 4:** Comparador de Peças (Confronto Inicial vs. Contestação — Art. 357 CPC) | **Apresentador 3** |
| **14:15 – 15:00** | 0m45 | **Fechamento Executivo** e abertura para perguntas | **Apresentador 3** |
| **15:00 – 20:00** | 5m00 | **Dúvidas e Comentários** | **Todos** |

---

## Checklist Rápido Antes de Iniciar (2 minutos)

1. **Subir Back-end e Front-end** com o banco local (`jurivision_local.sqlite3`) já populado com os 91 julgados:
   * **Back-end:**
     ```powershell
     .\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --port 8000
     ```
   * **Front-end:**
     ```powershell
     cd frontend ; npm run dev
     ```
2. **Navegador:** Abrir `http://localhost:5173` em **aba anônima** (para exibir a animação inicial de abertura do *JuriVision*). Deixar `http://localhost:8000/docs` (Swagger) aberto em uma segunda aba apenas como apoio para perguntas técnicas.
3. **Contingência para o DataJud:** Ter 1 número CNJ do TJAL copiado no bloco de notas. Se a API pública do CNJ estiver lenta ou retornar HTTP `429` na hora, **não trave esperando**: comente o tratamento resiliente (o sistema avisa e nunca inventa dados) e siga nos julgados já indexados.

---

## Roteiro Completo — Tour pelo Produto e Falas

### Bloco 1 — Dor do Negócio e Proposta *(00:00 – 01:45 | Apresentador 1)*

* **[NA TELA]:** Deixar a **Landing Page** do *JuriVision* visível logo após a intro animada.
* **[FALA — Apresentador 1]:**
  > "Boa tarde a todos aqui presentes, eu me chamo Lucas Gabriel, nós somos a Equipe Epsilon e estou acompanhado pelo meus colegas Victor Samyr e Gabriel Damião para apresentarmos para vocês o nosso projeto da disciplina de Gerência de Projetos, lecionada pelo Prof. Rafael Amorim, o **JuriVision**, uma plataforma web analítica e preditiva desenvolvida para a gestão estratégica de processos jurídicos para advogados e escritórios de advocacia.
  >
  > Antes de navegar pelo sistema, vale olhar para a dor real que motivou a criação do nosso produto. Na rotina de um escritório de advocacia ou de um advogado em si, tomar decisão ainda depende muito de trabalho braçal e de intuição. O advogado precisa consultar portais fragmentados de tribunais, ler dezenas de páginas para extrair padrões de julgamento e, muitas vezes, acaba definindo acordos ou teses sem saber qual é o histórico real daquele magistrado ou daquela vara para o tema em questão e no fim perde-se muito tempo com tudo isso.
  >
  > Além disso, existe um risco silencioso crescente na era da IA: muitos profissionais estão colocando petições inteiras e documentos de processos — cheios de CPFs, nomes e dados sensíveis de clientes — diretamente em ferramentas públicas de inteligência artificial, criando um passivo grave frente à **LGPD**.
  >
  > O **JuriVision** nasce exatamente para resolver esses três gargalos em um único fluxo: centralizar a pesquisa jurisprudencial com integração oficial ao DataJud do CNJ, entregar jurimetria transparente e auditável sobre o histórico decisório, e processar petições e contestações com uma **barreira local de anonimização LGPD** antes de qualquer análise automatizada."

---

### Bloco 2 — Tour Parte 1: Onboarding, Pesquisa, LGPD ao Vivo e PDF *(01:45 – 04:30 | Apresentador 1)*

* **[NA TELA]:** Rolar rapidamente pela Landing Page, clicar em **Criar conta gratuita** (ou **Entrar** com uma conta rápida usando OAB fictícia, ex.: `55555/AL`), destacando no cabeçalho o selo **`Plano FREE · 0/3`**. Entrar na aba **Pesquisa Jurisprudencial**.

* **[FALA — Apresentador 1]:**

  > "Entrando na plataforma, o usuário já inicia no modelo Freemium, com controle multiusuário e cota visível no topo da tela.
  >
  > Aqui na **Pesquisa Jurisprudencial**, o advogado consulta a base de julgados com busca textual e filtros combinados por assunto e magistrado, ordenados diretamente no servidor. Se encontrar um precedente relevante, ele pode favoritar na coleção pessoal com um clique em **Salvar**.
  >
  > Mas quero destacar dois diferenciais críticos dessa tela. Primeiro, a **integração oficial com o DataJud do CNJ**: temos tanto a consulta pontual por número CNJ de 20 dígitos quanto a sincronização em lote por assunto. E por rigor técnico, se a API pública do tribunal estiver instável, o sistema informa claramente ao usuário e jamais fabrica dados fictícios.
  >
  > Segundo, a **proteção de dados na origem**."

* **[NA TELA]:** Clicar em **Cadastrar julgado**, digitar um nome completo fictício e um CPF (ex.: `123.456.789-00`), apontar para a **Prévia de anonimização** mascarando os dados em tempo real, fechar o modal, clicar em **Ler decisão** em um julgado existente e clicar em **Exportar PDF**.

* **[FALA — Apresentador 1]:**

  > "Reparem que, ao cadastrar ou editar um julgado, o sistema exibe uma **prévia de anonimização em tempo real**: nomes de pessoas físicas e CPFs são mascarados antes mesmo da gravação no banco, enquanto razões sociais de empresas rés são preservadas para manter o valor analítico. Ao abrir **Ler decisão**, temos os metadados higienizados e a opção de **Exportar PDF**, gerando na hora um relatório pronto para despacho ou reunião.
  >
  > Agora que vimos como a base é alimentada com segurança, passo a palavra para *[Victor Samyr]*, para mostrar como esses dados se transformam em inteligência visual na Análise Jurimétrica."

---

### Bloco 3 — Tour Parte 2: Análise Jurimétrica e Rigor Estatístico *(04:30 – 09:00 | Apresentador 2)*

* **[NA TELA]:** Clicar na aba **Análise Jurimétrica**.
* **[FALA — Apresentador 2]:**
  > "Obrigado, *[nome do Apresentador 1]*. Aqui na **Análise Jurimétrica**, nosso foco foi construir um painel que ajude o advogado a decidir com base em evidências, mas sem cair em armadilhas estatísticas comuns em ferramentas de BI.
  >
  > Olhando para os quatro indicadores no topo, há uma decisão metodológica importante: a **Proporção Favorável** considera exclusivamente a soma de *Procedentes* e *Acordos* dividida pelos processos efetivamente **Decididos**. Já os casos **Em Análise** — como petições recém-submetidas — ficam isolados em um card próprio. Assim, uma triagem em andamento nunca distorce artificialmente a taxa de êxito do escritório."
* **[NA TELA]:** Passar o cursor pelo gráfico de rosca (*Desfecho das Decisões*), ir ao gráfico **Perfil Decisório por Magistrado** e alternar o seletor entre **Quantidade** e **Percentual (%)**.
* **[FALA — Apresentador 2]:**
  > "Descendo para os gráficos interativos, temos a distribuição geral dos desfechos e o **Perfil Decisório por Magistrado**. Aqui o advogado pode alternar entre **Quantidade absoluta** e **Percentual**. Isso é essencial na prática jurídica: um juiz com 10 decisões procedentes em 12 julgadas tem um perfil muito diferente de outro com 10 procedentes em 100, e a leitura percentual evita falsas impressões."
* **[NA TELA]:** Ir ao gráfico **Panorama por Assunto**, alternar entre **Volume** e **Taxa Favorável (%)**, clicar em uma barra (ex.: **Dano Moral**) mostrando o *drill-down* para a Pesquisa já filtrada, voltar ao painel e rolar rapidamente até a **Amostra de Julgados** e a **Nota Metodológica**.
* **[FALA — Apresentador 2]:**
  > "No **Panorama por Assunto**, além de alternar entre volume e taxa favorável, o gráfico funciona como ferramenta de navegação: ao clicar diretamente na barra de *Dano Moral*, o sistema nos leva para a Pesquisa Jurisprudencial já filtrada naquele tema, permitindo auditar caso a caso. No rodapé do painel, mantemos ainda a amostra de lastro e a **Nota Metodológica**, deixando explícito o tamanho da amostra analisada.
  >
  > Com o cenário histórico mapeado, passo agora para o *[nome do Apresentador 3]* mostrar como o sistema atua na análise de novas petições e no confronto entre peças."

---

### Bloco 4 — Tour Parte 3: Análise de Petição, Pipeline LGPD e Freemium *(09:00 – 12:00 | Apresentador 3)*

* **[NA TELA]:** Clicar na aba **Análise de Petição** e clicar em **Testar petição de exemplo** (ou fazer upload do PDF preparado).
* **[FALA — Apresentador 3]:**
  > "Obrigado, *[nome do Apresentador 2]*. Quando o advogado precisa avaliar uma petição inicial antes do protocolo ou estudar um processo que acabou de chegar, ele entra na **Análise de Petição**.
  >
  > Ao submeter o documento, o sistema dispara um **pipeline auditável de 6 etapas**: primeiro aplica a barreira de **Sigilo de Dados (LGPD)** localmente; em seguida extrai metadados como juízo, comarca e tema; busca precedentes semelhantes no acervo por meio de recuperação híbrida (`TF-IDF` + `Okapi BM25`); e consolida o parecer comparativo."
* **[NA TELA]:** Mostrar o dossiê gerado: dados pessoais mascarados, precedentes similares ranqueados e o card da **Tese Estratégica** protegido com *blur* (plano FREE). Clicar no botão de upgrade, ativar o **Plano PRO** e mostrar o desbloqueio imediato da tese e da aba **Planilha CSV**.
* **[FALA — Apresentador 3]:**
  > "No dossiê gerado, observem que qualquer CPF ou nome civil foi bloqueado antes mesmo de sair do servidor. O sistema exibe os precedentes mais próximos com índice de similaridade e métricas estimadas.
  >
  > Aqui também demonstramos a regra de negócio do produto: no **Plano FREE**, o advogado tem acesso ao diagnóstico e aos precedentes, enquanto a **tese estratégica recomendada** fica protegida. Ao ativar o **Plano PRO**, a tese é desbloqueada instantaneamente e a aba de importação em lote via **Planilha CSV** passa a ficar disponível no menu."

---

### Bloco 5 — Tour Parte 4: Comparador de Peças (CPC) e Fechamento *(12:00 – 15:00 | Apresentador 3)*

* **[NA TELA]:** Clicar na aba **Comparador de Peças** e, na seção *Demonstração guiada*, clicar em **Comparar peças do exemplo**.
* **[FALA — Apresentador 3]:**
  > "Por fim, apresentamos uma funcionalidade pensada diretamente para a fase de saneamento e organização do processo, prevista no **Artigo 357 do Código de Processo Civil**: o **Comparador de Peças**.
  >
  > Em vez de o advogado abrir dois PDFs lado a lado para cruzar manualmente o que o autor pediu e o que o réu rebateu, o motor confronta a **Petição Inicial** contra a **Contestação** e organiza os pontos em um visualizador de **três colunas**."
* **[NA TELA]:** Clicar nos filtros **Divergentes**, **Omissões (Art. 341)**, **Fato Novo Defesa (Art. 350)** e **Convergentes**, apontando a citação exata dos trechos e números de página de cada peça.
* **[FALA — Apresentador 3]:**
  > "Com os filtros no topo, isolamos rapidamente os pontos **Divergentes**, as **Omissões da defesa** — que pela regra do Artigo 341 do CPC podem gerar presunção de veracidade —, os **Fatos Novos** alegados pelo réu (Artigo 350) e os pontos **Convergentes**, sempre citando o trecho literal e a página exata em cada documento.
  >
  > Para encerrar, resumimos o *JuriVision* em três compromissos de engenharia: **privacidade por design**, com LGPD aplicada localmente antes de qualquer modelo; **resiliência operacional**, operando mesmo se serviços externos como DataJud ou Gemini ficarem indisponíveis; e **transparência estatística**, sem dados inventados.
  >
  > Muito obrigado a todos. Ficamos agora à disposição para as dúvidas e comentários."

---

## Guia Rápido para os 5 Minutos de Perguntas (Q&A)

* **Se perguntarem sobre a veracidade dos dados / base inicial *(Apresentador 1 ou 2)*:**
  > *"Por padrão (`SEED_DEMO_DATA=false`), o sistema sobe vazio e aceita apenas registros vindos do DataJud (CNJ), uploads de PDF/CSV ou cadastros manuais. Para a demonstração de hoje, usamos uma base local populada com julgados reais/de teste para que os gráficos tivessem densidade estatística."*
* **Se perguntarem o que acontece se a API do Gemini falhar ou ficar sem chave *(Apresentador 3)*:**
  > *"Implementamos um gateway resiliente (`ResilientAIGateway`) seguindo o padrão Port & Adapter. Se o Gemini retornar erro 503, timeout ou estiver offline, o sistema aciona automaticamente um motor determinístico local baseado em `TF-IDF`, `Okapi BM25` e regras processuais, mantendo a aplicação 100% funcional."*
* **Se perguntarem sobre qualidade de software, segurança e testes *(Qualquer integrante)*:**
  > *"Além do isolamento multiusuário via JWT e chaves estrangeiras no banco, o projeto conta com **150 testes automatizados (`pytest`)** validando contratos REST, barreira LGPD, saneamento estatístico, motor de similaridade, regras Freemium, Comparador de Peças e critérios de acessibilidade WCAG 2.2 AA."*