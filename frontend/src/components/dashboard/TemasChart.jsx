import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

/**
 * Gráfico em rosca com a distribuição de volume por tema jurídico.
 * 
 * @param {Object} props
 * @param {Array<{ tema: string, percentual: number, color?: string }>} props.data
 */
export default function TemasChart({ data = [] }) {
  const chartData = data.map((item) => ({
    name: item.tema,
    value: item.percentual,
    color: item.color || '#3b82f6',
  }));

  return (
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between">
      <div>
        <h4 className="text-base font-bold text-slate-800 mb-1">Volume por Tema</h4>
        <p className="text-xs text-slate-400 mb-4">Distribuição percentual das matérias processuais</p>
      </div>

      <div className="h-64 w-full flex items-center justify-center">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={85}
              paddingAngle={4}
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
