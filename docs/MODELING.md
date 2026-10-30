# Modelagem Comportamental e Dinâmica do Sistema

> **Projeto Avaliativo de Gerência de Projetos — Prof. Rafael De Amorim (UFAL)**  
> **Sistema:** Plataforma Analítica e Preditiva para Gestão de Processos Jurídicos (Equipe Epsilon)  
> **Finalidade:** Servir como especificação comportamental formal para desenvolvedores e agentes de codificação (Google Antigravity / Cursor).

---

## 1. Visão Geral da Modelagem Dinâmica

Enquanto o `ARCHITECTURE.md` estabelece a organização estática (componentes, contêineres e contratos de API), este documento especifica o **comportamento dinâmico e o ciclo de vida dos dados** na plataforma.

Os quatro diagramas fundamentais contemplam:
1. **Diagrama de Casos de Uso (DCU):** Delimitação do escopo funcional sob a ótica do usuário final (Advogado).
2. **Diagrama de Atividades (DA):** O fluxo operacional detalhado das esteiras de negócio e bifurcações de decisão.
3. **Diagrama de Sequência (DS):** A coreografia cronológica de mensagens e chamadas entre Front-end, Back-end API, Worker de IA e Persistência.
4. **Diagrama de Estados (DE):** Os estados transitórios que um processo jurídico assume desde o upload até a consolidação analítica e predição.

---

## 2. Diagrama de Casos de Uso (DCU)

### 2.1 Descrição do Escopo Funcional
O sistema possui como ator primário o **Profissional do Direito (Advogado)**. O modelo reflete a ingestão primária por PDF (com suporte a CSV em lote), as etapas obrigatórias de processamento interno (`<<include>>`), as funções estendidas condicionais (`<<extend>>`) e os módulos consultivos e preditivos.

### 2.2 Diagrama Mermaid

```mermaid
flowchart LR
    Actor[("👤 Profissional do Direito<br/>(Advogado)")]

    subgraph Plataforma [" Plataforma Analítica e Preditiva para Gestão de Processos Jurídicos "]
        UC_Auth(("Acessar Sistema<br/>(Login / Sessão)"))
        UC_Upload(("Realizar Upload de Processo<br/>(PDF ou Planilha CSV)"))
        UC_Validar(("Validar e Estruturar<br/>Dados do Arquivo"))
        UC_LGPD(("Anonimizar Dados<br/>Sensíveis (LGPD)"))
        UC_NLP(("Analisar Texto e Gerar<br/>Resumo Factual (NLP)"))
        UC_Dashboard(("Visualizar Dashboard<br/>Analítico"))
        UC_Metricas(("Visualizar Métricas e<br/>Indicadores de Jurimetria"))
        UC_Filtros(("Aplicar Filtros<br/>de Pesquisa"))
        UC_Predicao(("Solicitar Análise de<br/>Probabilidade / Tendência"))
        UC_CasosSimilares(("Consultar Histórico de<br/>Casos Semelhantes (IA)"))
        UC_ExibirPredicao(("Exibir Tendência do Juiz<br/>e % de Sucesso"))
        UC_Relatorio(("Solicitar Geração de<br/>Relatório Estratégico"))
        UC_ExportPDF(("Exportar Relatório<br/>Consolidado em PDF"))
    end

    %% Relações do Ator
    Actor --> UC_Auth
    Actor --> UC_Upload
    Actor --> UC_Dashboard
    Actor --> UC_Filtros
    Actor --> UC_Predicao
    Actor --> UC_Relatorio

    %% Relacionamentos de Ingestão e IA
    UC_Upload -.->|«include»| UC_Validar
    UC_Validar -.->|«include»| UC_LGPD
    UC_LGPD -.->|«include»| UC_NLP

    %% Relacionamentos do Dashboard
    UC_Dashboard -.->|«extend»| UC_Metricas

    %% Relacionamentos da Predição
    UC_Predicao -.->|«include»| UC_CasosSimilares
    UC_CasosSimilares -.->|«include»| UC_ExibirPredicao

    %% Relacionamentos de Exportação
    UC_Relatorio -.->|«include»| UC_ExportPDF
```

---

## 3. Diagrama de Atividades (DA)

### 3.1 Fluxo de Negócio Operacional
Mapeia a execução de ponta a ponta: desde a recepção do arquivo, passagem obrigatória pela esteira de segurança LGPD, indexação para consulta, cálculo preditivo sob demanda e geração de relatórios.

### 3.2 Diagrama Mermaid

```mermaid
flowchart TD
    Inicio([Início]) --> A1[Advogado submete arquivo: PDF ou CSV]
    
    subgraph Ingestao [" Esteira de Ingestão e Validação "]
        A1 --> B1{Arquivo válido e íntegro?}
        B1 -- Não --> E1[Exibir mensagem de erro ao usuário]
        E1 --> FimErro([Fim com Erro])
        B1 -- Sim --> B2{Tipo de Arquivo?}
        B2 -- PDF --> B3[Executar OCR / Parser textual de petições]
        B2 -- CSV --> B4[Validar colunas e estruturação tabular]
    end

    subgraph Seguranca_LGPD [" Higienização e Anonimização "]
        B3 --> C1[Varrer texto em busca de dados sensíveis]
        B4 --> C1
        C1 --> C2{Existem dados sensíveis identificados?}
        C2 -- Sim --> C3[Aplicar mascaramento: CPFs, RGs e Nomes Reais]
        C2 -- Não --> C4[Manter texto base limpo]
        C3 --> C4
    end

    subgraph Inteligencia_NLP [" Processamento de Linguagem Natural "]
        C4 --> D1[Executar algoritmo NLP para extração de entidades]
        D1 --> D2[Gerar resumo executivo factual do caso]
        D2 --> D3[Gravar processo higienizado e resumo no Banco de Dados]
    end

    subgraph Dashboard_Consulta [" Exploração de Jurimetria "]
        D3 --> G1[Disponibilizar dados no Dashboard Interativo]
        G1 --> G2[Advogado aplica filtros: Magistrado, Comarca ou Tema]
        G2 --> G3[Renderizar gráficos de decisões e tempo médio]
    end

    subgraph Predicao_IA [" Inteligência Preditiva "]
        G3 --> H1{Solicitar análise preditiva de caso?}
        H1 -- Sim --> H2[Consultar base histórica com mesmos atributos]
        H2 --> H3[Calcular probabilidade estatística de êxito]
        H3 --> H4[Estimar tempo de sentença e perfil decisório do juiz]
        H4 --> H5[Exibir parecer consolidado na tela]
        H1 -- Não --> H6{Exportar relatório tático?}
        H5 --> H6
    end

    subgraph Exportacao [" Fechamento e Relatório "]
        H6 -- Sim --> I1[Compilar métricas, resumo NLP e projeção da IA]
        I1 --> I2[Gerar arquivo PDF formatado para download]
        I2 --> FimSucesso([Fim com Sucesso])
        H6 -- Não --> FimSucesso
    end
```

---

## 4. Diagrama de Sequência (DS)

### 4.1 Ciclo Completo de Comunicação
O Diagrama de Sequência detalha as requisições assíncronas e síncronas entre os 5 atores e subsistemas definidos na arquitetura.

### 4.2 Diagrama Mermaid

```mermaid
sequenceDiagram
    autonumber
    actor ADV as Advogado
    participant FE as Front-end (React SPA)
    participant API as Back-end (FastAPI Gateway)
    participant IA as Worker de IA & NLP
    participant DB as Banco de Dados (PostgreSQL)

    %% FASE 1: AUTENTICAÇÃO E DASHBOARD
    rect rgb(240, 245, 255)
    Note over ADV, DB: Fase 1: Acesso Seguro e Carga de Métricas Globais
    ADV->>FE: Inserir credenciais (Login)
    FE->>API: POST /api/v1/auth/login
    API->>DB: Consultar credenciais e permissões
    DB-->>API: Dados do usuário validados
    API-->>FE: Retornar JWT Token + Perfil
    FE->>API: GET /api/v1/dashboard/metricas
    API->>DB: Consultar agregações históricas (juízes, taxas, prazos)
    DB-->>API: Conjunto de dados estatísticos
    API-->>FE: Retornar JSON consolidado
    FE-->>ADV: Renderizar dashboard com gráficos e indicadores
    end

    %% FASE 2: UPLOAD E PROCESSAMENTO INTELIGENTE
    rect rgb(245, 255, 245)
    Note over ADV, DB: Fase 2: Ingestão de Novo Processo (PDF) e Esteira de IA
    ADV->>FE: Selecionar e submeter PDF da petição inicial
    FE->>API: POST /api/v1/processos/upload-pdf (Multipart Form-Data)
    API->>API: Validar assinatura e tamanho do arquivo
    API->>IA: Disparar tarefa de extração e processamento
    
    activate IA
    IA->>IA: Executar OCR / Leitura textual (pdfplumber)
    IA->>IA: Mascarar dados pessoais sensíveis (Motor LGPD)
    IA->>IA: Gerar resumo factual da lide (Motor NLP)
    IA->>DB: Buscar histórico de casos similares (mesmo Juiz / Tema)
    DB-->>IA: Retornar sentenças correlatas da base
    IA->>IA: Calcular probabilidade de deferimento e tempo médio
    IA-->>API: Devolver metadados, resumo, taxa de êxito e perfil do juiz
    deactivate IA

    API->>DB: Persistir processo higienizado e indicadores calculados
    DB-->>API: Confirmação de gravação
    API-->>FE: Retornar payload com análise preditiva completa
    FE-->>ADV: Apresentar na interface: parecer da IA, juiz e resumo
    end

    %% FASE 3: CONSULTA AVANÇADA E RELATÓRIO
    rect rgb(255, 250, 240)
    Note over ADV, DB: Fase 3: Pesquisa Jurisprudencial e Exportação
    ADV->>FE: Aplicar filtros de pesquisa (ex: Juiz = "Dr. Rafael", Tema = "Consumidor")
    FE->>API: GET /api/v1/processos?tema=Consumidor&juiz=Rafael
    API->>DB: Consultar registros higienizados
    DB-->>API: Retornar processos correspondentes
    API-->>FE: Lista paginada de jurisprudência
    FE-->>ADV: Exibir tabela com resultados anonimizados

    opt Exportação de Relatório Executivo
        ADV->>FE: Clicar em "Exportar Relatório Estratégico"
        FE->>API: GET /api/v1/relatorios/processo/{id}/pdf
        API->>DB: Coletar métricas daquele processo específico
        DB-->>API: Dados consolidados
        API->>API: Renderizar documento PDF profissional
        API-->>FE: Stream binário do PDF (application/pdf)
        FE-->>ADV: Iniciar download automático do documento
    end
    end
```

---

## 5. Diagrama de Estados do Processo (DE)

### 5.1 Ciclo de Vida da Entidade Processual
Modela as transições de estado que um documento processual percorre no backend desde sua chegada bruta até a prontidão para consultas preditivas.

### 5.2 Diagrama Mermaid

```mermaid
stateDiagram-v2
    [*] --> Submetido : Upload realizado pelo advogado

    state Submetido {
        [*] --> EmValidacaoFormato
        EmValidacaoFormato --> Valido : Assinatura PDF / CSV correta
        EmValidacaoFormato --> Invalido : Arquivo corrompido / Formato incorreto
    }

    Invalido --> ErroProcessamento : Notificar falha de integridade
    ErroProcessamento --> [*]

    Valido --> EmExtracaoTexto : Iniciar OCR / Parser textual
    
    state EmExtracaoTexto {
        [*] --> ProcessandoTexto
        ProcessandoTexto --> TextoExtraido : Conteúdo recuperado
        ProcessandoTexto --> FalhaOCR : Arquivo ilegível / sem texto
    }

    FalhaOCR --> ErroProcessamento : Falha na extração documental

    TextoExtraido --> EmAnonimizacaoLGPD : Aplicar filtros de privacidade
    
    state EmAnonimizacaoLGPD {
        [*] --> DetectandoEntidades
        DetectandoEntidades --> MascarandoDados : CPFs / Nomes detectados
        DetectandoEntidades --> SemDadosSensiveis : Nenhum dado sensível
        MascarandoDados --> DadosHigienizados
        SemDadosSensiveis --> DadosHigienizados
    }

    DadosHigienizados --> EmProcessamentoNLP : Gerar resumo factual da lide

    state EmProcessamentoNLP {
        [*] --> SintetizandoPeticao
        SintetizandoPeticao --> ResumoConcluido
    }

    ResumoConcluido --> EmAnalisePreditiva : Correlacionar com base histórica

    state EmAnalisePreditiva {
        [*] --> ConsultandoHistoricoJuiz
        ConsultandoHistoricoJuiz --> CalculandoMetricas : Casos análogos encontrados
        CalculandoMetricas --> PredicaoConcluida
    }

    PredicaoConcluida --> ProntoParaConsulta : Gravar metadados e score na base
    
    ProntoParaConsulta --> RelatorioGerado : Exportação solicitada
    RelatorioGerado --> ProntoParaConsulta : Download finalizado

    ProntoParaConsulta --> [*]
```

---

## 6. Diretrizes para Agentes de Código (Google Antigravity)

Ao implementar rotas, serviços ou workers baseando-se neste documento:
1. **Nunca violar a sequência LGPD:** Qualquer rotina de sumarização (`MotorNLP`) ou de predição deve receber obrigatoriamente como entrada o texto que já transicionou pelo estado `DadosHigienizados`.
2. **Respeitar os Estados de Erro:** Em caso de exceção de leitura ou arquivo corrompido, a API deve atualizar o estado da entidade no banco para `ErroProcessamento` e retornar o código HTTP padronizado (422 Unprocessable Entity ou 400 Bad Request) com mensagem orientativa.
3. **Assincronismo nas Tarefas Longas:** Operações de OCR e predição não devem bloquear o loop principal da API FastAPI; devem ser delegadas a workers ou tarefas em background (`BackgroundTasks` / Celery / Redis).