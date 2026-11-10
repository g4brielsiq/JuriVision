# Roteiro Oficial de Apresentação e Demonstração do MVP — JuriVision

- **Projeto:** JuriVision — Plataforma de Pesquisa Jurisprudencial, Jurimetria e Análise Comparativa de Petições
- **Disciplina:** Gerência de Projetos — Instituto de Computação (UFAL) | **Professor:** Rafael De Amorim Silva
- **Equipe:** Equipe Epsilon | **Apresentador (Avaliação Parcial Remota):** Lucas Gabriel
- **Data da Apresentação:** 10/11/2026 | **Duração Alvo:** 12 a 15 minutos *(faixa sugerida pelos monitores: 10–15 min)*
- **Branch / Versão de Referência:** `main` (commit `40c231c`)

> **Diretriz dos Monitores (Norte da Apresentação):**
> Focar no **negócio** (objetivo do projeto, problemas que resolve e o que ainda falta desenvolver), executando o **fluxo principal com calma**. Detalhes técnicos devem ser aprofundados apenas se o professor ou os monitores perguntarem.

---

## 1. Estrutura e Cronograma da Apresentação (~13 min)

| Bloco | Tema | Tempo Estimado | Objetivo Principal |
| :---: | :--- | :---: | :--- |
| **1** | **Abertura e Contextualização** | `00:00 – 01:00` *(1 min)* | Apresentar você, a equipe e o propósito da apresentação parcial. |
| **2** | **Problema e Oportunidade** | `01:00 – 03:00` *(2 min)* | Mostrar as dores do dia a dia jurídico com volume documental, pesquisa e sigilo. |
| **3** | **Proposta de Valor e Visão do Produto** | `03:00 – 04:30` *(1,5 min)* | Explicar o que é o JuriVision, quem usa e seus 3 módulos visíveis. |
| **4** | **Demonstração Prática Guiada** | `04:30 – 10:30` *(6 min)* | Navegar em fluxo lógico pelo sistema real na branch `main`. |
| **5** | **Limitações Atuais e Próximos Passos** | `10:30 – 12:30` *(2 min)* | Apresentar com transparência o que falta evoluir (funcional, segurança/LGPD, IA, UX). |
| **6** | **Encerramento e Perguntas** | `12:30 – 13:15` *(45s + Q&A)* | Fechar retomando o valor do produto e abrir espaço para a banca. |

---

## 2. Alerta Rápido: O Que EVITAR Demonstrar ao Vivo na `main`

Para garantir uma demonstração fluida e sem surpresas no estado atual da branch `main` (`40c231c`) com o banco demonstrativo local:

1. **Não clicar em "Decisões Salvas"** (nem no menu lateral, nem no filtro *"Apenas decisões salvas"*): o filtro atua na página atual (8 itens mais recentes) e, como há 63 registros ordenados por data de criação, os itens pré-salvos ficam fora da página 1 e a lista aparecerá vazia.
2. **Não clicar em `Dra. Amanda Cavalcante` ou `Dr. Marcelo Lins` no painel de Jurimetria:** eles existem no banco expandido, mas o filtro de magistrado da tela de pesquisa lista apenas os 3 juízes originais (`Dr. Rafael De Amorim`, `Dra. Maria Silva`, `Dr. Carlos Souza`), fazendo o filtro automático falhar silenciosamente. Se quiser demonstrar clique no painel, clique apenas em **`Dr. Rafael De Amorim`**, **`Dra. Maria Silva`** ou **`Dr. Carlos Souza`**.
3. **Não abrir o modal "Conta" (Login) durante o fluxo principal:** os campos já vêm pré-preenchidos e a sessão já aparece conectada como exemplo; só mostre se perguntarem sobre autenticação.
4. **Não enviar PDF escaneado (imagem pura):** a leitura atual extrai texto digital (`pypdf`) e ainda não possui OCR; para demonstrar sem risco, use o botão **"Testar com petição demonstrativa (Atraso de Voo)"** ou um PDF com texto selecionável.
5. **Não afirmar recursos não implementados na `main`:**
   - Não diga que a tela gera ou exibe **"hash HMAC-SHA256"** (ela exibe a contagem de documentos e nomes ocultados pelo mascaramento LGPD).
   - Não diga que o sistema está rodando **"Machine Learning treinado"** ou **"Gemini ao vivo neste ambiente"** (o ambiente local atual roda o motor heurístico/estatístico local; o adaptador Gemini existe no código como camada plugável opcional).

---

## 3. Roteiro Falado Completo e Passo a Passo da Demonstração

### Bloco 1 — Abertura e Contextualização (`00:00 – 01:00`)

**AÇÃO NA TELA:** Compartilhar a janela do navegador já aberta em `http://localhost:5173` (na aba inicial **"Pesquisar Jurisprudência"**).

**FALA:**
> *"Bom dia, professor Rafael, bom dia monitores e colegas. Eu sou o Lucas Gabriel, e hoje vou apresentar a evolução parcial do **JuriVision**, projeto desenvolvido pela Equipe Epsilon na disciplina de Gerência de Projetos.*
> 
> *Nosso objetivo hoje é mostrar o produto do ponto de vista de negócio: qual problema real motivou o JuriVision, como a plataforma funciona na prática através de uma demonstração do fluxo principal do MVP, e também trazer com bastante transparência o que ainda é protótipo ou precisa evoluir nas próximas etapas."*

**OBSERVAÇÃO:** Fale pausadamente. Confirme no áudio/chat que a tela está visível e nítida antes de entrar no Bloco 2.

---

### Bloco 2 — Problema e Oportunidade (`01:00 – 03:00`)

**AÇÃO NA TELA:** Permanecer na tela inicial sem clicar freneticamente, deixando o visual limpo da plataforma servir de apoio.

**FALA:**
> *"O ponto de partida do JuriVision vem de uma dor muito concreta na rotina de advogados e pequenos escritórios: o tempo gasto para pesquisar decisões anteriores e analisar petições longas manualmente.*
> 
> *Quando um advogado precisa preparar uma nova ação ou avaliar os riscos de um processo, ele geralmente encontra informações espalhadas em documentos PDF extensos, portais de tribunais com buscas pouco analíticas e planilhas isoladas. Fica difícil responder perguntas simples de negócio, como: 'Em casos parecidos com este, naquela vara ou com aquele magistrado, os pedidos costumam ser aceitos ou negados? Quanto tempo costuma levar?'*
> 
> *Além disso, existe uma barreira jurídica importante hoje: muitos profissionais gostariam de usar ferramentas digitais ou inteligência artificial para resumir e organizar peças, mas não podem simplesmente jogar dados pessoais de clientes — como nomes completos, CPFs e RGs — sem cuidado com a privacidade e a LGPD.*
> 
> *É exatamente nessa oportunidade que o JuriVision nasce: transformar documentos jurídicos soltos em informação pesquisável, comparável e com indicadores objetivos para apoiar a decisão do advogado, respeitando a proteção de dados."*

**OBSERVAÇÃO:** Evite números absolutos de mercado ("economiza 80% das horas"). Mantenha a narrativa qualitativa e realista.

---

### Bloco 3 — Proposta de Valor e Visão do Produto (`03:00 – 04:30`)

**AÇÃO NA TELA:** Passar suavemente o cursor pelos 3 itens principais do menu lateral esquerdo (*Pesquisar Jurisprudência*, *Análise Jurimétrica* e *Análise de Petição*) enquanto apresenta.

**FALA:**
> *"Então, o que é o JuriVision? É uma plataforma web pensada para advogados e equipes jurídicas que reúne, em um único fluxo de trabalho, três frentes principais:*
> 
> *Primeiro, uma **área de pesquisa de jurisprudência**, onde o profissional localiza decisões por assunto, texto, magistrado ou número de processo — incluindo consulta integrada à base pública do DataJud do CNJ.*
> 
> *Segundo, um **painel de jurimetria**, que consolida os dados do acervo para mostrar distribuição por assunto, tempo estimado de tramitação e histórico de decisões por órgão julgador, sempre indicando o tamanho da amostra para evitar leituras enganosas.*
> 
> *E terceiro, um **fluxo de análise comparativa de petições**, onde o advogado envia um PDF ou importa uma planilha CSV. O sistema extrai os dados principais, aplica um filtro local de proteção para ocultar dados pessoais sensíveis, gera um resumo e compara aquele caso com o histórico disponível, permitindo baixar um relatório em PDF pronto para uso."*

---

### Bloco 4 — Demonstração Prática Guiada (`04:30 – 10:30`)

> **Fio condutor sugerido:** *"Vamos imaginar um advogado abrindo o JuriVision pela primeira vez para estudar um caso de Direito do Consumidor no TJAL."*

#### Passo 4.1 — Pesquisa Jurisprudencial e Leitura de Decisão (`04:30 – 06:00`)

**AÇÃO NA TELA:**
1. Apontar rapidamente no topo o selo verde **"Acervo TJAL sincronizado"** e na barra lateral o contador total de processos.
2. Clicar no botão rápido de pesquisa **"Responsabilidade civil · Atraso de voo"** (ou selecionar *"Responsabilidade Civil / Dano Moral"* em **Assunto** e clicar em **"Pesquisar decisões"**).
3. Mostrar rapidamente o botão **"Tabela comparativa"** e voltar para **"Cartões de decisão"**.
4. Clicar em **"Abrir decisão"** em um dos cartões retornados.
5. Na folha de leitura aberta (`#drawer-processo`), mostrar os metadados, o campo **"Polo Ativo (Anonimizado)"** (`Nome X. ***`) e a **"Síntese Factual"**. Clicar em **"← Voltar aos resultados"**.
6. Clicar em **"Limpar filtros"** para restaurar a lista completa.

**FALA:**
> *"Entrando na plataforma, o advogado já cai direto na pesquisa jurisprudencial. Aqui no topo vemos que a base do TJAL está conectada. Vamos supor que eu esteja estudando um caso de responsabilidade civil. Posso digitar termos livres aqui em cima ou usar esses atalhos de filtro por assunto e magistrado.*
> 
> *Os resultados aparecem como cartões organizados — e, se o usuário preferir uma visão mais densa para comparar vários de uma vez, pode alternar para 'Tabela comparativa' e voltar para 'Cartões'.*
> 
> *Percebam que já na listagem os nomes das partes pessoas físicas aparecem mascarados. Se eu clicar em 'Abrir decisão', o sistema abre uma folha limpa de leitura com os metadados processuais, a síntese dos fatos e a fundamentação relacionada. Isso resolve a dificuldade de ler e extrair o núcleo do caso rapidamente. Voltando para a lista e limpando os filtros..."*

**VALOR ENTREGUE:** Organização rápida do acervo e separação visual clara entre metadados oficiais, resumo factual e partes protegidas.

---

#### Passo 4.2 — Consulta Híbrida ao DataJud / CNJ (`06:00 – 07:00`)

**AÇÃO NA TELA:**
1. Na barra de busca superior (`#filtro-busca`), digitar o número CNJ `0019283-44.2025.8.02.0001` *(ou deixar vazio para usar o padrão `0710802-55.2018.8.02.0001`)*.
2. Clicar no botão **"Consultar DataJud (CNJ)"** (`#btn-consultar-datajud`).
3. Aguardar aparecer o cartão destacado abaixo da barra (`#datajud-result-box`) exibindo Tribunal, Classe, Assunto, Órgão Julgador, Data, Movimentações e a fonte no selo superior (*API Pública DataJud* ou *Acervo Local Homologado*).
4. Clicar em **"✕ Ocultar"**.

**FALA:**
> *"Um diferencial importante que implementamos foi a consulta de metadados processuais pelo número único do CNJ através do botão 'Consultar DataJud'.*
> 
> *Quando informo um número de processo e clico aqui, o sistema consulta a API pública oficial do Conselho Nacional de Justiça para trazer classe processual, assunto, órgão julgador e últimas movimentações. E se o serviço externo estiver instável, sem resposta rápida ou o número não estiver indexado lá fora, o sistema aciona automaticamente um mecanismo de contingência na base local para não deixar o advogado com erro na tela."*

**OBSERVAÇÃO:** Se houver internet e o processo existir no CNJ, aparecerá `"Consulta em Tempo Real: API Pública DataJud (CNJ)"`. Se estiver sem retorno ou usando o número do seed local `0019283-44.2025.8.02.0001`, aparecerá `"Acervo Local Homologado (Fallback Resiliente TJAL)"`. Leia exatamente o selo que aparecer na hora!

---

#### Passo 4.3 — Análise Jurimétrica / Dashboard (`07:00 – 08:30`)

**AÇÃO NA TELA:**
1. Clicar na aba lateral **"Análise Jurimétrica"** (`#btn-dashboard`).
2. Passar o mouse sobre os 4 cards superiores (*Conjunto de Decisões Analisadas*, *Proporção de Resultados Favoráveis*, *Tempo Mediano até Julgamento*, *Método de Classificação*).
3. Rolar até os dois painéis de gráficos (*por magistrado* e *por assunto*). Mostrar as barras comparativas e os gráficos Chart.js.
4. Clicar em **"Ver as X decisões →"** abaixo de **`Dr. Rafael De Amorim`** para mostrar a volta automática à pesquisa filtrada pelo magistrado; depois clicar em **"Limpar filtros"**.

**FALA:**
> *"Depois de pesquisar, o advogado pode aprofundar a visão quantitativa clicando em 'Análise Jurimétrica'.*
> 
> *Aqui consolidamos os indicadores do acervo analisado: quantidade total de decisões na base, proporção de resultados favoráveis — considerando procedentes e acordos — e estimativa de tempo até julgamento.*
> 
> *Um cuidado de negócio que tivemos nesta tela foi a transparência metodológica: todo percentual mostra exatamente quantas decisões compõem aquela conta, e deixamos claro na nota abaixo que padrão histórico serve de apoio estratégico, nunca como promessa de resultado.*
> 
> *O painel também é interativo: se eu quiser conferir exatamente quais decisões compõem o histórico do Dr. Rafael De Amorim, por exemplo, basta clicar aqui e a plataforma já me leva para a lista filtrada."*

**OBSERVAÇÃO:**
- **Lembrete:** Não clique em `Dra. Amanda Cavalcante` nem `Dr. Marcelo Lins`.
- **Se os gráficos não aparecerem (sem internet/CDN):** O sistema ainda exibe as barras proporcionais em HTML logo acima dos canvas e as tabelas analíticas em `<details>`. Mostre as barras normalmente e informe que o Chart.js depende de CDN nesta versão.

---

#### Passo 4.4 — Análise de Petição (PDF), Proteção LGPD, Lote CSV e Exportação de Relatório (`08:30 – 10:30`)

**AÇÃO NA TELA:**
1. Clicar na aba **"Análise de Petição"** (`#btn-upload`).
2. Apontar brevemente que a aba exibe um estudo comparativo inicial de referência e o painel de envio à esquerda.
3. Clicar no botão **"Testar com petição demonstrativa (Atraso de Voo)"** (`#btn-sample-pdf`).
4. Aguardar o spinner rápido e apontar no parecer atualizado à direita:
   - Selo verde de auditoria (**`LGPD: X documento(s) e Y nome(s) ocultados`**) — explicando que a petição de teste tinha CPF, RG e nome completo.
   - Campo **Polo Ativo (Anonimizado — LGPD)**: `Lucas G. ***`.
   - **Síntese Factual Automatizada**, os **4 indicadores** (Proporção Histórica, Precedentes, Tempo, Origem) e **Fundamentação Recorrente**.
5. Clicar no botão **"Exportar Relatório Analítico (PDF)"** (`#btn-result-export-pdf`) no topo do parecer; abrir rapidamente a guia/arquivo PDF gerado no navegador para comprovar que o download gera um documento real.
6. Voltar à aba do sistema e, no painel esquerdo, alternar o seletor de **"Petição em PDF"** para **"Planilha CSV"** (`#mode-btn-csv`) e clicar em **"Testar com planilha demonstrativa em lote"** (`#btn-sample-csv`).
7. Mostrar o box verde de confirmação (*Planilha incorporada ao acervo jurisprudencial*: registros lidos, adicionados e partes anonimizadas). *(Dica: clicar em "Importar outra planilha" ou deixar o resultado visível).*

**FALA:**
> *"Agora chegamos ao fluxo de análise de novos documentos, na aba 'Análise de Petição'. O sistema já carrega um modelo de estrutura de parecer para referência, e aqui à esquerda o advogado pode enviar uma petição real em PDF do computador ou rodar um teste demonstrativo.*
> 
> *Vou clicar em 'Testar com petição demonstrativa'. Essa petição simulada contém propositalmente um CPF, um RG e o nome completo da parte autora. Em poucos instantes, o backend extrai o texto, passa por uma barreira local de higienização que oculta os documentos e mascara o nome do autor — como vemos no selo verde de proteção LGPD e no campo 'Polo Ativo' —, gera uma síntese factual e cruza com os registros similares do juízo.*
> 
> *A partir desse resultado, com um clique em 'Exportar Relatório Analítico (PDF)', o advogado gera e baixa um dossiê consolidado em PDF com os dados já protegidos para compartilhar com o cliente ou com a equipe.*
> 
> *Por fim, pensando em escritórios que já têm histórico em planilhas, também implementamos a importação em lote via CSV. Alternando para 'Planilha CSV' e testando o arquivo demonstrativo em lote, o sistema lê todas as linhas, aplica o mesmo processo de ocultação de dados pessoais linha a linha e já incorpora as decisões ao acervo e ao dashboard."*

**OBSERVAÇÃO:** Esta sequência fecha exatamente no fluxo principal pedido pelos monitores, sem depender de arquivos externos no computador.

---

### Bloco 5 — Limitações Atuais e Próximos Passos (`10:30 – 12:30`)

**AÇÃO NA TELA:** Pode manter na tela do sistema ou no parecer final enquanto resume os próximos passos com franqueza.

**FALA:**
> *"Como este é o nosso MVP de avaliação parcial, fizemos também uma revisão criteriosa interna para mapear com honestidade o que já funciona e o que ainda precisa amadurecer antes de uma versão de produção.*
> 
> *Destaco quatro frentes de evolução planejadas:*
> 
> *1. **Evolução da Inteligência e Dados:** Hoje, a classificação de temas e as estimativas operam com regras heurísticas determinísticas e estatística simples no próprio backend. O serviço separado de IA que projetamos na arquitetura ainda está em estrutura inicial, e a extração de PDFs ainda não conta com OCR para documentos escaneados como imagem. Nos próximos passos, queremos evoluir o cruzamento estatístico por assunto e vara, incluir OCR e ativar plenamente a camada isolada de IA — mantendo o uso opcional de modelos externos como o Gemini apenas sobre textos já anonimizados.*
> 
> *2. **Segurança e Controle de Acesso:** Embora o sistema já possua fluxo de login e emissão de token, nesta versão de MVP as demais rotas de consulta e envio ainda não exigem verificação obrigatória de permissão em cada requisição. Além disso, precisamos limitar tamanho de upload, endurecer a sanitização de conteúdo exibido na tela e ampliar o detector LGPD para capturar também outros dados como endereços, telefones e réus pessoa física.*
> 
> *3. **Aprimoramento de Filtros e Relatórios:** Precisamos levar a filtragem de 'Decisões Salvas' e a ordenação para o servidor (para funcionar em todo o banco e não só na página atual), atualizar dinamicamente a lista de magistrados nos filtros e implementar quebra automática de várias páginas no relatório PDF exportado.*
> 
> *4. **Experiência do Usuário e Offline:** Queremos empacotar a biblioteca de gráficos localmente para não depender de internet na apresentação dos gráficos, além de finalizar ajustes visuais e de contraste que já começamos a testar em outra branch de desenvolvimento."*

**OBSERVAÇÃO:** Apresente isso de forma construtiva — mostra maturidade de engenharia e controle do escopo sem soar como um relatório de falhas.

---

### Bloco 6 — Encerramento (`12:30 – 13:15`)

**FALA:**
> *"Resumindo, hoje temos uma plataforma funcional de ponta a ponta: o advogado pesquisa jurisprudência, consulta metadados no DataJud com contingência local, visualiza métricas jurimétricas, processa PDFs e CSVs com proteção inicial de dados pessoais e exporta relatórios em PDF — tudo validado por testes automatizados.*
> 
> *Agradecemos muito a atenção, o apoio dos monitores e ficamos à disposição para perguntas do professor Rafael e da equipe."*

---

## 4. Guia de Preparação para Perguntas (Q&A da Banca)

### 4.1. Produto e Negócio

1. **Qual problema o JuriVision resolve?**
   - **Resposta curta:** Resolve o tempo gasto com análise manual de petições extensas e a falta de organização e visão estatística acessível sobre padrões de decisões jurídicas, evitando expor dados pessoais de clientes sem tratamento prévio.
   - **Aprofundamento:** Pequenos escritórios raramente têm acesso a ferramentas caras de jurimetria ou precisam conciliar pesquisa de jurisprudência, leitura de peças e organização em planilhas dispersas.
   - **Não afirmar:** Não invente métricas comerciais de economia ("economiza 70% do tempo") nem diga que o produto foi validado em escritórios reais se não houve estudo de campo.

2. **Quem é o público-alvo?**
   - **Resposta curta:** Advogados autônomos, escritórios de advocacia de pequeno/médio porte e equipes jurídicas que atuam principalmente no contencioso (no protótipo, focado em processos do TJAL).
   - **Aprofundamento:** Especialmente profissionais que lidam com demandas repetitivas (consumidor, bancário, saúde, trabalhista) e precisam preparar teses com base no histórico das varas.
   - **Não afirmar:** Não apresente como ferramenta para magistrados ou órgãos públicos sem necessidade — o fluxo de produto atual é centrado no advogado.

3. **Qual é o diferencial da solução?**
   - **Resposta curta:** Reunir pesquisa jurisprudencial integrada ao DataJud/CNJ, análise de petição e jurimetria com transparência amostral em uma interface editorial limpa, priorizando o tratamento prévio dos dados pessoais antes da análise e rodando com custo zero em infraestrutura local.
   - **Aprofundamento:** Muitos sistemas ou focam só em busca textual ou mandam documentos brutos direto para LLMs externas; aqui a arquitetura prevê a barreira local LGPD antes da camada analítica.
   - **Não afirmar:** Não afirme que a anonimização atual já é 100% blindada contra qualquer vazamento; reconheça que há melhorias planejadas.

4. **Como o sistema gera valor para um escritório jurídico?**
   - **Resposta curta:** Centraliza o acervo do escritório, acelera a triagem inicial de novas petições e fornece uma base quantitativa transparente para orientar estratégia e alinhar expectativas com o cliente por meio de relatórios em PDF.
   - **Aprofundamento:** Ao importar o histórico em CSV e enviar novas minutas em PDF, o escritório vai construindo sua própria base de conhecimento estruturada.
   - **Não afirmar:** Não prometa "previsão certa do resultado da sentença". O sistema apoia decisões com base em histórico.

---

### 4.2. Funcionalidades

1. **Como funciona a pesquisa de decisões?**
   - **Resposta curta:** Permite filtrar por texto livre (assunto, partes, número CNJ ou palavras no resumo), por tema jurídico e por magistrado, com paginação no servidor e alternância entre visualização em cartões ou tabela comparativa, além da leitura individual completa.
   - **Aprofundamento:** Há suporte também à consulta direta de um número CNJ no DataJud na mesma barra de busca.
   - **Limitação a reconhecer:** A lista de magistrados no seletor ainda é fixa e a ordenação/filtro de "Decisões Salvas" hoje atua apenas sobre a página carregada.

2. **Como os documentos são processados?**
   - **Resposta curta:** PDFs passam por validação de assinatura binária (`%PDF-`) e extração de texto digital via `pypdf`; planilhas CSV passam por validação das colunas obrigatórias. Em seguida, os textos passam pelo filtro LGPD, recebem classificação, resumo e estimativa, e são salvos no banco.
   - **Aprofundamento:** Se um arquivo enviado não for um PDF válido ou não tiver texto extraível, a API recusa com erro diagnóstico (HTTP 422).
   - **Limitação a reconhecer:** Ainda não há OCR para PDFs digitalizados apenas como imagem, nem limite máximo configurado de tamanho do arquivo no backend.

3. **De onde vêm os dados?**
   - **Resposta curta:** De três fontes no MVP: (a) carga demonstrativa inicial inspirada em comarcas e varas do TJAL (`seed`), (b) documentos PDF e planilhas CSV importados pelo usuário e (c) metadados processuais consultados na API Pública do DataJud (CNJ).
   - **Aprofundamento:** No ambiente local de demonstração, utilizamos 63 registros estruturados do TJAL (10 iniciais + 50 do script de carga expandida) e consulta sob demanda ao CNJ.
   - **Não afirmar:** Não diga que a base atual possui milhares de acórdãos reais raspados diretamente dos tribunais; os dados locais demonstrativos são sintéticos/estruturados para simular cenários realistas do TJAL.

4. **Como funciona a análise de jurimetria?**
   - **Resposta curta:** O backend consolida todos os processos cadastrados no banco, calcula a proporção de decisões favoráveis (procedentes + acordos), agrupa por magistrado e por tema, e estima o prazo médio em meses.
   - **Aprofundamento:** A tela exibe o denominador exato de cada taxa e oferece leitura acessível em tabela abaixo dos gráficos.
   - **Limitação a reconhecer:** A interface rotula *"Tempo Mediano"*, mas o cálculo atual no backend faz uma média simples das estimativas gravadas nos processos.

5. **Quais funcionalidades já estão implementadas?**
   - **Resposta curta:** Pesquisa paginada com filtros básicos, leitor de decisão, consulta DataJud com fallback, dashboard com gráficos, upload e extração de PDF/CSV com mascaramento LGPD básico, geração de relatório PDF e login com emissão de token JWT.
   - **Não afirmar:** Não apresente o serviço `ai_engine` separado ou o controle de acesso multiusuário completo como prontos.

---

### 4.3. Inteligência Artificial e Estatística

1. **O sistema utiliza inteligência artificial?**
   - **Resposta curta:** Hoje o sistema utiliza regras heurísticas determinísticas locais para classificar temas, extrair resumos e recomendar teses, mas possui uma arquitetura de adaptadores preparada para conectar modelos externos como o Google Gemini sobre textos previamente anonimizados.
   - **Aprofundamento:** Adotamos o padrão Port & Adapter: se não houver chave de API ou internet, tudo funciona localmente sem custo financeiro (R$ 0,00).
   - **Limitação a reconhecer:** Embora o adaptador para o Gemini esteja implementado e testado com mocks, no ambiente atual rodamos em modo heurístico local e ainda não validamos chamadas ao vivo contra a API do Gemini.

2. **Existe aprendizado de máquina?**
   - **Resposta curta:** Não nesta etapa do MVP. Apesar de o planejamento prever evolução com modelos estatísticos/ML (`scikit-learn`), a implementação atual usa heurísticas baseadas em palavras-chave e contagem histórica simples.
   - **Aprofundamento:** Essa escolha priorizou entregar o fluxo completo funcional e determinístico dentro do prazo acadêmico e sem custos de infraestrutura de GPU.
   - **Não afirmar:** Jamais chame a heurística atual de "rede neural", "modelo de ML treinado" ou "acurácia preditiva validada".

3. **Como os indicadores são calculados?**
   - **Resposta curta:** A taxa global no dashboard é a divisão direta de processos com resultado `Procedente` ou `Acordo` pelo total de processos na base. Já na análise de uma petição enviada, o sistema consulta a taxa de êxito histórica do magistrado identificado no banco.
   - **Limitação a reconhecer:** Na análise de petição, a filtragem histórica atual considera apenas o magistrado identificado (entre 3 nomes mapeados), ainda sem cruzar por assunto específico, e usa fator multiplicador fixo para estimar casos similares na vara e margem de confiança padrão fixa (`±8%`).

4. **Os resultados são estatisticamente confiáveis?**
   - **Resposta curta:** Refletem com precisão aritmética os dados cadastrados na base atual, mas como o acervo demonstrativo tem amostra reduzida (63 processos sintéticos/estruturados) e o cálculo individual é simplificado, servem para demonstrar o conceito do produto e não devem fundamentar decisões jurídicas reais sem ampliar a base e os métodos estatísticos.

5. **Qual é a diferença entre as heurísticas atuais e um modelo preditivo validado?**
   - **Resposta curta:** As heurísticas aplicam regras explícitas definidas pela equipe (palavras-chave para tema e proporções simples), sendo fáceis de auditar, mas limitadas; já um modelo validado exige base histórica real volumosa, engenharia de atributos, validação cruzada, métricas de erro e calibração de probabilidade.

---

### 4.4. Segurança e LGPD

1. **Como os dados jurídicos são protegidos?**
   - **Resposta curta:** O pipeline aplica sanitização local no backend antes de gravar no banco ou acionar qualquer adaptador externo de IA, substituindo CPFs, RGs rotulados e nomes de pessoas físicas do polo ativo por máscaras, além de registrar um log de auditoria no banco.
   - **Aprofundamento:** Também há suporte a senha com hash PBKDF2-HMAC-SHA256 e emissão de JWT na rota de login.

2. **O sistema anonimiza informações pessoais?**
   - **Resposta curta:** Faz uma anonimização/pseudonimização inicial determinística para CPFs, RGs e nomes identificados como autor/requerente, mantendo nomes de empresas (pessoas jurídicas) visíveis para jurimetria.
   - **Limitação importante (se aprofundarem):** Hoje ainda é uma proteção parcial baseada em expressões regulares: não detecta automaticamente endereços, telefones, e-mails, dados de saúde (CID) ou nomes de réus pessoa física em prosa solta, e como o número completo do processo (CNJ) continua salvo, existe risco de reidentificação indireta. Além disso, o adaptador do Gemini precisa receber a lista explícita de nomes identificados antes do envio externo.

3. **Como são controlados os acessos?**
   - **Resposta curta:** Implementamos o endpoint de login (`/api/v1/auth/login`) com verificação de senha e emissão de JWT, mas, no MVP atual para facilitar a demonstração e integração inicial, a validação obrigatória desse token nas demais rotas e o isolamento de processos por usuário ainda estão pendentes de ativação.

4. **Quais são as limitações atuais de segurança?**
   - **Resposta curta:** Precisamos principalmente ativar a exigência do token JWT em todas as rotas protegidas, sanitizar conteúdo dinâmico na interface para evitar XSS, impor limite de tamanho em uploads, restringir CORS, remover credenciais de demonstração padrão do HTML e endurecer o filtro LGPD antes de qualquer uso em produção.

---

### 4.5. Arquitetura e Tecnologia

1. **Por que o frontend foi desenvolvido dessa maneira?**
   - **Resposta curta:** Optamos por HTML semântico, CSS com Design Tokens e JavaScript modular puro (ES Modules via Vite) para ter controle total sobre acessibilidade (WCAG), carregamento leve sem excesso de dependências em tempo de execução e foco na estética editorial jurídica.
   - **Aprofundamento:** Chegamos a experimentar uma estrutura paralela em React em outra branch de estudo, mas consolidamos na `main` a versão Vanilla/Vite por estar completa para todos os requisitos do MVP e validada pelos testes de acessibilidade.

2. **Como frontend, backend e processamento se comunicam?**
   - **Resposta curta:** O frontend se comunica via HTTP/REST (JSON e envio de arquivos `multipart/form-data`) com a API FastAPI no backend (`:8000`). Embora a arquitetura preveja um container separado (`ai_engine:8001`), nesta etapa o módulo de processamento e o gateway de IA executam dentro do próprio backend para simplificar a entrega e evitar falhas de rede no MVP.

3. **Por que utilizar PostgreSQL e SQLite?**
   - **Resposta curta:** Por portabilidade e resiliência. Em execução completa com Docker, o sistema conecta no PostgreSQL 16; em execução local direta sem Docker (como na máquina de desenvolvimento ou testes automatizados), o backend detecta a ausência do Postgres e chaveia automaticamente para um banco SQLite local sem quebrar a aplicação.

4. **Como funciona a integração com o DataJud?**
   - **Resposta curta:** Um cliente assíncrono no backend lê os dígitos do tribunal no número CNJ (por exemplo, `8.02` identifica o TJAL), envia uma consulta Elasticsearch oficial à API Pública do DataJud com timeout curto de 3 segundos e, em caso de erro, indisponibilidade ou ausência, recorre à base local.

5. **Quais são os principais desafios técnicos?**
   - **Resposta curta:** (a) Garantir anonimização robusta em textos jurídicos livres altamente variados; (b) evoluir de heurísticas para análise semântica e estatística confiável sem gerar custo de API; (c) ativar o microsserviço isolado de IA e OCR; e (d) fechar os requisitos de segurança (autenticação por rota, limites de upload e sanitização) antes de ir além do MVP.

---

## 5. Checklist Operacional para a Apresentação Remota

### 5.1. Verificações Prévias (15 Minutos Antes)

> **Atenção importante sobre o estado atual da sua máquina:** Antes da última inspeção, o repositório local estava com a branch **`dev`** selecionada, e não a **`main`**. Confira o item 1 abaixo antes de iniciar os servidores!

- [ ] **1. Branch e Commit Corretos (`main` / `40c231c`):**
  - Confirmar no terminal que está na branch `main`: `git branch --show-current` $\rightarrow$ deve exibir `main`.
  - *(Se aparecer `dev`, rodar `git checkout main` antes de subir a aplicação. Não edite nem dê `pytest` sem banco temporário para não sujar o SQLite demonstrativo.)*
- [ ] **2. Internet Ativa:**
  - Necessária para carregar `Chart.js` (CDN) e fontes (`Google Fonts`) no navegador, além da consulta ao vivo no DataJud (CNJ).
- [ ] **3. Iniciar Backend e Frontend:**
  - Clicar em **`start_dev.bat`** (ou rodar em dois terminais:
    - Terminal 1: `.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --port 8000`
    - Terminal 2: `cd frontend; npm run dev`)
- [ ] **4. Validar Saúde Antes de Entrar na Chamada:**
  - Abrir [`http://localhost:8000/health`](http://localhost:8000/health) $\rightarrow$ confirmar `{"status":"ok", ...}`.
  - Abrir [`http://localhost:5173`](http://localhost:5173) $\rightarrow$ confirmar selo verde **"Acervo TJAL sincronizado"** e gráficos carregando na aba **"Análise Jurimétrica"**.
  - Deixar aberta uma aba extra com [`http://localhost:8000/docs`](http://localhost:8000/docs) (Swagger) caso o professor peça para ver os endpoints.
- [ ] **5. Ambiente de Apresentação Remota:**
  - Fechar abas pessoais, WhatsApp/Discord/notificações do sistema.
  - Compartilhar **apenas a janela do navegador** (ou tela dedicada) com zoom confortável (`100%` ou `110%` se necessário).
  - Testar microfone e deixar este roteiro aberto em uma segunda tela, janela ao lado ou celular para consulta rápida.
  - Deixar um cronômetro visível para gerenciar os ~13 minutos sem pressa.

---

### 5.2. Plano B — Contingências para Falhas Durante a Apresentação

| Cenário de Falha | Sintoma / Causa Provável | Ação Imediata de Contingência (Plano B) |
| :--- | :--- | :--- |
| **1. Backend não inicia** | Porta `8000` ocupada ou erro no `.venv` | Verificar se já há processo rodando em `http://localhost:8000/health`. Se estiver travado, rodar em outro terminal na porta normal após fechar processos antigos. **Em último caso durante a chamada:** explicar honestamente a falha local da porta, mostrar o código/Swagger ou o frontend em **modo de demonstração local** (o frontend carrega dados de fallback automaticamente se a API estiver desligada, mas **deixe explícito ao professor** que é o fallback estático e não a API ao vivo). |
| **2. Frontend não carrega (`:5173`)** | `node_modules` ausente ou Vite não subiu | Confirmar se está dentro da pasta `frontend` antes de `npm run dev`. Se persistir, não perca mais de 30s ao vivo: demonstre os fluxos reais diretamente pelo **Swagger** em `http://localhost:8000/docs` (`/processos`, `/dashboard/metricas`, `/processos/datajud/{numero}`, `/relatorios/processo/proc-1004/pdf`), que comprova todo o funcionamento real do backend. |
| **3. Internet indisponível ou DataJud lento** | Wi-Fi caiu ou API do CNJ demorou > 3s | O próprio sistema já foi projetado para isso: a consulta **DataJud (CNJ)** cairá em ~3s no fallback local exibindo os metadados do TJAL (`proc-1001` = `0019283-44.2025.8.02.0001`). Aproveite o momento para mostrar a resiliência funcionando na prática! |
| **4. Gráficos do Dashboard não aparecem** | Sem acesso ao CDN do `Chart.js` | Os indicadores numéricos superiores, as barras proporcionais em HTML e as tabelas acessíveis abaixo (`Consultar tabela analítica...`) continuam funcionando localmente com dados reais da API. Abra os `<details>` das tabelas e explique com transparência que `Chart.js` depende de CDN nesta versão (já listado nos próximos passos). |
| **5. Upload de PDF falha ou demora** | Arquivo externo sem texto (escaneado) ou erro momentâneo | **Use exclusivamente o botão `"Testar com petição demonstrativa (Atraso de Voo)"`**, que gera em memória um PDF 1.4 válido em < 200ms. Se ocorrer falha de rede, recarregue a aba (`F5`) e explique a estrutura do parecer. |
| **6. Funcionalidade trava ou dá erro inesperado ao vivo** | Estado preso na tela ou filtro vazio | Clicar em **"Limpar filtros"** (na pesquisa) ou **"Analisar outro documento"** (no upload) antes de recarregar (`F5`). Se não responder, passar imediatamente para o próximo bloco usando capturas de tela previamente salvas **ou** o Swagger (`/docs`), deixando claro para a banca o que foi executado ao vivo vs o que foi mostrado como registro/contingência. |
