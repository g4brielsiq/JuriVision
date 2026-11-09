import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar, Header } from './components';
import { DashboardPage, UploadPage, HistoricoPage } from './pages';

/**
 * Ponto de entrada da Interface Web (SPA React).
 * Arquitetura Modular Conforme ARCHITECTURE.md (Dupla 1 - UI/UX).
 * Roteamento Declarativo com react-router-dom.
 */
export default function App() {
  return (
    <div className="bg-slate-50 h-screen flex overflow-hidden">
      {/* 1. Menu Lateral Fixo com Rotas */}
      <Sidebar />

      {/* 2. Área de Conteúdo Principal */}
      <main className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Barra Superior de Ações e Título Dinâmico */}
        <Header />

        {/* Rotas Dinâmicas */}
        <div className="flex-1 overflow-y-auto p-8">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/dashboard" element={<Navigate to="/" replace />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/historico" element={<HistoricoPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
