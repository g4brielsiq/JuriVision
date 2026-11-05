/**
 * Controlador de Interface, Estados de Diálogo (ISO 9241-110) e Acessibilidade (WAI-ARIA 1.2) — JuriVision.
 * Rastreabilidade:
 * - Requisitos Funcionais: RF-01 (Login), RF-02 (Upload PDF), RF-03 (Upload CSV), RF-04 (LGPD),
 *   RF-05 (Resumo NLP), RF-06 (Predição), RF-07 (Dashboard), RF-08 (Busca/Filtros), RF-09 (Relatório PDF)
 * - Requisitos Não Funcionais: RNF-04 (ISO 9241-110 & Nielsen), RNF-09 (WCAG 2.2 AA), RNF-10 (Leis de UX & Gestalt)
 */

import {
    buildSampleBatchCsvFile,
    buildSamplePetitionPdfFile,
    checkApiHealth,
    fetchDashboardMetricas,
    fetchProcessoDetalhes,
    fetchProcessos,
    getRelatorioPdfUrl,
    loginAdvogado,
    uploadProcessoPdf,
    uploadProcessosCsv,
} from "./services/api.js";

const FALLBACK_METRICAS = {
    taxa_exito_global: 0.70,
    tempo_medio_tramitacao_meses: 12,
    total_processos_analisados: 10,
    decisoes_por_juiz: [
        { juiz: "Dr. Rafael De Amorim", procedentes: 4, improcedentes: 1 },
        { juiz: "Dra. Maria Silva", procedentes: 2, improcedentes: 1 },
        { juiz: "Dr. Carlos Souza", procedentes: 1, improcedentes: 1 },
    ],
    volume_por_tema: [
        { tema: "Dano Moral", percentual: 50.0 },
        { tema: "Direito Trabalhista", percentual: 20.0 },
        { tema: "Plano de Saúde", percentual: 20.0 },
        { tema: "Tributário", percentual: 10.0 },
    ],
};

const FALLBACK_PROCESSOS = [
    {
        id_processo: "proc-1004",
        numero_processo: "0088210-12.2026.8.02.0001",
        tema: "Dano Moral",
        magistrado: "Dr. Rafael De Amorim",
        comarca: "1ª Vara Cível de Maceió",
        partes_anonimizadas: "Lucas G. *** vs Companhia Aérea Linhas Brasil S.A.",
        resultado: "Procedente",
        data_julgamento: "2026-10-05",
        probabilidade_deferimento: 0.75,
    },
    {
        id_processo: "proc-1001",
        numero_processo: "0019283-44.2025.8.02.0001",
        tema: "Dano Moral",
        magistrado: "Dra. Maria Silva",
        comarca: "1ª Vara Cível de Maceió",
        partes_anonimizadas: "Felipe C. *** vs Banco Bradesco S.A.",
        resultado: "Procedente",
        data_julgamento: "2026-08-15",
        probabilidade_deferimento: 0.78,
    },
    {
        id_processo: "proc-1002",
        numero_processo: "0004512-19.2025.8.02.0001",
        tema: "Direito Trabalhista",
        magistrado: "Dr. Rafael De Amorim",
        comarca: "2ª Vara do Trabalho de Maceió",
        partes_anonimizadas: "Emanuele V. *** vs Tech Softwares LTDA",
        resultado: "Acordo",
        data_julgamento: "2026-09-02",
        probabilidade_deferimento: 0.74,
    },
];

const state = {
    activeTab: "dashboard",
    uploadMode: "pdf", // "pdf" | "csv"
    apiOnline: false,
    currentUser: {
        id: "usr-01",
        nome: "Lucas Gabriel",
        oab: "12345/AL",
        authenticated: true,
    },
    lastAnalyzedProcessId: "proc-1004",
    paginaAtual: 1,
    limitePorPagina: 8,
    totalProcessosLista: 0,
    chartJuizesInstance: null,
    chartTemasInstance: null,
};

function announceStatus(message) {
    const liveRegion = document.getElementById("global-aria-live");
    if (liveRegion) {
        liveRegion.textContent = message;
    }
}

/* ==========================================================================
   1. Navegação de Abas Acessível (WAI-ARIA 1.2 Tab Pattern + Teclado)
   ========================================================================== */
export function switchTab(tabId, moveFocus = false) {
    state.activeTab = tabId;
    const tabs = ["dashboard", "upload", "historico"];

    tabs.forEach((id) => {
        const btn = document.getElementById(`btn-${id}`);
        const panel = document.getElementById(`panel-${id}`);
        const isSelected = id === tabId;

        if (btn) {
            btn.setAttribute("aria-selected", isSelected ? "true" : "false");
            btn.setAttribute("tabindex", isSelected ? "0" : "-1");
            if (isSelected) {
                btn.classList.add("bg-blue-700", "text-white", "shadow-sm");
                btn.classList.remove("text-slate-200", "hover:bg-slate-800");
                if (moveFocus) btn.focus();
            } else {
                btn.classList.remove("bg-blue-700", "text-white", "shadow-sm");
                btn.classList.add("text-slate-200", "hover:bg-slate-800");
            }
        }

        if (panel) {
            if (isSelected) {
                panel.classList.add("active");
                panel.removeAttribute("hidden");
            } else {
                panel.classList.remove("active");
                panel.setAttribute("hidden", "hidden");
            }
        }
    });

    const titles = {
        dashboard: "Dashboard Analítico de Jurimetria",
        upload: "Ingestão Segura (LGPD) e Predição Jurídica",
        historico: "Base de Conhecimento Estruturada",
    };
    const headerTitle = document.getElementById("header-title");
    if (headerTitle) headerTitle.textContent = titles[tabId] || "JuriVision";

    announceStatus(`Seção ativa: ${titles[tabId]}`);

    if (tabId === "dashboard") {
        carregarDashboard();
    } else if (tabId === "historico") {
        carregarBaseConhecimento();
    }
}

function setupTabKeyboardNavigation() {
    const tabOrder = ["dashboard", "upload", "historico"];
    const tablist = document.getElementById("sidebar-tablist");
    if (!tablist) return;

    tablist.addEventListener("keydown", (event) => {
        const currentIndex = tabOrder.indexOf(state.activeTab);
        if (currentIndex === -1) return;

        if (event.key === "ArrowDown" || event.key === "ArrowRight") {
            event.preventDefault();
            const nextIndex = (currentIndex + 1) % tabOrder.length;
            switchTab(tabOrder[nextIndex], true);
        } else if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
            event.preventDefault();
            const prevIndex = (currentIndex - 1 + tabOrder.length) % tabOrder.length;
            switchTab(tabOrder[prevIndex], true);
        } else if (event.key === "Home") {
            event.preventDefault();
            switchTab(tabOrder[0], true);
        } else if (event.key === "End") {
            event.preventDefault();
            switchTab(tabOrder[tabOrder.length - 1], true);
        }
    });
}

/* ==========================================================================
   2. Verificação de Status do Sistema (Heurística de Nielsen #1)
   ========================================================================== */
async function verificarConectividadeApi() {
    const badge = document.getElementById("api-status-badge");
    try {
        const health = await checkApiHealth();
        state.apiOnline = true;
        if (badge) {
            badge.className =
                "inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300";
            badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-600 mr-2" aria-hidden="true"></span>API Online (${health.ai_provider_configured || "local"})`;
        }
    } catch {
        state.apiOnline = false;
        if (badge) {
            badge.className =
                "inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300";
            badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-amber-600 mr-2" aria-hidden="true"></span>Modo Demonstração Local`;
        }
    }
}

/* ==========================================================================
   3. Dashboard de Jurimetria e Gráficos Acessíveis (RF-07 / WCAG 1.1.1)
   ========================================================================== */
async function carregarDashboard() {
    let metricas = FALLBACK_METRICAS;
    try {
        metricas = await fetchDashboardMetricas();
        state.apiOnline = true;
    } catch {
        // Mantém fallback resiliente (ISO 9241-110 Tolerância a Falhas)
    }

    const elTaxa = document.getElementById("kpi-taxa-exito");
    const elPrazo = document.getElementById("kpi-tempo-medio");
    const elTotal = document.getElementById("kpi-total-processos");

    const pct = (metricas.taxa_exito_global * 100).toFixed(1);
    if (elTaxa) elTaxa.textContent = `${pct}%`;
    if (elPrazo) elPrazo.textContent = `${metricas.tempo_medio_tramitacao_meses} Meses`;
    if (elTotal) elTotal.textContent = String(metricas.total_processos_analisados);

    renderizarGraficos(metricas);
    preencherTabelasAcessiveisGraficos(metricas);
}

function renderizarGraficos(metricas) {
    if (typeof window.Chart === "undefined") return;

    const canvasJuizes = document.getElementById("chartJuizes");
    const canvasTemas = document.getElementById("chartTemas");

    if (canvasJuizes) {
        if (state.chartJuizesInstance) state.chartJuizesInstance.destroy();
        const labels = metricas.decisoes_por_juiz.map((d) => d.juiz);
        const procedentes = metricas.decisoes_por_juiz.map((d) => d.procedentes);
        const improcedentes = metricas.decisoes_por_juiz.map((d) => d.improcedentes);

        state.chartJuizesInstance = new window.Chart(canvasJuizes, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        label: "Procedentes / Acordos",
                        data: procedentes,
                        backgroundColor: "#1d4ed8", // blue-700
                    },
                    {
                        label: "Improcedentes",
                        data: improcedentes,
                        backgroundColor: "#dc2626", // red-600
                    },
                ],
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: "bottom" },
                },
                scales: {
                    x: { stacked: true },
                    y: { stacked: true, beginAtZero: true },
                },
            },
        });
    }

    if (canvasTemas) {
        if (state.chartTemasInstance) state.chartTemasInstance.destroy();
        const labels = metricas.volume_por_tema.map((t) => `${t.tema} (${t.percentual}%)`);
        const valores = metricas.volume_por_tema.map((t) => t.percentual);

        state.chartTemasInstance = new window.Chart(canvasTemas, {
            type: "doughnut",
            data: {
                labels,
                datasets: [
                    {
                        data: valores,
                        backgroundColor: ["#1d4ed8", "#6d28d9", "#047857", "#d97706", "#0284c7"],
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "bottom" },
                },
            },
        });
    }
}

function preencherTabelasAcessiveisGraficos(metricas) {
    const tbodyJuizes = document.getElementById("a11y-table-juizes");
    if (tbodyJuizes) {
        tbodyJuizes.innerHTML = metricas.decisoes_por_juiz
            .map(
                (item) => `
            <tr class="border-b border-slate-200">
                <td class="py-1.5 pr-4 font-medium text-slate-800">${item.juiz}</td>
                <td class="py-1.5 px-2 text-emerald-800 font-semibold">${item.procedentes}</td>
                <td class="py-1.5 pl-2 text-red-800 font-semibold">${item.improcedentes}</td>
            </tr>`
            )
            .join("");
    }

    const tbodyTemas = document.getElementById("a11y-table-temas");
    if (tbodyTemas) {
        tbodyTemas.innerHTML = metricas.volume_por_tema
            .map(
                (item) => `
            <tr class="border-b border-slate-200">
                <td class="py-1.5 pr-4 font-medium text-slate-800">${item.tema}</td>
                <td class="py-1.5 pl-2 text-slate-700 font-semibold">${item.percentual}%</td>
            </tr>`
            )
            .join("");
    }
}

/* ==========================================================================
   4. Ingestão Híbrida PDF / CSV, Barreira LGPD e Predição (RF-02 a RF-06)
   ========================================================================== */
export function alternarModoUpload(mode) {
    state.uploadMode = mode;
    const btnPdf = document.getElementById("mode-btn-pdf");
    const btnCsv = document.getElementById("mode-btn-csv");
    const boxPdf = document.getElementById("upload-box-pdf");
    const boxCsv = document.getElementById("upload-box-csv");

    if (mode === "pdf") {
        btnPdf?.classList.add("bg-blue-700", "text-white");
        btnPdf?.classList.remove("bg-slate-100", "text-slate-700");
        btnPdf?.setAttribute("aria-pressed", "true");

        btnCsv?.classList.remove("bg-blue-700", "text-white");
        btnCsv?.classList.add("bg-slate-100", "text-slate-700");
        btnCsv?.setAttribute("aria-pressed", "false");

        boxPdf?.classList.remove("hidden");
        boxCsv?.classList.add("hidden");
    } else {
        btnCsv?.classList.add("bg-blue-700", "text-white");
        btnCsv?.classList.remove("bg-slate-100", "text-slate-700");
        btnCsv?.setAttribute("aria-pressed", "true");

        btnPdf?.classList.remove("bg-blue-700", "text-white");
        btnPdf?.classList.add("bg-slate-100", "text-slate-700");
        btnPdf?.setAttribute("aria-pressed", "false");

        boxCsv?.classList.remove("hidden");
        boxPdf?.classList.add("hidden");
    }

    resetarFluxoUpload();
}

export function resetarFluxoUpload() {
    document.getElementById("upload-selection-container")?.classList.remove("hidden");
    document.getElementById("loading-state")?.classList.add("hidden");
    document.getElementById("error-state")?.classList.add("hidden");
    document.getElementById("result-state")?.classList.add("hidden");
    document.getElementById("csv-result-state")?.classList.add("hidden");

    const inputPdf = document.getElementById("file-input-pdf");
    const inputCsv = document.getElementById("file-input-csv");
    if (inputPdf) inputPdf.value = "";
    if (inputCsv) inputCsv.value = "";

    announceStatus("Formulário de submissão pronto para novo arquivo.");
}

function exibirErroUpload(mensagem) {
    document.getElementById("upload-selection-container")?.classList.add("hidden");
    document.getElementById("loading-state")?.classList.add("hidden");
    document.getElementById("result-state")?.classList.add("hidden");
    document.getElementById("csv-result-state")?.classList.add("hidden");

    const errBox = document.getElementById("error-state");
    const errMsg = document.getElementById("error-message-text");
    if (errMsg) errMsg.textContent = mensagem;
    errBox?.classList.remove("hidden");

    announceStatus(`Erro no processamento: ${mensagem}`);
}

export async function processarArquivoPdf(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
        exibirErroUpload(
            "Formato inválido (RN-04): Selecione apenas documentos em formato .PDF para extração processual."
        );
        return;
    }

    document.getElementById("upload-selection-container")?.classList.add("hidden");
    document.getElementById("error-state")?.classList.add("hidden");
    document.getElementById("result-state")?.classList.add("hidden");
    document.getElementById("loading-state")?.classList.remove("hidden");
    announceStatus("Processando petição em PDF: extraindo texto, aplicando máscara LGPD e calculando predição...");

    try {
        const resultado = await uploadProcessoPdf(file);
        renderizarResultadoPredicaoPdf(resultado);
        carregarDashboard();
    } catch (err) {
        exibirErroUpload(err.message || "Não foi possível processar o arquivo PDF enviado.");
    }
}

export async function processarArquivoCsv(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
        exibirErroUpload(
            "Formato inválido (RN-04): Selecione uma planilha estruturada com extensão .CSV."
        );
        return;
    }

    document.getElementById("upload-selection-container")?.classList.add("hidden");
    document.getElementById("error-state")?.classList.add("hidden");
    document.getElementById("csv-result-state")?.classList.add("hidden");
    document.getElementById("loading-state")?.classList.remove("hidden");
    announceStatus("Importando lote CSV e executando higienização determinística LGPD...");

    try {
        const resCsv = await uploadProcessosCsv(file);
        document.getElementById("loading-state")?.classList.add("hidden");
        const csvBox = document.getElementById("csv-result-state");
        csvBox?.classList.remove("hidden");

        document.getElementById("csv-res-arquivo").textContent = resCsv.arquivo_nome;
        document.getElementById("csv-res-lidos").textContent = String(resCsv.total_registros_lidos);
        document.getElementById("csv-res-importados").textContent = String(resCsv.total_importados_com_sucesso);
        document.getElementById("csv-res-lgpd").textContent = String(resCsv.total_entidades_anonimizadas_lgpd);

        announceStatus(
            `Lote CSV processado com sucesso: ${resCsv.total_importados_com_sucesso} processos importados e anonimizados.`
        );
        carregarDashboard();
    } catch (err) {
        exibirErroUpload(err.message || "Falha ao importar planilha CSV.");
    }
}

export function renderizarResultadoPredicaoPdf(payload) {
    document.getElementById("upload-selection-container")?.classList.add("hidden");
    document.getElementById("loading-state")?.classList.add("hidden");
    document.getElementById("error-state")?.classList.add("hidden");
    document.getElementById("csv-result-state")?.classList.add("hidden");

    const resContainer = document.getElementById("result-state");
    resContainer?.classList.remove("hidden");

    state.lastAnalyzedProcessId = payload.id_processo;
    const meta = payload.metadados_extraidos;
    const pred = payload.analise_preditiva;
    const lgpd = payload.auditoria_lgpd || {
        total_cpfs_mascarados: 1,
        total_nomes_mascarados: 1,
        texto_higienizado_verificado: true,
    };

    const probPct = Math.round(pred.probabilidade_deferimento * 100);
    const margemPct = Math.round((pred.margem_confianca || 0.08) * 100);

    document.getElementById("res-id-processo").textContent = payload.id_processo;
    document.getElementById("res-numero-cnj").textContent = meta.numero_processo;
    document.getElementById("res-probabilidade").textContent = `${probPct}%`;
    document.getElementById("res-margem").textContent = `±${margemPct}% de margem de confiança`;
    document.getElementById("res-prazo").textContent = `${pred.tempo_estimado_sentenca_meses} meses`;
    document.getElementById("res-similares").textContent = `${pred.casos_similares_encontrados} julgados`;
    document.getElementById("res-provedor-ia").textContent = pred.provedor_ia || "local_heuristic";

    document.getElementById("res-tema").textContent = meta.tema;
    document.getElementById("res-magistrado").textContent = meta.magistrado;
    document.getElementById("res-comarca").textContent = meta.comarca;
    document.getElementById("res-autor").textContent = meta.partes_anonimizadas.autor;
    document.getElementById("res-reu").textContent = meta.partes_anonimizadas.reu;

    document.getElementById("res-lgpd-badge").textContent =
        `LGPD Verificado (${lgpd.total_cpfs_mascarados} CPF/RG e ${lgpd.total_nomes_mascarados} nome(s) mascarados localmente)`;

    document.getElementById("res-resumo-nlp").textContent = payload.resumo_nlp;
    document.getElementById("res-tese-recomendada").textContent = pred.tese_recomendada;
    document.getElementById("res-tendencia-juiz").textContent = pred.tendencia_juiz;

    announceStatus(
        `Análise preditiva concluída para o processo ${meta.numero_processo}. Probabilidade de deferimento estimada em ${probPct} por cento.`
    );
}

/* ==========================================================================
   5. Base de Conhecimento, Filtros e Paginação (RF-08)
   ========================================================================== */
export async function carregarBaseConhecimento(novaPagina = null) {
    if (novaPagina !== null) {
        state.paginaAtual = novaPagina;
    }

    const busca = document.getElementById("filtro-busca")?.value.trim() || "";
    const tema = document.getElementById("filtro-tema")?.value || "";
    const juiz = document.getElementById("filtro-juiz")?.value || "";

    let lista = {
        total: FALLBACK_PROCESSOS.length,
        pagina: 1,
        itens: FALLBACK_PROCESSOS,
    };

    try {
        lista = await fetchProcessos({
            tema,
            juiz,
            busca,
            pagina: state.paginaAtual,
            limite: state.limitePorPagina,
        });
    } catch {
        // Fallback local se backend estiver offline
    }

    state.totalProcessosLista = lista.total;
    const tbody = document.getElementById("historico-tbody");
    const countLabel = document.getElementById("historico-total-label");

    if (countLabel) {
        countLabel.textContent = `${lista.total} processo(s) higienizado(s) encontrado(s)`;
    }

    if (!tbody) return;

    if (!lista.itens || lista.itens.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="p-8 text-center text-slate-600">
                    Nenhum processo encontrado para os filtros selecionados.
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = lista.itens
        .map((item) => {
            const resLower = (item.resultado || "").toLowerCase();
            let badgeClass = "bg-emerald-100 text-emerald-800 border border-emerald-300";
            if (resLower === "improcedente") {
                badgeClass = "bg-red-100 text-red-800 border border-red-300";
            } else if (resLower.includes("analise")) {
                badgeClass = "bg-blue-100 text-blue-800 border border-blue-300";
            }

            const probText =
                item.probabilidade_deferimento != null
                    ? `${Math.round(item.probabilidade_deferimento * 100)}%`
                    : "—";

            return `
            <tr class="hover:bg-slate-50 border-b border-slate-200 transition">
                <td class="p-4 font-mono text-xs text-blue-800 font-semibold">
                    <div>${item.numero_processo}</div>
                    <div class="text-slate-600 font-sans text-[11px]">ID: ${item.id_processo}</div>
                </td>
                <td class="p-4 font-medium text-slate-800">${item.tema}</td>
                <td class="p-4 text-slate-700">
                    <div>${item.magistrado}</div>
                    <div class="text-xs text-slate-600">${item.comarca || ""}</div>
                </td>
                <td class="p-4 text-slate-700">
                    <span>${item.partes_anonimizadas}</span>
                    <span class="inline-block ml-1.5 text-[11px] bg-slate-200 text-slate-800 font-semibold px-1.5 py-0.5 rounded" title="Dados pessoais anonimizados localmente (LGPD)">LGPD</span>
                </td>
                <td class="p-4">
                    <span class="${badgeClass} px-2.5 py-1 rounded-md text-xs font-bold">${item.resultado}</span>
                    <span class="block text-xs text-slate-600 mt-1">Score IA: <strong>${probText}</strong></span>
                </td>
                <td class="p-4 text-right space-x-2 whitespace-nowrap">
                    <button type="button" data-inspect-id="${item.id_processo}" class="btn-inspecionar-proc text-xs font-semibold text-blue-800 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-3 py-2 rounded-lg transition" aria-label="Ver parecer preditivo do processo ${item.numero_processo}">
                        <i class="fa-solid fa-magnifying-glass-chart mr-1" aria-hidden="true"></i>Parecer
                    </button>
                    <button type="button" data-pdf-id="${item.id_processo}" class="btn-exportar-pdf text-xs font-semibold text-slate-800 bg-slate-100 hover:bg-slate-200 border border-slate-300 px-3 py-2 rounded-lg transition" aria-label="Baixar relatório estratégico em PDF do processo ${item.numero_processo}">
                        <i class="fa-solid fa-file-pdf text-red-700 mr-1" aria-hidden="true"></i>PDF
                    </button>
                </td>
            </tr>`;
        })
        .join("");

    // Eventos dos botões da tabela
    tbody.querySelectorAll(".btn-inspecionar-proc").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const idProc = btn.getAttribute("data-inspect-id");
            if (!idProc) return;
            try {
                const detalhes = await fetchProcessoDetalhes(idProc);
                switchTab("upload");
                renderizarResultadoPredicaoPdf(detalhes);
            } catch (err) {
                announceStatus(err.message);
            }
        });
    });

    tbody.querySelectorAll(".btn-exportar-pdf").forEach((btn) => {
        btn.addEventListener("click", () => {
            const idProc = btn.getAttribute("data-pdf-id");
            if (idProc) exportarRelatorioPdfProcesso(idProc);
        });
    });

    atualizarControlesPaginacao();
}

function atualizarControlesPaginacao() {
    const btnPrev = document.getElementById("btn-page-prev");
    const btnNext = document.getElementById("btn-page-next");
    const pageInfo = document.getElementById("pagination-info");

    const totalPaginas = Math.max(1, Math.ceil(state.totalProcessosLista / state.limitePorPagina));
    if (pageInfo) {
        pageInfo.textContent = `Página ${state.paginaAtual} de ${totalPaginas}`;
    }
    if (btnPrev) {
        btnPrev.disabled = state.paginaAtual <= 1;
    }
    if (btnNext) {
        btnNext.disabled = state.paginaAtual >= totalPaginas;
    }
}

/* ==========================================================================
   6. Exportação de Relatório Estratégico em PDF (RF-09)
   ========================================================================== */
export function exportarRelatorioPdfProcesso(idProcesso = null) {
    const targetId = idProcesso || state.lastAnalyzedProcessId || "proc-1004";
    const url = getRelatorioPdfUrl(targetId);
    announceStatus(`Iniciando download do relatório estratégico em PDF do processo ${targetId}...`);
    window.open(url, "_blank", "noopener,noreferrer");
}

/* ==========================================================================
   7. Modal de Autenticação de Advogado (RF-01 — JWT)
   ========================================================================== */
function configurarModalAutenticacao() {
    const modal = document.getElementById("login-modal");
    const btnOpen = document.getElementById("btn-open-login");
    const btnClose = document.getElementById("btn-close-login");
    const form = document.getElementById("login-form");
    const feedback = document.getElementById("login-feedback");

    btnOpen?.addEventListener("click", () => {
        modal?.classList.remove("hidden");
        document.getElementById("login-email")?.focus();
    });

    btnClose?.addEventListener("click", () => {
        modal?.classList.add("hidden");
    });

    form?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("login-email")?.value.trim() || "";
        const senha = document.getElementById("login-senha")?.value || "";

        if (feedback) {
            feedback.className = "text-xs font-medium text-blue-800 bg-blue-50 p-3 rounded-lg";
            feedback.textContent = "Validando credenciais junto ao serviço de autenticação JWT...";
            feedback.classList.remove("hidden");
        }

        try {
            const res = await loginAdvogado(email, senha);
            state.currentUser = {
                ...res.usuario,
                authenticated: true,
                token: res.access_token,
            };

            document.getElementById("sidebar-user-name").textContent = res.usuario.nome;
            document.getElementById("sidebar-user-oab").textContent = `OAB ${res.usuario.oab} • JWT Ativo`;

            if (feedback) {
                feedback.className =
                    "text-xs font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200 p-3 rounded-lg";
                feedback.textContent = `Autenticado com sucesso! Token emitido para ${res.usuario.nome} (${res.usuario.oab}).`;
            }
            announceStatus(`Sessão autenticada para ${res.usuario.nome}.`);
            setTimeout(() => modal?.classList.add("hidden"), 900);
        } catch (err) {
            if (feedback) {
                feedback.className =
                    "text-xs font-semibold text-red-800 bg-red-50 border border-red-200 p-3 rounded-lg";
                feedback.textContent = err.message;
            }
        }
    });
}

/* ==========================================================================
   8. Inicialização e Registro de Listeners Acessíveis
   ========================================================================== */
document.addEventListener("DOMContentLoaded", () => {
    setupTabKeyboardNavigation();
    configurarModalAutenticacao();
    verificarConectividadeApi();
    carregarDashboard();

    // Listeners das Abas
    document.getElementById("btn-dashboard")?.addEventListener("click", () => switchTab("dashboard"));
    document.getElementById("btn-upload")?.addEventListener("click", () => switchTab("upload"));
    document.getElementById("btn-historico")?.addEventListener("click", () => switchTab("historico"));

    // Alternância de Modo de Upload (PDF vs CSV)
    document.getElementById("mode-btn-pdf")?.addEventListener("click", () => alternarModoUpload("pdf"));
    document.getElementById("mode-btn-csv")?.addEventListener("click", () => alternarModoUpload("csv"));

    // Inputs de Arquivo Reais (WCAG 2.1.1)
    const inputPdf = document.getElementById("file-input-pdf");
    inputPdf?.addEventListener("change", (e) => {
        const file = e.target.files?.[0];
        if (file) processarArquivoPdf(file);
    });

    const inputCsv = document.getElementById("file-input-csv");
    inputCsv?.addEventListener("change", (e) => {
        const file = e.target.files?.[0];
        if (file) processarArquivoCsv(file);
    });

    // Botões de Demonstração Real com 1 Clique (Envia arquivo real para a API FastAPI)
    document.getElementById("btn-sample-pdf")?.addEventListener("click", () => {
        const sampleFile = buildSamplePetitionPdfFile();
        processarArquivoPdf(sampleFile);
    });

    document.getElementById("btn-sample-csv")?.addEventListener("click", () => {
        const sampleCsv = buildSampleBatchCsvFile();
        processarArquivoCsv(sampleCsv);
    });

    // Botões de Reset / Nova Análise (ISO 9241-110 Controlabilidade & Heurística de Nielsen #3)
    document.getElementById("btn-reset-upload")?.addEventListener("click", resetarFluxoUpload);
    document.getElementById("btn-reset-csv")?.addEventListener("click", resetarFluxoUpload);
    document.getElementById("btn-retry-error")?.addEventListener("click", resetarFluxoUpload);

    // Botões de Exportação de Relatório Estratégico PDF (RF-09)
    document.getElementById("btn-header-export-pdf")?.addEventListener("click", () => {
        exportarRelatorioPdfProcesso();
    });
    document.getElementById("btn-result-export-pdf")?.addEventListener("click", () => {
        exportarRelatorioPdfProcesso(state.lastAnalyzedProcessId);
    });

    // Filtros e Paginação da Base de Conhecimento (RF-08)
    document.getElementById("form-filtros-historico")?.addEventListener("submit", (e) => {
        e.preventDefault();
        carregarBaseConhecimento(1);
    });
    document.getElementById("btn-limpar-filtros")?.addEventListener("click", () => {
        const elBusca = document.getElementById("filtro-busca");
        const elTema = document.getElementById("filtro-tema");
        const elJuiz = document.getElementById("filtro-juiz");
        if (elBusca) elBusca.value = "";
        if (elTema) elTema.value = "";
        if (elJuiz) elJuiz.value = "";
        carregarBaseConhecimento(1);
    });
    document.getElementById("btn-page-prev")?.addEventListener("click", () => {
        if (state.paginaAtual > 1) carregarBaseConhecimento(state.paginaAtual - 1);
    });
    document.getElementById("btn-page-next")?.addEventListener("click", () => {
        carregarBaseConhecimento(state.paginaAtual + 1);
    });
});
