import React from 'react';
import { NavLink } from 'react-router-dom';
import { Scale, PieChart, FileUp, Database } from 'lucide-react';
import { getCurrentUser } from '../../services/authService';

/**
 * Menu lateral fixo de navegação da plataforma integrado com react-router-dom.
 */
export default function Sidebar() {
  const user = getCurrentUser();
  const initials = user?.nome
    ? user.nome
        .split(' ')
        .map((n) => n[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : 'LG';

  const navItems = [
    { to: '/', label: 'Jurimetria', icon: PieChart, end: true },
    { to: '/upload', label: 'Novo Processo (PDF)', icon: FileUp },
    { to: '/historico', label: 'Base de Conhecimento', icon: Database },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-white flex flex-col justify-between shrink-0 shadow-lg select-none">
      <div>
        {/* Identificação / Logo */}
        <div className="p-6 border-b border-slate-800 flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
            <Scale size={22} />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">JuriPredict</h1>
            <p className="text-xs text-slate-400">Equipe Epsilon · UFAL</p>
          </div>
        </div>

        {/* Itens de Navegação com rotas */}
        <nav className="p-4 space-y-1.5" aria-label="Menu principal">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-medium transition duration-150 ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
                      : 'text-slate-400 hover:bg-slate-800/80 hover:text-slate-200'
                  }`
                }
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Perfil do Usuário Conectado */}
      <div className="p-4 border-t border-slate-800">
        <div className="flex items-center space-x-3 p-2 rounded-xl bg-slate-800/50">
          <div className="w-9 h-9 rounded-full bg-slate-700 border border-slate-600 flex items-center justify-center text-xs font-semibold text-slate-200">
            {initials}
          </div>
          <div className="truncate flex-1">
            <p className="text-xs font-semibold text-slate-200 truncate">{user?.nome || 'Advogado Associado'}</p>
            <p className="text-[10px] text-slate-400 truncate">{user?.email || 'epsilon@ufal.br'}</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
