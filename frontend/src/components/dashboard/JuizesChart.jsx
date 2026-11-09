import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

/**
 * Gráfico de barras com as decisões (Procedentes vs Improcedentes) por Magistrado.
 * 
 * @param {Object} props
 * @param {Array<{ juiz: string, procedentes: number, improcedentes: number }>} props.data
 */
export default function JuizesChart({ data = [] }) {
  return (
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between">
      <div>
        <h4 className="text-base font-bold text-slate-800 mb-1">Decisões por Magistrado</h4>
        <p className="text-xs text-slate-400 mb-4">Volume de sentenças procedentes vs. improcedentes</p>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <XAxis dataKey="juiz" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Bar dataKey="procedentes" name="Procedentes" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            <Bar dataKey="improcedentes" name="Improcedentes" fill="#ef4444" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
