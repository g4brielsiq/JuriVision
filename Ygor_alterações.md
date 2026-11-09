Alterações feitas no projeto:
    Separei o frontEnd em môdulos como previsto no Architeture.md, adicionei as ferramentas e tecnologias (Vite, Recharts, Tailwindcss, LucideIcons). Implementei paginação na pesquisa de processos, ao invés de ser tudo numa página única, agora é possível transitar entre as páginas, atualizar a página sem voltar ao começo e é possível compartilhar o link de cada página. (Está salvo)



//-----------------------------------------------------//

Para fazer:

1. Feedback e Tratamento de Erros no Dashboard
Situação: Se a chamada para getMetricasDashboard() falhar, o serviço hoje entrega um mock de fallback silenciosamente. Isso é ótimo para desenvolvimento offline, mas é prudente indicar na UI (ex: uma tag discreta "Modo Demonstração / Dados Mockados") quando a API real estiver indisponível.

2. Ingestão em Lote via Planilhas CSV (Requisito da Arquitetura)
Situação: A tela UploadPage.jsx contempla apenas o upload unitário de PDF (uploadProcessoPDF).
Impacto: O ARCHITECTURE.md (Seção 1 e Seção 7.5) exige ingestão híbrida (PDF + importação em lote via CSV com barra de progresso de lotes processados).
Solução: Criar uma aba ou componente alternativo na tela de Upload permitindo arrastar arquivos .csv e disparar a importação em massa.

3. Modal/Gaveta de Detalhes do Processo:
Ao clicar em uma linha da tabela de processos no Histórico, abrir um modal exibindo os metadados extraídos, o texto com dados anonimizados e o resumo gerado pelo NLP.