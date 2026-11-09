/**
 * Serviço de Gestão Processual, Ingestão de PDF e Base de Conhecimento.
 * Contratos oficiais: Seções 7.3, 7.4 e 7.5 do ARCHITECTURE.md.
 */
import { api, apiRequest } from './api';

// Mock de resposta para o fluxo de Upload / Predição (Seção 7.3)
export const MOCK_UPLOAD_RESPONSE = {
  id_processo: 'proc-88910',
  arquivo_nome: 'peticao_inicial_voo.pdf',
  status: 'PROCESSADO',
  metadados_extraidos: {
    numero_processo: '0019283-44.2026.8.02.0001',
    tema: 'Atraso de Voo / Indenização',
    magistrado: 'Dr. Rafael De Amorim',
    comarca: '1ª Vara Cível de Maceió',
    partes_anonimizadas: {
      autor: 'L. G. R. S. ***',
      reu: 'Companhia Aérea Linhas Brasil S.A.',
    },
  },
  resumo_nlp:
    'Ação de reparação civil contra transportadora aérea decorrente de cancelamento abusivo de voo internacional sem assistência emergencial ao passageiro.',
  analise_preditiva: {
    probabilidade_deferimento: 0.75,
    margem_confianca: 0.08,
    tempo_estimado_sentenca_meses: 9,
    casos_similares_encontrados: 42,
    tese_recomendada:
      'Aplicação prioritária do Código de Defesa do Consumidor e súmula sobre danos presumidos por falta de assistência.',
    tendencia_juiz:
      'Magistrado possui histórico de 72% de decisões favoráveis ao consumidor neste padrão fático.',
  },
};

// Mock de lista de processos (Seção 7.4) - 15 registros para demonstração completa de paginação
export const MOCK_PROCESSOS_LIST = {
  total: 15,
  pagina: 1,
  itens: [
    {
      id_processo: '0019283-44.2026.8.02.0001',
      tema: 'Dano Moral / Atraso de Voo',
      magistrado: 'Dr. Rafael De Amorim',
      partes_anonimizadas: 'L. G. R. S. *** vs Cia Aérea Linhas Brasil',
      resultado: 'Procedente',
      data_julgamento: '2026-08-15',
    },
    {
      id_processo: '0004512-19.2026.8.02.0001',
      tema: 'Direito Trabalhista',
      magistrado: 'Dr. Rafael De Amorim',
      partes_anonimizadas: 'E. V. *** vs Tech Softwares LTDA',
      resultado: 'Acordo',
      data_julgamento: '2026-07-22',
    },
    {
      id_processo: '0055102-88.2025.8.02.0001',
      tema: 'Plano de Saúde',
      magistrado: 'Dra. Maria Silva',
      partes_anonimizadas: 'J. R. *** vs Unimed / Bem Estar',
      resultado: 'Improcedente',
      data_julgamento: '2026-05-10',
    },
    {
      id_processo: '0089201-12.2025.8.02.0001',
      tema: 'Tributário / ICMS',
      magistrado: 'Dr. Carlos Souza',
      partes_anonimizadas: 'Distribuidora Comercial *** vs Estado de Alagoas',
      resultado: 'Procedente',
      data_julgamento: '2026-04-18',
    },
    {
      id_processo: '0032190-77.2026.8.02.0001',
      tema: 'Dano Moral / Cobrança Indevida',
      magistrado: 'Dr. Rafael De Amorim',
      partes_anonimizadas: 'M. F. *** vs Banco Nacional S.A.',
      resultado: 'Procedente',
      data_julgamento: '2026-03-12',
    },
    {
      id_processo: '0011244-55.2025.8.02.0001',
      tema: 'Direito Trabalhista / Horas Extras',
      magistrado: 'Dra. Maria Silva',
      partes_anonimizadas: 'A. C. *** vs Logística Nordeste EIRELI',
      resultado: 'Procedente',
      data_julgamento: '2026-02-28',
    },
    {
      id_processo: '0044912-33.2025.8.02.0001',
      tema: 'Plano de Saúde / Negativa de Cirurgia',
      magistrado: 'Dr. Carlos Souza',
      partes_anonimizadas: 'R. S. *** vs Operadora Vida Plena',
      resultado: 'Procedente',
      data_julgamento: '2026-02-14',
    },
    {
      id_processo: '0077819-01.2025.8.02.0001',
      tema: 'Tributário / ISS',
      magistrado: 'Dr. Rafael De Amorim',
      partes_anonimizadas: 'Consultoria Alpha *** vs Município de Maceió',
      resultado: 'Improcedente',
      data_julgamento: '2026-01-20',
    },
    {
      id_processo: '0099120-44.2024.8.02.0001',
      tema: 'Dano Moral / Negativação',
      magistrado: 'Dra. Maria Silva',
      partes_anonimizadas: 'P. H. *** vs Telefonia Global S.A.',
      resultado: 'Acordo',
      data_julgamento: '2025-12-05',
    },
    {
      id_processo: '0066314-88.2024.8.02.0001',
      tema: 'Direito Trabalhista / Rescisão',
      magistrado: 'Dr. Carlos Souza',
      partes_anonimizadas: 'K. T. *** vs Supermercados Alagoanos',
      resultado: 'Procedente',
      data_julgamento: '2025-11-19',
    },
    {
      id_processo: '0088192-31.2024.8.02.0001',
      tema: 'Dano Moral / Extravio de Bagagem',
      magistrado: 'Dr. Rafael De Amorim',
      partes_anonimizadas: 'F. B. *** vs Linhas Aéreas Mundiais',
      resultado: 'Procedente',
      data_julgamento: '2025-10-08',
    },
    {
      id_processo: '0023419-62.2024.8.02.0001',
      tema: 'Plano de Saúde / Medicamento Alto Custo',
      magistrado: 'Dr. Carlos Souza',
      partes_anonimizadas: 'V. M. *** vs Saúde Segura Brasil',
      resultado: 'Procedente',
      data_julgamento: '2025-09-30',
    },
    {
      id_processo: '0015690-11.2024.8.02.0001',
      tema: 'Tributário / Taxa de Localização',
      magistrado: 'Dra. Maria Silva',
      partes_anonimizadas: 'Indústria Metalúrgica *** vs Município de Maceió',
      resultado: 'Improcedente',
      data_julgamento: '2025-08-14',
    },
    {
      id_processo: '0078129-90.2024.8.02.0001',
      tema: 'Direito Trabalhista / Equiparação',
      magistrado: 'Dr. Rafael De Amorim',
      partes_anonimizadas: 'C. D. *** vs Construtora Vanguarda',
      resultado: 'Acordo',
      data_julgamento: '2025-07-02',
    },
    {
      id_processo: '0041290-78.2024.8.02.0001',
      tema: 'Dano Moral / Fraude Bancária',
      magistrado: 'Dra. Maria Silva',
      partes_anonimizadas: 'G. O. *** vs Banco Digital S.A.',
      resultado: 'Procedente',
      data_julgamento: '2025-06-18',
    },
  ],
};

/**
 * Envia um arquivo PDF para extração inteligente, anonimização LGPD e parecer preditivo.
 * Rota: POST /api/v1/processos/upload-pdf (multipart/form-data)
 */
export async function uploadProcessoPDF(file) {
  const formData = new FormData();
  formData.append('file', file);

  try {
    return await apiRequest('/processos/upload-pdf', {
      method: 'POST',
      body: formData,
      isFormData: true,
    });
  } catch (error) {
    console.info('[ProcessoService] Simulando esteira de IA com dados de mock.');
    // Simula tempo de processamento da IA de 1.8 segundos
    await new Promise((resolve) => setTimeout(resolve, 1800));
    return {
      ...MOCK_UPLOAD_RESPONSE,
      arquivo_nome: file?.name || MOCK_UPLOAD_RESPONSE.arquivo_nome,
    };
  }
}

/**
 * Consulta a base de conhecimento estruturada com filtros opcionais.
 * Rota: GET /api/v1/processos?tema=...&juiz=...&pagina=1&limite=10
 */
export async function getProcessos({ tema = '', juiz = '', busca = '', pagina = 1, limite = 10 } = {}) {
  const params = new URLSearchParams();
  if (tema) params.append('tema', tema);
  if (juiz) params.append('juiz', juiz);
  if (busca) params.append('busca', busca);
  params.append('pagina', String(pagina));
  params.append('limite', String(limite));

  try {
    return await api.get(`/processos?${params.toString()}`);
  } catch (error) {
    console.info('[ProcessoService] Usando lista de processos mock.');
    let filtrados = [...MOCK_PROCESSOS_LIST.itens];

    if (busca) {
      const termo = busca.toLowerCase();
      filtrados = filtrados.filter(
        (p) =>
          p.id_processo.toLowerCase().includes(termo) ||
          p.tema.toLowerCase().includes(termo) ||
          p.magistrado.toLowerCase().includes(termo) ||
          p.partes_anonimizadas.toLowerCase().includes(termo)
      );
    }

    if (tema) {
      filtrados = filtrados.filter((p) => p.tema.toLowerCase().includes(tema.toLowerCase()));
    }

    if (juiz) {
      filtrados = filtrados.filter((p) => p.magistrado.toLowerCase().includes(juiz.toLowerCase()));
    }

    const total = filtrados.length;
    const inicio = (pagina - 1) * limite;
    const paginados = filtrados.slice(inicio, inicio + limite);

    return {
      total,
      pagina,
      itens: paginados,
    };
  }
}

/**
 * Exporta o relatório estratégico em PDF do processo selecionado.
 * Rota: GET /api/v1/relatorios/processo/{id_processo}/pdf
 */
export async function downloadRelatorioPDF(idProcesso = 'proc-88910') {
  try {
    const blob = await api.get(`/relatorios/processo/${idProcesso}/pdf`);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `relatorio-estrategico-${idProcesso}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.info('[ProcessoService] Backend indisponível para download de PDF. Acionando impressão nativa.');
    window.print();
  }
}
