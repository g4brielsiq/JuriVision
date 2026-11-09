import React from 'react';

/**
 * Indicador de carregamento visual para tarefas assíncronas de IA e Requisições.
 * 
 * @param {Object} props
 * @param {string} [props.title='Processamento em andamento...']
 * @param {string} [props.description]
 */
export default function LoadingSpinner({
  title = 'Processamento em andamento...',
  description,
}) {
  return (
    <div className="py-12 text-center space-y-4">
      <div className="inline-block w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
      <div>
        <h4 className="text-base font-bold text-slate-800">{title}</h4>
        {description && <p className="text-xs text-slate-500 mt-1">{description}</p>}
      </div>
    </div>
  );
}
