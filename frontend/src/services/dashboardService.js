/**
 * Serviço de Métricas e Jurimetria do Dashboard.
 * Contrato oficial: Seção 7.2 do ARCHITECTURE.md.
 */
import { api } from './api';

// Dados de contingência (mock) espelhando o ARCHITECTURE.md
export const MOCK_METRICAS_DASHBOARD = {
  taxa_exito_global: 0.684,
  tempo_medio_tramitacao_meses: 14,
  total_processos_analisados: 1248,
  decisoes_por_juiz: [
    { juiz: 'Dr. Rafael De Amorim', procedentes: 120, improcedentes: 45 },
    { juiz: 'Dra. Maria Silva', procedentes: 95, improcedentes: 80 },
    { juiz: 'Dr. Carlos Souza', procedentes: 60, improcedentes: 50 },
  ],
  volume_por_tema: [
    { tema: 'Dano Moral', percentual: 45, color: '#3b82f6' },
    { tema: 'Direito Trabalhista', percentual: 25, color: '#8b5cf6' },
    { tema: 'Plano de Saúde', percentual: 20, color: '#10b981' },
    { tema: 'Tributário', percentual: 10, color: '#f59e0b' },
  ],
};

/**
 * Busca as métricas consolidadas para os gráficos e cards do Dashboard.
 * Rota: GET /api/v1/dashboard/metricas
 */
export async function getMetricasDashboard() {
  try {
    const data = await api.get('/dashboard/metricas');
    // Enriquecer temas com cores para visualização no gráfico
    const colors = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899', '#6366f1'];
    return {
      ...data,
      volume_por_tema: (data.volume_por_tema || []).map((t, idx) => ({
        ...t,
        color: t.color || colors[idx % colors.length],
      })),
    };
  } catch (error) {
    console.info('[DashboardService] Usando dados mock de jurimetria (backend offline ou inicializando).');
    return MOCK_METRICAS_DASHBOARD;
  }
}
