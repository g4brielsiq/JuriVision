import React, { useRef, useState } from 'react';
import { FileUp, FileText } from 'lucide-react';

/**
 * Área de arrastar e soltar (drag & drop) e seleção de PDF.
 * 
 * @param {Object} props
 * @param {Function} props.onFileSelected - Callback chamado quando um arquivo é selecionado
 * @param {boolean} props.isLoading - Se o processamento está em andamento
 */
export default function UploadDropzone({ onFileSelected, isLoading }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      onFileSelected(files[0]);
    }
  };

  const handleFileInputChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onFileSelected(files[0]);
    }
  };

  const handleClickArea = () => {
    if (!isLoading && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  return (
    <div
      onClick={handleClickArea}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`border-2 border-dashed rounded-2xl p-10 text-center transition cursor-pointer group ${
        isDragOver
          ? 'border-blue-600 bg-blue-50/50'
          : 'border-slate-300 hover:border-blue-500 hover:bg-blue-50/30'
      }`}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.csv"
        className="hidden"
        onChange={handleFileInputChange}
      />

      <div className="w-16 h-16 mx-auto mb-4 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center group-hover:scale-110 transition shadow-sm">
        <FileUp size={30} />
      </div>

      <p className="text-base font-semibold text-slate-700">
        Clique para selecionar ou arraste sua petição em PDF
      </p>
      <p className="text-xs text-slate-400 mt-1">
        Suporta PDF (peça única) ou CSV (em lote) · Até 25MB · Em conformidade com a LGPD
      </p>

      <button
        type="button"
        disabled={isLoading}
        onClick={(e) => {
          e.stopPropagation();
          // Simula upload passando um mock de arquivo
          onFileSelected({ name: 'peticao_inicial_voo.pdf', size: 1024 * 1024 * 2 });
        }}
        className="mt-5 px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg shadow-sm hover:bg-blue-700 transition"
      >
        Simular Upload com IA
      </button>
    </div>
  );
}
