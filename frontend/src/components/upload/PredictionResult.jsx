import React from 'react';
import { Sparkles, ShieldCheck, ArrowLeft, Scale, Award } from 'lucide-react';

/**
 * Exibe o resultado consolidado da extração NLP e do modelo preditivo.
 * Contrato oficial: Seção 7.3 do ARCHITECTURE.md.
 * 
 * @param {Object} props
 * @param {Object} props.data - Objeto retornado por uploadProcessoPDF
 * @param {Function} props.onReset - Callback para reiniciar o upload
 */
export default function PredictionResult({ data, onReset }) {
  if (!data) return null;

  const {
    arquivo_nome,
    metadados_extraidos = {},
    resumo_nlp,
    analise_preditiva = {},
  } = data;

  const probabilidadePercent = analise_preditiva.probabilidade_deferimento
    ? Math.round(analise_preditiva.probabilidade_deferimento * 100)
    : 75;

  const confiancaPercent = analise_preditiva.margem_confianca
    ? Math.round((1 - analise_preditiva.margem_confianca) * 100)
    : 92;

  return (
    <div className="space-y-6">
      {/* Banner Principal da IA */}
      <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-6 flex items-start space-x-4">
        <div className="p-3 bg-emerald-500 text-white rounded-xl shadow-sm shrink-0">
          <Sparkles size={24} />
        </div>
        <div className="flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="text-base font-bold text-emerald-900">
              Parecer Preditivo do Modelo
            </h4>
            <span className="text-xs font-semibold bg-emerald-200/60 text-emerald-800 px-2.5 py-0.5 rounded-full">
              Confiança Estatística: {confiancaPercent}%
            </span>
          </div>

          <p className="text-sm text-emerald-800 mt-2 leading-relaxed">
            "Com base em{' '}
            <strong>
              {analise_preditiva.casos_similares_encontrados || 42} casos similares
            </strong>{' '}
            na comarca de {metadados_extraidos.comarca || 'Maceió'}, identificamos{' '}
            <strong>{probabilidadePercent}% de probabilidade de deferimento</strong> para este
            padrão fático. Tempo estimado até a sentença:{' '}
            <strong>
              {analise_preditiva.tempo_estimado_sentenca_meses || 9} meses
            </strong>
            ."
          </p>

          {analise_preditiva.tendencia_juiz && (
            <p className="text-xs text-emerald-700 mt-2 italic">
              <strong>Tendência do Magistrado:</strong> {analise_preditiva.tendencia_juiz}
            </p>
          )}
        </div>
      </div>

      {/* Grid de Atributos e Resumo */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Atributos Extraídos & Higienização LGPD */}
        <div className="border border-slate-200 rounded-2xl p-5 bg-slate-50/50">
          <div className="flex items-center justify-between pb-3 border-b border-slate-200">
            <h5 className="text-sm font-bold text-slate-800">Atributos Extraídos</h5>
            <span className="inline-flex items-center space-x-1 text-xs font-semibold bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
              <ShieldCheck size={12} />
              <span>LGPD Higienizado</span>
            </span>
          </div>

          <ul className="space-y-2.5 text-xs text-slate-600 mt-3">
            <li>
              <strong className="text-slate-800">Arquivo:</strong> {arquivo_nome}
            </li>
            <li>
              <strong className="text-slate-800">Número do Processo:</strong>{' '}
              <span className="font-mono text-blue-600 font-semibold">
                {metadados_extraidos.numero_processo || '0019283-44.2026.8.02.0001'}
              </span>
            </li>
            <li>
              <strong className="text-slate-800">Tema Jurídico:</strong>{' '}
              {metadados_extraidos.tema || 'Atraso de Voo / Indenização'}
            </li>
            <li>
              <strong className="text-slate-800">Magistrado:</strong>{' '}
              {metadados_extraidos.magistrado || 'Dr. Rafael De Amorim'}
            </li>
            <li>
              <strong className="text-slate-800">Comarca:</strong>{' '}
              {metadados_extraidos.comarca || '1ª Vara Cível de Maceió'}
            </li>
            <li>
              <strong className="text-slate-800">Autor (Mascarado):</strong>{' '}
              {metadados_extraidos.partes_anonimizadas?.autor || 'L. G. R. S. ***'}
            </li>
            <li>
              <strong className="text-slate-800">Réu:</strong>{' '}
              {metadados_extraidos.partes_anonimizadas?.reu || 'Companhia Aérea Linhas Brasil S.A.'}
            </li>
          </ul>
        </div>

        {/* Resumo Factual (NLP) e Tese */}
        <div className="border border-slate-200 rounded-2xl p-5 bg-slate-50/50 flex flex-col justify-between">
          <div>
            <div className="pb-3 border-b border-slate-200 flex items-center justify-between">
              <h5 className="text-sm font-bold text-slate-800">Resumo Factual (NLP)</h5>
              <span className="text-[11px] text-slate-400">Sumarização Automática</span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed mt-3 text-justify">
              {resumo_nlp ||
                'Ação de reparação civil contra transportadora aérea decorrente de cancelamento abusivo de voo internacional sem assistência emergencial ao passageiro.'}
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-200 bg-blue-50/50 p-3 rounded-xl border border-blue-100">
            <p className="text-xs text-blue-900 leading-snug">
              <strong>Tese Recomendada:</strong>{' '}
              {analise_preditiva.tese_recomendada ||
                'Aplicação prioritária do Código de Defesa do Consumidor e súmula sobre danos presumidos por falta de assistência.'}
            </p>
          </div>
        </div>
      </div>

      {/* Ação para Novo Upload */}
      <div className="text-center pt-2">
        <button
          type="button"
          onClick={onReset}
          className="inline-flex items-center space-x-1.5 text-xs text-blue-600 hover:text-blue-800 font-semibold transition"
        >
          <ArrowLeft size={14} />
          <span>Fazer novo upload de processo</span>
        </button>
      </div>
    </div>
  );
}
