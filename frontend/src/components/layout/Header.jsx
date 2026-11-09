import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Bell, Download, CheckCircle2 } from 'lucide-react';
import { downloadRelatorioPDF } from '../../services/processoService';

/**
 * Barra superior fixa da aplicação com título dinâmico baseado na rota atual.
 */
export default function Header({ title }) {
  const [exporting, setExporting] = useState(false);
  const [exported, setExported] = useState(false);
  const location = useLocation();

  const getTitle = () => {
    if (title) return title;
    switch (location.pathname) {
      case '/':
      case '/dashboard':
        return 'Dashboard de Jurimetria';
      case '/upload':
        return 'Análise de Novo Processo (PDF)';
      case '/historico':
        return 'Base de Conhecimento e Jurisprudência';
      default:
        return 'JuriPredict';
    }
  };

  const handleExportPDF = async () => {
    setExporting(true);
    try {
      await downloadRelatorioPDF('proc-88910');
      setExported(true);
      setTimeout(() => setExported(false), 3000);
    } catch (error) {
      console.error('Erro ao exportar PDF:', error);
    } finally {
      setExporting(false);
    }
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shrink-0">
      <div>
        <h2 className="text-xl font-bold text-slate-800">{getTitle()}</h2>
      </div>

      <div className="flex items-center space-x-3">
        {/* Notificações */}
        <button
          type="button"
          aria-label="Notificações do sistema"
          className="relative p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-50 transition"
        >
          <Bell size={20} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-blue-600 rounded-full animate-pulse" />
        </button>

        {/* Botão de Exportação de Relatório Executivo */}
        <button
          type="button"
          onClick={handleExportPDF}
          disabled={exporting}
          className="flex items-center space-x-2 px-3.5 py-2 border border-slate-200 hover:border-slate-300 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 shadow-sm transition disabled:opacity-50"
        >
          {exported ? (
            <>
              <CheckCircle2 size={16} className="text-emerald-500" />
              <span>PDF Gerado!</span>
            </>
          ) : (
            <>
              <Download size={16} className={exporting ? 'animate-bounce text-blue-600' : 'text-slate-500'} />
              <span>{exporting ? 'Exportando...' : 'Exportar Relatório'}</span>
            </>
          )}
        </button>
      </div>
    </header>
  );
}
