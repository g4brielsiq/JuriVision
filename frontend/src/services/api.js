/**
 * Cliente HTTP de Integração com a API Core FastAPI — JuriVision.
 * Rastreabilidade:
 * - ARCHITECTURE.md: Seção 8 (Contratos Oficiais de API REST — 8.1 a 8.6)
 * - MODELING.md: RF-01 a RF-09, RNF-03 (Interoperabilidade), RNF-04 (Usabilidade)
 */

const DEFAULT_API_BASE = "http://localhost:8000";

export function getApiBaseUrl() {
    if (typeof window !== "undefined" && window.__JURIVISION_API_URL__) {
        return window.__JURIVISION_API_URL__;
    }
    if (import.meta?.env?.VITE_API_BASE_URL) {
        return import.meta.env.VITE_API_BASE_URL;
    }
    if (typeof window !== "undefined" && window.location?.origin && window.location.protocol.startsWith("http")) {
        const port = window.location.port;
        if (port !== "5173" && port !== "4173") {
            return window.location.origin;
        }
    }
    return DEFAULT_API_BASE;
}

/**
 * Recupera o token JWT de autenticação do storage e retorna o cabeçalho Bearer.
 */
export function getAuthHeader() {
    if (typeof window === "undefined") return {};
    const token = localStorage.getItem("jurivision_token") || sessionStorage.getItem("jurivision_token");
    return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Constrói em memória um arquivo PDF 1.4 válido (%PDF-1.4) para demonstração real de upload
 * na rota POST /api/v1/processos/upload-pdf caso o usuário deseje testar com 1 clique.
 */
export function buildSamplePetitionPdfFile() {
    const lines = [
        "EXCELENTISSIMO SENHOR JUIZ DA 1a VARA CIVEL DE MACEIO",
        "Processo: 0019283-44.2026.8.02.0001",
        "Magistrado: Dr. Rafael De Amorim",
        "Autor: Lucas Gabriel Rodrigues Silva, inscrito no CPF 123.456.789-00 e RG: 98.765.432-1.",
        "Reu: Companhia Aerea Linhas Brasil S.A.",
        "Acao de reparacao civil contra transportadora aerea decorrente de cancelamento abusivo de voo internacional sem assistencia emergencial ao passageiro.",
    ];

    const streamOps = ["BT", "/F1 12 Tf", "50 750 Td"];
    lines.forEach((line) => {
        streamOps.push(`(${line}) Tj`);
        streamOps.push("0 -18 Td");
    });
    streamOps.push("ET");
    const streamStr = streamOps.join("\n");

    const pdfContent = [
        "%PDF-1.4\n",
        "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n",
        "4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        `5 0 obj\n<< /Length ${streamStr.length} >>\nstream\n${streamStr}\nendstream\nendobj\n`,
        "trailer\n<< /Size 6 /Root 1 0 R >>\n%%EOF\n",
    ].join("");

    const blob = new Blob([pdfContent], { type: "application/pdf" });
    return new File([blob], "peticao_inicial_voo.pdf", { type: "application/pdf" });
}

export function buildSampleBatchCsvFile() {
    const csvText = [
        "numero_processo,tema,magistrado,comarca,autor,reu,texto_resumo,resultado,data_julgamento",
        "0088701-15.2026.8.02.0001,Dano Moral,Dr. Rafael De Amorim,1ª Vara Cível de Maceió,Roberto Almeida Souza,Banco Bradesco S.A.,Cobrança indevida em conta corrente do titular CPF 111.222.333-44 Roberto Almeida Souza,Procedente,2026-10-15",
        "0088702-29.2026.8.02.0001,Plano de Saúde,Dra. Maria Silva,2ª Vara Cível de Maceió,Ana Beatriz Ferreira,Operadora Unimed S.A.,Negativa de cobertura de exame oncológico urgente prescrito para Ana Beatriz Ferreira,Acordo,2026-10-18",
        "0088703-44.2026.8.02.0001,Direito Trabalhista,Dr. Rafael De Amorim,1ª Vara do Trabalho de Maceió,Marcos Vinicius Lima,Tech Softwares LTDA,Reclamação trabalhista referente a horas extras habituais e adicional noturno,Procedente,2026-10-20",
    ].join("\n");

    const blob = new Blob([csvText], { type: "text/csv;charset=utf-8;" });
    return new File([blob], "base_historica_vara_civel.csv", { type: "text/csv" });
}

export async function checkApiHealth() {
    const res = await fetch(`${getApiBaseUrl()}/health`, { method: "GET" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

export async function loginAdvogado(email, senha) {
    const res = await fetch(`${getApiBaseUrl()}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, senha }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        throw new Error(data.detail || "Falha na autenticação. Verifique suas credenciais.");
    }
    if (data.access_token && typeof window !== "undefined") {
        localStorage.setItem("jurivision_token", data.access_token);
    }
    return data;
}

export async function registerAdvogado(payload) {
    const res = await fetch(`${getApiBaseUrl()}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        const mensagens = {
            nome: "Informe um nome entre 2 e 150 caracteres.",
            email: "Informe um e-mail válido de até 150 caracteres.",
            numero_oab: "Informe a OAB no formato número/UF, como 54321/AL.",
            senha: "Informe uma senha entre 8 e 128 caracteres.",
        };
        const detail = data.detail;
        const campos = Array.isArray(detail)
            ? [...new Set(detail.map((error) => error.loc?.[1]))]
            : [];
        const validacao = campos.map((campo) => mensagens[campo]).filter(Boolean).join(" ");
        throw new Error(
            (typeof detail === "string" && detail) || validacao || "Não foi possível criar a conta. Tente novamente.",
        );
    }
    return data;
}

export async function fetchUsuarioAtual() {
    const res = await fetch(`${getApiBaseUrl()}/api/v1/auth/me`, {
        headers: { ...getAuthHeader() },
    });
    if (!res.ok) {
        const err = new Error(`Sessão inválida (HTTP ${res.status})`);
        err.status = res.status;
        throw err;
    }
    return res.json();
}

export function logoutAdvogado() {
    if (typeof window !== "undefined") {
        localStorage.removeItem("jurivision_token");
        sessionStorage.removeItem("jurivision_token");
    }
}

export async function fetchDashboardMetricas() {
    const res = await fetch(`${getApiBaseUrl()}/api/v1/dashboard/metricas`, {
        headers: { ...getAuthHeader() },
    });
    if (!res.ok) throw new Error(`Erro ao carregar métricas: HTTP ${res.status}`);
    return res.json();
}

export async function uploadProcessoPdf(file) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${getApiBaseUrl()}/api/v1/processos/upload-pdf`, {
        method: "POST",
        headers: { ...getAuthHeader() },
        body: formData,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        const err = new Error(data.detail || `Erro no processamento do PDF (HTTP ${res.status}).`);
        err.status = res.status;
        throw err;
    }
    return data;
}

export async function uploadProcessosCsv(file) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${getApiBaseUrl()}/api/v1/processos/upload-csv`, {
        method: "POST",
        headers: { ...getAuthHeader() },
        body: formData,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        const err = new Error(data.detail || `Erro na importação da planilha CSV (HTTP ${res.status}).`);
        err.status = res.status;
        throw err;
    }
    return data;
}

export async function fetchStatusPlano() {
    const res = await fetch(`${getApiBaseUrl()}/api/v1/auth/plano`, {
        headers: { ...getAuthHeader() },
    });
    if (!res.ok) {
        throw new Error(`Erro ao consultar plano (HTTP ${res.status}).`);
    }
    return res.json();
}

export async function atualizarPlanoAssinatura(plano = "PRO", codigoConvite = "CONAD2026") {
    const res = await fetch(`${getApiBaseUrl()}/api/v1/auth/plano/upgrade`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify({ plano, codigo_convite: codigoConvite }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        const err = new Error(data.detail || `Não foi possível atualizar o plano (HTTP ${res.status}).`);
        err.status = res.status;
        throw err;
    }
    return data;
}

export async function fetchProcessos({
    tema = "",
    juiz = "",
    busca = "",
    ordenacao = "recentes",
    ids = null,
    pagina = 1,
    limite = 8,
} = {}) {
    const params = new URLSearchParams();
    if (tema) params.set("tema", tema);
    if (juiz) params.set("juiz", juiz);
    if (busca) params.set("busca", busca);
    if (ordenacao) params.set("ordenacao", ordenacao);
    if (ids !== null && ids !== undefined) params.set("ids", String(ids));
    params.set("pagina", String(pagina));
    params.set("limite", String(limite));

    const res = await fetch(`${getApiBaseUrl()}/api/v1/processos?${params.toString()}`, {
        headers: { ...getAuthHeader() },
    });
    if (!res.ok) throw new Error(`Erro ao consultar processos: HTTP ${res.status}`);
    return res.json();
}

export async function fetchFiltrosProcessos() {
    const res = await fetch(`${getApiBaseUrl()}/api/v1/processos/filtros`, {
        headers: { ...getAuthHeader() },
    });
    if (!res.ok) throw new Error(`Erro ao carregar filtros: HTTP ${res.status}`);
    return res.json();
}

export async function excluirProcesso(idProcesso) {
    const res = await fetch(`${getApiBaseUrl()}/api/v1/processos/${encodeURIComponent(idProcesso)}`, {
        method: "DELETE",
        headers: { ...getAuthHeader() },
    });
    if (res.status === 404) {
        throw new Error(`Processo ${idProcesso} não encontrado.`);
    }
    if (!res.ok) {
        throw new Error(`Não foi possível excluir o julgado (HTTP ${res.status}).`);
    }
    return true;
}

export async function fetchProcessoDetalhes(idProcesso) {
    const res = await fetch(`${getApiBaseUrl()}/api/v1/processos/${encodeURIComponent(idProcesso)}`, {
        headers: { ...getAuthHeader() },
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        throw new Error(data.detail || `Processo ${idProcesso} não encontrado.`);
    }
    return data;
}

export async function salvarProcesso(payload, idProcesso) {
    const caminho = idProcesso ? `/${encodeURIComponent(idProcesso)}` : "";
    const res = await fetch(`${getApiBaseUrl()}/api/v1/processos${caminho}`, {
        method: idProcesso ? "PUT" : "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify(payload),
    });
    if (res.status === 409) throw new Error("Já existe uma decisão com esse número CNJ.");
    if (res.status === 404) throw new Error("A decisão não está mais disponível para edição.");
    if (res.status === 422) throw new Error("Revise os campos e o formato do número CNJ.");
    if (!res.ok) throw new Error("Não foi possível salvar a decisão. Tente novamente.");
    return res.json();
}

export async function preverAnonimizacao(payload, signal) {
    const res = await fetch(`${getApiBaseUrl()}/api/v1/processos/anonimizacao/previa`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify(payload),
        signal,
    });
    if (!res.ok) throw new Error("Não foi possível atualizar a prévia.");
    return res.json();
}

export function getRelatorioPdfUrl(idProcesso) {
    const base = `${getApiBaseUrl()}/api/v1/relatorios/processo/${encodeURIComponent(idProcesso)}/pdf`;
    if (typeof window !== "undefined") {
        const token = localStorage.getItem("jurivision_token") || sessionStorage.getItem("jurivision_token");
        if (token) {
            return `${base}?token=${encodeURIComponent(token)}`;
        }
    }
    return base;
}

export async function consultarProcessoDatajud(numeroProcesso) {
    const res = await fetch(`${getApiBaseUrl()}/api/v1/processos/datajud/${encodeURIComponent(numeroProcesso)}`, {
        headers: { ...getAuthHeader() },
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        throw new Error(data.detail || `Erro ao consultar metadados no DataJud (HTTP ${res.status}).`);
    }
    return data;
}
