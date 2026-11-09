import React from 'react';

/**
 * Card para exibição de métricas numéricas do Dashboard.
 * 
 * @param {Object} props
 * @param {string} props.title - Rótulo da métrica (ex: "Taxa de Êxito Global")
 * @param {string|number} props.value - Valor numérico em destaque (ex: "68.4%")
 * @param {string} [props.subtitle] - Texto explicativo inferior
 * @param {string} [props.badge] - Tag de destaque/tendência (ex: "+2.1% este mês")
 * @param {React.ReactNode} props.icon - Ícone Lucide
 * @param {'blue'|'purple'|'emerald'} [props.variant='blue'] - Variação de cor da borda esquerda
 */
export default function MetricCard({
  title,
  value,
  subtitle,
  badge,
  icon,
  variant = 'blue',
}) {
  const borderVariants = {
    blue: 'border-l-blue-600',
    purple: 'border-l-purple-600',
    emerald: 'border-l-emerald-600',
  };

  const iconBgVariants = {
    blue: 'bg-blue-50 text-blue-600',
    purple: 'bg-purple-50 text-purple-600',
    emerald: 'bg-emerald-50 text-emerald-600',
  };

  return (
    <div
      className={`bg-white p-6 rounded-2xl shadow-sm border border-slate-100 border-l-4 ${
        borderVariants[variant] || borderVariants.blue
      }`}
    >
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500 font-medium">{title}</p>
        <span className={`p-2 rounded-lg ${iconBgVariants[variant] || iconBgVariants.blue}`}>
          {icon}
        </span>
      </div>

      <div className="mt-3 flex items-baseline space-x-2">
        <h3 className="text-3xl font-extrabold text-slate-800">{value}</h3>
        {badge && (
          <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
            {badge}
          </span>
        )}
      </div>

      {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
    </div>
  );
}
