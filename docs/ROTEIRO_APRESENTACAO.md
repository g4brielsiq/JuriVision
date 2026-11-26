# Roteiro de Apresentação e Tour pelo JuriVision (3 Apresentadores)

> **Formato:** Até **15 min** de apresentação + **5 min** para dúvidas e comentários  
> **Foco principal:** Produto desenvolvido (proposta, dor do negócio e demonstração ao vivo)

---

## Preparação Antes de Começar (Checklist de 2 minutos)

1. **Subir os 2 servidores** (com o `jurivision_local.sqlite3` já populado com os 91 julgados para os gráficos ficarem completos desde o início):
   - **Back-end:**
     ```powershell
     .\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --port 8000
     ```
   - **Front-end:**
     ```powershell
     cd frontend ; npm run dev
     ```
     Abrir `http://localhost:5173` em aba anônima ou recém-limpa (para exibir a intro animada logo na abertura).
2. **Ter em mãos na pasta da apresentação:**
   - 1 número CNJ real do TJAL copiado no bloco de notas (caso queiram testar *Consultar no DataJud* ao vivo) e 1 PDF de petição opcional;
   - **Lembrete de contingência:** se a API pública do DataJud estiver lenta ou com HTTP `429` na hora da banca, **não dependam do sync ao vivo** — expliquem o comportamento resiliente (ele avisa e não inventa dados) e sigam imediatamente pelos julgados reais/locais e pelos exemplos integrados.
3. **Deixar o Swagger (`http://localhost:8000/docs`) aberto em uma 2ª aba** apenas para eventuais perguntas técnicas.

---

## Divisão de Papéis e Cronograma (15 min)

| Tempo | Bloco | Apresentador(a) | Foco |
| :---: | :--- | :---: | :--- |
| **00:00 – 02:30** *(2m30)* | **Dor do Negócio, Proposta e Abertura** | **Apresentador 1** | Problema real da advocacia, proposta do JuriVision e tour na *Landing Page* + criação de conta / Freemium. |
| **02:30 – 06:30** *(4m00)* | **Pesquisa, DataJud, LGPD e Cadastro** | **Apresentador 1** | Aba *Pesquisa Jurisprudencial*, *Cadastrar julgado* (prévia LGPD ao vivo), DataJud e *Ler decisão* + *Exportar PDF*. |
| **06:30 – 10:00** *(3m30)* | **Análise Jurimétrica (Dashboard)** | **Apresentador 2** | Aba *Análise Jurimétrica*: KPIs com transparência amostral, gráficos interativos e *drill-down* para a Pesquisa. |
| **10:00 – 14:00** *(4m00)* | **Análise de Petição + Comparador de Peças** | **Apresentador 3** | Pipeline de 6 etapas, barreira LGPD, paywall `FREE → PRO`, e confronto Inicial vs. Contestação (Art. 357 CPC). |
| **14:00 – 15:00** *(1m00)* | **Fechamento e Diferenciais Técnicos** | **Apresentador 3** | Resumo dos diferenciais (LGPD local, fallback determinístico, zero dados inventados) e abertura para dúvidas. |
| **15:00 – 20:00** *(5m00)* | **Dúvidas e Comentários da Banca** | **Todos** | Respostas rápidas alinhadas ao módulo de cada um. |

---

## Roteiro Detalhado (Fala + Ações na Tela)

### Bloco 1 — Dor, Proposta e Entrada na Plataforma *(00:00 – 02:30 | Apresentador 1)*

- **Na tela:** Mostrar a animação inicial de entrada (`JuriVision`) e percorrer a **Landing Page**.
- **Fala-chave (Dor & Proposta — ~1m30):**
  - *Dor do negócio:* Advogados perdem horas buscando precedentes em portais fragmentados, não têm visão estatística clara do histórico de um tema ou vara, e frequentemente colam petições com dados sensíveis de clientes direto em IAs públicas (risco à LGPD).
  - *Proposta:* O **JuriVision** centraliza pesquisa jurisprudencial, jurimetria transparente, triagem de petições com anonimização LGPD local e comparação entre Petição Inicial e Contestação.
- **Ação na tela (~1m00):**
  - Clicar em um objetivo na seção *"Comece pelo que você precisa resolver agora"*, mostrar brevemente as abas ilustrativas e entrar clicando em **Criar conta gratuita** (ou **Entrar**, criando rapidamente uma conta com OAB fictícia tipo `55555/AL` para mostrar o cabeçalho logado com **`Plano FREE · 0/3`**).

---

### Bloco 2 — Pesquisa Jurisprudencial, LGPD ao Vivo e DataJud *(02:30 – 06:30 | Apresentador 1)*

- **Na tela:** Aba **Pesquisa Jurisprudencial**.
- **Ações e falas:**
  1. **Busca e filtros (~45s):** Digitar um termo (ex.: `voo` ou `dano moral`), filtrar por assunto/magistrado e mostrar a ordenação no servidor e o botão **Salvar** (coleção pessoal).
  2. **Cadastro manual + Barreira LGPD ao vivo (~1m15):** Clicar em **Cadastrar julgado** *(ou mostrar no formulário de edição)*, preencher nome completo de pessoa física e um CPF (ex.: `123.456.789-00`) e destacar a **Prévia de anonimização** mascarando os dados pessoais em tempo real antes mesmo de salvar no banco (mantendo razões sociais de empresas como réus).
  3. **Leitura Documental e PDF (~1m00):** Abrir **Ler decisão** em um julgado, mostrar os metadados anonimizados, a estimativa e clicar em **Exportar PDF** para demonstrar a geração real do relatório em PDF no momento.
  4. **Integração DataJud CNJ (~1m00):** Explicar a diferença dos dois botões:
     - **Consultar no DataJud (CNJ):** consulta metadados oficiais de 1 processo pelo número CNJ completo (20 dígitos);
     - **Sincronizar lote DataJud:** coleta julgados públicos do tribunal (por Assunto). *(Dica: mostrar o painel de retorno se o CNJ responder rápido, ou explicar que, caso a API pública do CNJ esteja sobrecarregada, o sistema aborta com aviso transparente e não inventa processos fictícios.)*

---

### Bloco 3 — Análise Jurimétrica e Transparência Estatística *(06:30 – 10:00 | Apresentador 2)*

- **Na tela:** Aba **Análise Jurimétrica**.
- **Ações e falas:**
  1. **KPIs e rigor metodológico (~1m15):**
     - Mostrar os 4 cards no topo e explicar um ponto forte do projeto: **Proporção Favorável** soma *Procedentes + Acordos* divididos apenas pelos processos *Decididos*, enquanto **Em Análise** (como petições recém-enviadas) fica separado para não distorcer a estatística.
  2. **Gráficos interativos e *drill-down* (~1m45):**
     - **Desfecho das Decisões (rosca):** composição geral do acervo.
     - **Perfil Decisório por Magistrado:** alternar entre **Quantidade** e **Percentual (%)**.
     - **Panorama por Assunto:** alternar entre **Volume** e **Taxa Favorável (%)** e **clicar em uma barra** (ex.: *Dano Moral*) para mostrar que o painel leva direto à aba de Pesquisa já filtrada naquele assunto.
  3. **Lastro Documental e Nota Metodológica (~30s):** Rolar até *Amostra de Julgados do Painel* e abrir brevemente a *Nota Metodológica* no rodapé do painel para mostrar a transparência amostral.

---

### Bloco 4 — Análise de Petição, Freemium e Comparador de Peças *(10:00 – 15:00 | Apresentador 3)*

- **Parte 1 — Análise de Petição + Freemium (~2m00):**
  - Ir à aba **Análise de Petição** e clicar em **Testar petição de exemplo** (ou subir um PDF).
  - Apontar o **rastreador de 6 etapas** concluindo (*Sigilo de Dados* → *Metadados* → *Precedentes do Juízo* → *Parecer Comparativo*).
  - Mostrar no dossiê gerado: CPF/nomes protegidos pela barreira LGPD local, comparação por similaridade (`TF-IDF` + `Okapi BM25`) com precedentes do acervo e **tese estratégica bloqueada com *blur*** no plano **FREE**.
  - Clicar no botão do plano para abrir o modal de assinatura, ativar o **Plano PRO** e mostrar o desbloqueio imediato da tese e da aba **Planilha CSV**.
- **Parte 2 — Comparador de Peças (~2m00):**
  - Ir à aba **Comparador de Peças**.
  - Explicar o caso de uso: automatizar a leitura de saneamento do processo (Art. 357 do CPC) confrontando **Petição Inicial** vs. **Contestação**.
  - Na seção **Demonstração guiada**, clicar em **Comparar peças do exemplo** e percorrer rapidamente o visualizador de **3 colunas** usando os filtros:
    - **Divergentes** (pontos de conflito direto),
    - **Omissões (Art. 341)** (fatos que o réu não impugnou),
    - **Fato Novo Defesa (Art. 350)** e **Convergentes**, mostrando os trechos citados com página em cada peça.
- **Fechamento (~1m00 | Apresentador 3):**
  - Recapitular os 3 pilares do sistema:
    1. **Segurança e LGPD local** antes de qualquer persistência ou envio à IA;
    2. **Tolerância a falhas** (funciona 100% offline com motor estatístico local se o Gemini ou o DataJud estiverem indisponíveis);
    3. **Rigor nos dados** (sem presunção artificial de resultados e com isolamento multiusuário).
  - Convidar a banca para os 5 minutos de perguntas.

---

## Respostas Prontas para Possíveis Perguntas da Banca *(5 min Q&A)*

- **"Os dados do sistema são reais ou fictícios?"**  
  → *Por padrão (`SEED_DEMO_DATA=false`), o sistema inicia vazio e só aceita dados vindos do DataJud (CNJ), uploads PDF/CSV ou cadastros manuais; nunca inventa resultados quando o tribunal ou a IA falham. Para a demonstração de hoje, usamos uma base populada com julgados de teste + sincronização pública, e o Comparador traz exemplos guiados sob demanda.*

- **"E se a API do Gemini ficar fora do ar (HTTP 503)?"**  
  → *Seguindo o padrão Port & Adapter, todo texto passa antes pela barreira LGPD local e, se o Gemini estiver sem chave, offline ou retornar 503, o `ResilientAIGateway` aciona automaticamente o fallback determinístico local (`TF-IDF` + `Okapi BM25` + heurísticas processuais) sem interromper o fluxo do usuário.*

- **"Como vocês garantem qualidade e conformidade?"**  
  → *Contamos com **150 testes automatizados (`pytest`)** cobrindo contratos REST, isolamento multiusuário JWT/Foreign Keys, barreira LGPD, saneamento de dados, motor NLP/RAG, modelo Freemium, Comparador de Peças e acessibilidade WCAG 2.2 AA / WAI-ARIA.*
