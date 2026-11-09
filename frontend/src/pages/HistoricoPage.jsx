import React, { useEffect, useState } from 'react';
import { Search, Filter, RefreshCw, AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import { getProcessos } from '../services/processoService';
import { LoadingSpinner } from '../components';

/**
 * Página de Consulta da Base de Conhecimento e Jurisprudência.
 * Contrato oficial: Seção 7.4 do ARCHITECTURE.md.
 */
export default function HistoricoPage() {
  const [processos, setProcessos] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filtroTema, setFiltroTema] = useState('');
  const [pagina, setPagina] = useState(1);
  const [limite, setLimite] = useState(5);

  const carregarProcessos = async (busca = '', tema = '', paginaAtual = 1, limiteAtual = 5) => {
    setLoading(true);
    try {
      const response = await getProcessos({
        busca,
        tema,
        pagina: paginaAtual,
        limite: limiteAtual,
      });
      setProcessos(response.itens || []);
      setTotal(response.total || 0);
    } catch (error) {
      console.error('Falha ao buscar processos:', error);
    } finally {
      setLoading(false);
    }
  };

  // Ao alterar busca ou tema, reseta para a primeira página
  useEffect(() => {
    setPagina(1);
  }, [searchTerm, filtroTema]);

  // Carrega processos ao alterar busca, tema, página ou limite
  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      carregarProcessos(searchTerm, filtroTema, pagina, limite);
    }, 300);

    return () => clearTimeout(delayDebounce);
  }, [searchTerm, filtroTema, pagina, limite]);

  const temasDisponiveis = [
    'Todos',
    'Dano Moral',
    'Direito Trabalhista',
    'Plano de Saúde',
    'Tributário',
  ];

  const totalPaginas = Math.ceil(total / limite) || 1;
  const registroInicial = total === 0 ? 0 : (pagina - 1) * limite + 1;
  const registroFinal = Math.min(pagina * limite, total);

  const handlePaginaAnterior = () => {
    if (pagina > 1) {
      setPagina((prev) => prev - 1);
    }
  };

  const handleProximaPagina = () => {
    if (pagina < totalPaginas) {
      setPagina((prev) => prev + 1);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        {/* Barra de Filtros e Busca */}
        <div className="p-6 border-b border-slate-100 flex flex-col md:flex-row justify-between items-stretch md:items-center gap-4 bg-slate-50/50">
          <div>
            <h3 className="text-base font-bold text-slate-800">Processos Estruturados</h3>
            <p className="text-xs text-slate-400">
              Total de <strong className="text-slate-700">{total}</strong> registros catalogados e higienizados
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Filtro por Tema */}
            <div className="relative">
              <select
                value={filtroTema}
                onChange={(e) => setFiltroTema(e.target.value === 'Todos' ? '' : e.target.value)}
                className="bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
              >
                {temasDisponiveis.map((tema) => (
                  <option key={tema} value={tema === 'Todos' ? '' : tema}>
                    {tema}
                  </option>
                ))}
              </select>
            </div>

            {/* Campo de Pesquisa Textual */}
            <div className="relative flex-1 md:w-80">
              <Search size={16} className="absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Buscar por juiz, tema ou partes..."
                className="w-full pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
              />
            </div>
          </div>
        </div>

        {/* Tabela de Processos */}
        {loading ? (
          <div className="py-12">
            <LoadingSpinner title="Buscando processos..." />
          </div>
        ) : processos.length === 0 ? (
          <div className="text-center py-16 text-slate-400 space-y-2">
            <AlertCircle size={32} className="mx-auto text-slate-300" />
            <p className="text-sm font-medium">Nenhum processo encontrado para os filtros selecionados.</p>
            <button
              type="button"
              onClick={() => {
                setSearchTerm('');
                setFiltroTema('');
                setPagina(1);
              }}
              className="text-xs text-blue-600 hover:underline font-semibold"
            >
              Limpar filtros
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-100/70 text-slate-600 font-semibold border-b border-slate-200">
                  <th className="p-4">Nº do Processo</th>
                  <th className="p-4">Tema</th>
                  <th className="p-4">Magistrado</th>
                  <th className="p-4">Partes (Anonimizadas LGPD)</th>
                  <th className="p-4">Data Julgamento</th>
                  <th className="p-4">Resultado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {processos.map((item, index) => (
                  <tr key={item.id_processo || index} className="hover:bg-slate-50/70 transition">
                    <td className="p-4 font-mono font-medium text-blue-600">{item.id_processo}</td>
                    <td className="p-4 font-medium">{item.tema}</td>
                    <td className="p-4">{item.magistrado}</td>
                    <td className="p-4 text-slate-500">{item.partes_anonimizadas}</td>
                    <td className="p-4 text-slate-500">{item.data_julgamento}</td>
                    <td className="p-4">
                      <span
                        className={`px-2.5 py-1 rounded-full text-[11px] font-semibold inline-flex items-center space-x-1 ${
                          item.resultado === 'Procedente'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : item.resultado === 'Acordo'
                            ? 'bg-blue-50 text-blue-700 border border-blue-200'
                            : 'bg-rose-50 text-rose-700 border border-rose-200'
                        }`}
                      >
                        {item.resultado}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Rodapé com Controles de Paginação */}
        {!loading && total > 0 && (
          <div className="p-4 border-t border-slate-100 bg-slate-50/60 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-600">
            <div className="flex items-center space-x-3">
              <span>
                Exibindo <strong className="font-semibold text-slate-800">{registroInicial}</strong> a{' '}
                <strong className="font-semibold text-slate-800">{registroFinal}</strong> de{' '}
                <strong className="font-semibold text-slate-800">{total}</strong> processos
              </span>

              <div className="flex items-center space-x-1 border-l border-slate-200 pl-3">
                <span className="text-slate-400">Por página:</span>
                <select
                  value={limite}
                  onChange={(e) => {
                    setLimite(Number(e.target.value));
                    setPagina(1);
                  }}
                  className="bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                </select>
              </div>
            </div>

            <div className="flex items-center space-x-1.5">
              <button
                type="button"
                onClick={handlePaginaAnterior}
                disabled={pagina <= 1}
                className="flex items-center space-x-1 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                <ChevronLeft size={14} />
                <span>Anterior</span>
              </button>

              <div className="flex items-center space-x-1 px-2">
                {Array.from({ length: totalPaginas }, (_, i) => i + 1).map((num) => (
                  <button
                    key={num}
                    type="button"
                    onClick={() => setPagina(num)}
                    className={`w-7 h-7 rounded-lg text-xs font-medium transition ${
                      num === pagina
                        ? 'bg-blue-600 text-white shadow-sm'
                        : 'text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {num}
                  </button>
                ))}
              </div>

              <button
                type="button"
                onClick={handleProximaPagina}
                disabled={pagina >= totalPaginas}
                className="flex items-center space-x-1 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                <span>Próxima</span>
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
