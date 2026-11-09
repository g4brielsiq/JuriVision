import React, { useState } from 'react';
import { uploadProcessoPDF } from '../services/processoService';
import { UploadDropzone, PredictionResult, LoadingSpinner } from '../components';

/**
 * Página de Ingestão de Novo Processo (PDF) e Parecer Preditivo.
 * Contrato oficial: Seção 7.3 do ARCHITECTURE.md.
 */
export default function UploadPage() {
  const [status, setStatus] = useState('idle'); // 'idle' | 'processing' | 'done' | 'error'
  const [predictionData, setPredictionData] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  const handleFileSelected = async (file) => {
    setStatus('processing');
    setErrorMessage('');

    try {
      const response = await uploadProcessoPDF(file);
      setPredictionData(response);
      setStatus('done');
    } catch (error) {
      console.error('Erro na esteira de processamento:', error);
      setErrorMessage(error.message || 'Falha ao processar o arquivo. Tente novamente.');
      setStatus('error');
    }
  };

  const handleReset = () => {
    setStatus('idle');
    setPredictionData(null);
    setErrorMessage('');
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-8">
        {/* Cabeçalho da Tela */}
        <div className="text-center mb-6">
          <h3 className="text-2xl font-bold text-slate-800">Ingestão de Novo Processo</h3>
          <p className="text-sm text-slate-500 mt-1">
            Faça upload da petição inicial em PDF para passar pela esteira de OCR, Anonimização LGPD e Predição Estatística.
          </p>
        </div>

        {/* Estado 1: Área de Drop / Seleção de Arquivo */}
        {status === 'idle' && (
          <UploadDropzone onFileSelected={handleFileSelected} isLoading={false} />
        )}

        {/* Estado 2: Processamento Assíncrono da IA */}
        {status === 'processing' && (
          <LoadingSpinner
            title="Processamento Inteligente em Andamento..."
            description="Higienizando dados sensíveis (LGPD), gerando resumo NLP e consultando modelos preditivos."
          />
        )}

        {/* Estado 3: Parecer Preditivo e Metadados Extraídos */}
        {status === 'done' && (
          <PredictionResult data={predictionData} onReset={handleReset} />
        )}

        {/* Estado de Erro */}
        {status === 'error' && (
          <div className="text-center py-8 space-y-4">
            <div className="inline-flex p-3 bg-rose-50 text-rose-600 rounded-full">
              <span className="text-xl font-bold">!</span>
            </div>
            <div>
              <h4 className="text-base font-bold text-slate-800">Não foi possível processar o documento</h4>
              <p className="text-xs text-rose-600 mt-1">{errorMessage}</p>
            </div>
            <button
              type="button"
              onClick={handleReset}
              className="px-4 py-2 bg-slate-800 text-white text-xs font-semibold rounded-lg hover:bg-slate-700 transition"
            >
              Tentar novamente
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
