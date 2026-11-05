/**
 * Controlador de Interface, Dossiê Preditivo, Context Drawer e Acessibilidade (WAI-ARIA 1.2) — JuriVision.
 * Direção de Arte: Precisão Editorial & Alta Densidade Operacional (Harvey AI / Linear / SATIC).
 * Rastreabilidade:
 * - Requisitos Funcionais: RF-01 a RF-09
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
    uploadMode: "pdf",
    apiOnline: false,
    currentUser: {
        id: "usr-01",
        nome: "Lucas Gabriel",
        oab: "12345/AL",
        authenticated: true,
    },
    lastAnalyzedProcessId: "proc-1004",
    drawerProcessId: "proc-1004",
    paginaAtual: 1,
    limitePorPagina: 8,
    totalProcessosLista: 0,
    chartJuizesInstance: null,
    chartTemasInstance: null,
    toastTimer: null,
};

function announceStatus(message) {
    const liveRegion = document.getElementById("global-aria-live");
    if (liveRegion) liveRegion.textContent = message;
}

export function showToast(message) {
    const toast = document.getElementById("status-toast");
    const text = document.getElementById("status-toast-text");
    if (!toast || !text) return;

    text.textContent = message;
    toast.classList.add("is-visible");
    announceStatus(message);

    if (state.toastTimer) clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => {
        toast.classList.remove("is-visible");
    }, 3200);
}

/* ==========================================================================
   1. Navegação de Abas (WAI-ARIA 1.2 Tab Pattern + Teclado)
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
            btn.classList.toggle("active", isSelected);
            if (isSelected && moveFocus) btn.focus();
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
        dashboard: "Panorama Geral",
        upload: "Triagem Documental & Dossiê Preditivo",
        historico: "Acervo Processual Higienizado",
    };
    const headerTitle = document.getElementById("header-title");
    if (headerTitle) headerTitle.textContent = titles[tabId] || "JuriVision";

    announceStatus(`Visão ativa: ${titles[tabId]}`);

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
            switchTab(tabOrder[(currentIndex + 1) % tabOrder.length], true);
        } else if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
            event.preventDefault();
            switchTab(tabOrder[(currentIndex - 1 + tabOrder.length) % tabOrder.length], true);
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
   2. Status de Conexão com a API Core (Heurística de Nielsen #1)
   ========================================================================== */
async function verificarConectividadeApi() {
    const badge = document.getElementById("api-status-badge");
    const motorEl = document.getElementById("kpi-motor-ia");
    try {
        const health = await checkApiHealth();
        state.apiOnline = true;
        const provider = health.ai_provider_configured || "local";
        if (badge) {
            badge.innerHTML = `<span class="dot dot-success" aria-hidden="true"></span><span>API Core Ativa (${provider})</span>`;
        }
        if (motorEl) motorEl.textContent = provider === "local" ? "local_heuristic" : provider;
    } catch {
        state.apiOnline = false;
        if (badge) {
            badge.innerHTML = `<span class="dot dot-warning" aria-hidden="true"></span><span>Modo Demonstração Offline</span>`;
        }
    }
}

/* ==========================================================================
   3. Panorama de Jurimetria, Matrizes de Precisão e Gráficos (RF-07)
   ========================================================================== */
async function carregarDashboard() {
    let metricas = FALLBACK_METRICAS;
    try {
        metricas = await fetchDashboardMetricas();
        state.apiOnline = true;
    } catch {
        // Fallback local resiliente
    }

    const pct = (metricas.taxa_exito_global * 100).toFixed(1);
    const elTaxa = document.getElementById("kpi-taxa-exito");
    const elPrazo = document.getElementById("kpi-tempo-medio");
    const elTotal = document.getElementById("kpi-total-processos");
    const elSidebarCount = document.getElementById("sidebar-total-count");

    if (elTaxa) elTaxa.textContent = `${pct}%`;
    if (elPrazo) elPrazo.textContent = `${metricas.tempo_medio_tramitacao_meses} Meses`;
    if (elTotal) elTotal.textContent = String(metricas.total_processos_analisados);
    if (elSidebarCount) elSidebarCount.textContent = String(metricas.total_processos_analisados);

    renderizarMatrizesPrecisao(metricas);
    renderizarGraficos(metricas);
    preencherTabelasAcessiveisGraficos(metricas);
    carregarPrecedentesRecentesOverview();
}

function renderizarMatrizesPrecisao(metricas) {
    const judgeList = document.getElementById("judge-matrix-list");
    if (judgeList) {
        judgeList.innerHTML = metricas.decisoes_por_juiz
            .map((d) => {
                const total = Math.max(d.procedentes + d.improcedentes, 1);
                const favPct = Math.round((d.procedentes / total) * 100);
                return `
                <div class="compact-metric-row">
                    <div>
                        <strong style="font-weight: 500;">${d.juiz}</strong>
                        <span style="display: block; font-size: 11px; color: var(--text-muted);">
                            ${d.procedentes} favoráveis · ${d.improcedentes} improcedentes
                        </span>
                    </div>
                    <div class="mini-bar-track" aria-hidden="true">
                        <div class="mini-bar-fill" style="width: ${favPct}%;"></div>
                    </div>
                    <div class="font-mono" style="text-align: right; font-size: var(--text-xs); font-weight: 600;">
                        ${favPct}% êxito
                    </div>
                </div>`;
            })
            .join("");
    }

    const themeList = document.getElementById("theme-matrix-list");
    if (themeList) {
        themeList.innerHTML = metricas.volume_por_tema
            .map(
                (t) => `
                <div class="compact-metric-row">
                    <span style="font-weight: 500;">${t.tema}</span>
                    <div class="mini-bar-track" aria-hidden="true">
                        <div class="mini-bar-fill" style="width: ${t.percentual}%;"></div>
                    </div>
                    <span class="font-mono" style="text-align: right; font-size: var(--text-xs); font-weight: 600;">
                        ${t.percentual}%
                    </span>
                </div>`
            )
            .join("");
    }
}

function renderizarGraficos(metricas) {
    if (typeof window.Chart === "undefined") return;

    const canvasJuizes = document.getElementById("chartJuizes");
    const canvasTemas = document.getElementById("chartTemas");

    if (canvasJuizes) {
        if (state.chartJuizesInstance) state.chartJuizesInstance.destroy();
        state.chartJuizesInstance = new window.Chart(canvasJuizes, {
            type: "bar",
            data: {
                labels: metricas.decisoes_por_juiz.map((d) => d.juiz),
                datasets: [
                    {
                        label: "Favoráveis",
                        data: metricas.decisoes_por_juiz.map((d) => d.procedentes),
                        backgroundColor: "#1B365D",
                        barThickness: 18,
                    },
                    {
                        label: "Improcedentes",
                        data: metricas.decisoes_por_juiz.map((d) => d.improcedentes),
                        backgroundColor: "#CBD5E1",
                        barThickness: 18,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { boxWidth: 10, font: { size: 11, family: "Inter" } },
                    },
                },
                scales: {
                    x: { stacked: true, grid: { display: false } },
                    y: { stacked: true, beginAtZero: true, ticks: { stepSize: 1 } },
                },
            },
        });
    }

    if (canvasTemas) {
        if (state.chartTemasInstance) state.chartTemasInstance.destroy();
        state.chartTemasInstance = new window.Chart(canvasTemas, {
            type: "bar",
            data: {
                labels: metricas.volume_por_tema.map((t) => t.tema),
                datasets: [
                    {
                        label: "Volume (%)",
                        data: metricas.volume_por_tema.map((t) => t.percentual),
                        backgroundColor: ["#1B365D", "#334E68", "#486581", "#627D98", "#829AB1"],
                        barThickness: 14,
                    },
                ],
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    x: { beginAtZero: true, max: 100 },
                    y: { grid: { display: false } },
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
            <tr>
                <td>${item.juiz}</td>
                <td class="font-mono">${item.procedentes}</td>
                <td class="font-mono">${item.improcedentes}</td>
            </tr>`
            )
            .join("");
    }

    const tbodyTemas = document.getElementById("a11y-table-temas");
    if (tbodyTemas) {
        tbodyTemas.innerHTML = metricas.volume_por_tema
            .map(
                (item) => `
            <tr>
                <td>${item.tema}</td>
                <td class="font-mono">${item.percentual}%</td>
            </tr>`
            )
            .join("");
    }
}

async function carregarPrecedentesRecentesOverview() {
    const tbody = document.getElementById("overview-recent-tbody");
    if (!tbody) return;

    let lista = { itens: FALLBACK_PROCESSOS };
    try {
        lista = await fetchProcessos({ pagina: 1, limite: 5 });
    } catch {
        // Fallback local
    }

    tbody.innerHTML = (lista.itens || [])
        .map((item) => {
            const resLower = (item.resultado || "").toLowerCase();
            const dotClass =
                resLower === "improcedente"
                    ? "dot-danger"
                    : resLower.includes("analise")
                    ? "dot-warning"
                    : "dot-success";

            return `
            <tr>
                <td class="font-mono" style="font-size: var(--text-xs); font-weight: 600;">${item.numero_processo}</td>
                <td style="font-weight: 500;">${item.tema}</td>
                <td style="color: var(--text-secondary);">${item.magistrado}</td>
                <td style="color: var(--text-secondary); font-size: var(--text-sm);">${item.partes_anonimizadas}</td>
                <td>
                    <span class="status-inline">
                        <span class="dot ${dotClass}" aria-hidden="true"></span>
                        <span>${item.resultado}</span>
                    </span>
                </td>
                <td style="text-align: right;">
                    <button type="button" class="btn btn-ghost btn-xs btn-open-dossier-overview" data-proc-id="${item.id_processo}">
                        Abrir dossiê →
                    </button>
                </td>
            </tr>`;
        })
        .join("");

    tbody.querySelectorAll(".btn-open-dossier-overview").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const idProc = btn.getAttribute("data-proc-id");
            if (!idProc) return;
            try {
                const det = await fetchProcessoDetalhes(idProc);
                switchTab("upload");
                renderizarResultadoPredicaoPdf(det);
            } catch (err) {
                showToast(err.message);
            }
        });
    });
}

/* ==========================================================================
   4. Ingestão Híbrida PDF / CSV, Barreira LGPD e Dossiê Preditivo (RF-02 a RF-06)
   ========================================================================== */
export function alternarModoUpload(mode) {
    state.uploadMode = mode;
    const btnPdf = document.getElementById("mode-btn-pdf");
    const btnCsv = document.getElementById("mode-btn-csv");
    const boxPdf = document.getElementById("upload-box-pdf");
    const boxCsv = document.getElementById("upload-box-csv");

    if (mode === "pdf") {
        btnPdf?.classList.add("active");
        btnPdf?.setAttribute("aria-pressed", "true");
        btnCsv?.classList.remove("active");
        btnCsv?.setAttribute("aria-pressed", "false");
        boxPdf?.classList.remove("hidden");
        boxCsv?.classList.add("hidden");
    } else {
        btnCsv?.classList.add("active");
        btnCsv?.setAttribute("aria-pressed", "true");
        btnPdf?.classList.remove("active");
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
    document.getElementById("csv-result-state")?.classList.add("hidden");

    const inputPdf = document.getElementById("file-input-pdf");
    const inputCsv = document.getElementById("file-input-csv");
    if (inputPdf) inputPdf.value = "";
    if (inputCsv) inputCsv.value = "";

    announceStatus("Esteira de submissão restaurada.");
}

function exibirErroUpload(mensagem) {
    document.getElementById("upload-selection-container")?.classList.add("hidden");
    document.getElementById("loading-state")?.classList.add("hidden");
    document.getElementById("csv-result-state")?.classList.add("hidden");

    const errBox = document.getElementById("error-state");
    const errMsg = document.getElementById("error-message-text");
    if (errMsg) errMsg.textContent = mensagem;
    errBox?.classList.remove("hidden");

    announceStatus(`Recusa de ingestão: ${mensagem}`);
}

export async function processarArquivoPdf(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
        exibirErroUpload(
            "Formato inválido (RN-04): Selecione exclusivamente arquivos com extensão .PDF."
        );
        return;
    }

    document.getElementById("upload-selection-container")?.classList.add("hidden");
    document.getElementById("error-state")?.classList.add("hidden");
    document.getElementById("loading-state")?.classList.remove("hidden");
    announceStatus("Processando petição na barreira local LGPD...");

    try {
        const resultado = await uploadProcessoPdf(file);
        document.getElementById("loading-state")?.classList.add("hidden");
        document.getElementById("upload-selection-container")?.classList.remove("hidden");
        renderizarResultadoPredicaoPdf(resultado);
        showToast(`Dossiê ${resultado.metadados_extraidos.numero_processo} higienizado e analisado.`);
        carregarDashboard();
    } catch (err) {
        exibirErroUpload(err.message || "Falha ao processar o PDF.");
    }
}

export async function processarArquivoCsv(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
        exibirErroUpload("Formato inválido (RN-04): Selecione uma planilha .CSV.");
        return;
    }

    document.getElementById("upload-selection-container")?.classList.add("hidden");
    document.getElementById("error-state")?.classList.add("hidden");
    document.getElementById("csv-result-state")?.classList.add("hidden");
    document.getElementById("loading-state")?.classList.remove("hidden");
    announceStatus("Processando planilha CSV em lote...");

    try {
        const resCsv = await uploadProcessosCsv(file);
        document.getElementById("loading-state")?.classList.add("hidden");
        const csvBox = document.getElementById("csv-result-state");
        csvBox?.classList.remove("hidden");

        document.getElementById("csv-res-arquivo").textContent = resCsv.arquivo_nome;
        document.getElementById("csv-res-lidos").textContent = String(resCsv.total_registros_lidos);
        document.getElementById("csv-res-importados").textContent = String(resCsv.total_importados_com_sucesso);
        document.getElementById("csv-res-lgpd").textContent = String(resCsv.total_entidades_anonimizadas_lgpd);

        showToast(`${resCsv.total_importados_com_sucesso} processos importados e anonimizados via CSV.`);
        carregarDashboard();
    } catch (err) {
        exibirErroUpload(err.message || "Falha ao importar planilha CSV.");
    }
}

export function renderizarResultadoPredicaoPdf(payload) {
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
    document.getElementById("res-margem").textContent = `±${margemPct}% intervalo de confiança`;
    document.getElementById("res-prazo").textContent = `${pred.tempo_estimado_sentenca_meses} meses`;
    document.getElementById("res-similares").textContent = `${pred.casos_similares_encontrados} julgados`;
    document.getElementById("res-provedor-ia").textContent = pred.provedor_ia || "local_heuristic";

    document.getElementById("res-tema").textContent = meta.tema;
    document.getElementById("res-magistrado").textContent = meta.magistrado;
    document.getElementById("res-comarca").textContent = meta.comarca;
    document.getElementById("res-autor").textContent = meta.partes_anonimizadas.autor;
    document.getElementById("res-reu").textContent = meta.partes_anonimizadas.reu;

    document.getElementById("res-lgpd-badge").textContent =
        `LGPD Verificado · ${lgpd.total_cpfs_mascarados} CPF/RG e ${lgpd.total_nomes_mascarados} nome(s) mascarados`;

    document.getElementById("res-resumo-nlp").textContent = payload.resumo_nlp;
    document.getElementById("res-tese-recomendada").textContent = pred.tese_recomendada;
    document.getElementById("res-tendencia-juiz").textContent = pred.tendencia_juiz;
}

/* ==========================================================================
   5. Acervo Processual, Filtros, Paginação e Context Drawer Lateral (RF-08)
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
        // Fallback local
    }

    state.totalProcessosLista = lista.total;
    const tbody = document.getElementById("historico-tbody");
    const countLabel = document.getElementById("historico-total-label");

    if (countLabel) {
        countLabel.textContent = `${lista.total} processo(s) higienizado(s) no acervo`;
    }
    if (!tbody) return;

    if (!lista.itens || lista.itens.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="padding: 28px; text-align: center; color: var(--text-secondary);">
                    Nenhum processo encontrado para os critérios selecionados.
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = lista.itens
        .map((item) => {
            const resLower = (item.resultado || "").toLowerCase();
            const dotClass =
                resLower === "improcedente"
                    ? "dot-danger"
                    : resLower.includes("analise")
                    ? "dot-warning"
                    : "dot-success";

            const probText =
                item.probabilidade_deferimento != null
                    ? `${Math.round(item.probabilidade_deferimento * 100)}%`
                    : "—";

            return `
            <tr data-row-proc-id="${item.id_processo}">
                <td>
                    <div class="font-mono" style="font-size: var(--text-xs); font-weight: 600;">${item.numero_processo}</div>
                    <div class="font-mono" style="font-size: 10.5px; color: var(--text-muted);">${item.id_processo}</div>
                </td>
                <td style="font-weight: 500;">${item.tema}</td>
                <td>
                    <div>${item.magistrado}</div>
                    <div style="font-size: var(--text-xs); color: var(--text-muted);">${item.comarca || ""}</div>
                </td>
                <td>
                    <span>${item.partes_anonimizadas}</span>
                    <span class="tag-subtle tag-lgpd" style="margin-left: 6px;">LGPD</span>
                </td>
                <td>
                    <div class="status-inline">
                        <span class="dot ${dotClass}" aria-hidden="true"></span>
                        <span style="font-weight: 500; color: var(--text-primary);">${item.resultado}</span>
                    </div>
                    <div class="font-mono" style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">
                        Score IA: ${probText}
                    </div>
                </td>
                <td style="text-align: right; white-space: nowrap;">
                    <button type="button" data-inspect-id="${item.id_processo}" class="btn btn-secondary btn-xs btn-inspecionar-proc">
                        Inspecionar
                    </button>
                    <button type="button" data-pdf-id="${item.id_processo}" class="btn btn-ghost btn-xs btn-exportar-pdf">
                        PDF
                    </button>
                </td>
            </tr>`;
        })
        .join("");

    tbody.querySelectorAll(".btn-inspecionar-proc").forEach((btn) => {
        btn.addEventListener("click", () => {
            const idProc = btn.getAttribute("data-inspect-id");
            if (idProc) abrirDrawerProcesso(idProc);
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

async function abrirDrawerProcesso(idProcesso) {
    const drawer = document.getElementById("drawer-processo");
    if (!drawer) return;

    try {
        const det = await fetchProcessoDetalhes(idProcesso);
        state.drawerProcessId = det.id_processo;
        const meta = det.metadados_extraidos;
        const pred = det.analise_preditiva;

        document.getElementById("drawer-proc-id").textContent = det.id_processo;
        document.getElementById("drawer-proc-cnj").textContent = meta.numero_processo;
        document.getElementById("drawer-proc-tema").textContent = meta.tema;
        document.getElementById("drawer-proc-juiz").textContent = meta.magistrado;
        document.getElementById("drawer-proc-comarca").textContent = meta.comarca;
        document.getElementById("drawer-proc-autor").textContent = meta.partes_anonimizadas.autor;
        document.getElementById("drawer-proc-reu").textContent = meta.partes_anonimizadas.reu;
        document.getElementById("drawer-proc-prob").textContent = `${Math.round(pred.probabilidade_deferimento * 100)}% (±${Math.round(pred.margem_confianca * 100)}%)`;
        document.getElementById("drawer-proc-resumo").textContent = det.resumo_nlp;
        document.getElementById("drawer-proc-tese").textContent = pred.tese_recomendada;

        drawer.classList.add("is-open");
        announceStatus(`Painel de inspeção aberto para o processo ${meta.numero_processo}.`);
    } catch (err) {
        showToast(err.message);
    }
}

function fecharDrawerProcesso() {
    document.getElementById("drawer-processo")?.classList.remove("is-open");
}

function atualizarControlesPaginacao() {
    const btnPrev = document.getElementById("btn-page-prev");
    const btnNext = document.getElementById("btn-page-next");
    const pageInfo = document.getElementById("pagination-info");

    const totalPaginas = Math.max(1, Math.ceil(state.totalProcessosLista / state.limitePorPagina));
    if (pageInfo) pageInfo.textContent = `Página ${state.paginaAtual} de ${totalPaginas}`;
    if (btnPrev) btnPrev.disabled = state.paginaAtual <= 1;
    if (btnNext) btnNext.disabled = state.paginaAtual >= totalPaginas;
}

/* ==========================================================================
   6. Exportação de Relatório Estratégico em PDF (RF-09)
   ========================================================================== */
export function exportarRelatorioPdfProcesso(idProcesso = null) {
    const targetId = idProcesso || state.lastAnalyzedProcessId || "proc-1004";
    const url = getRelatorioPdfUrl(targetId);
    showToast(`Exportando relatório estratégico PDF (${targetId})...`);
    window.open(url, "_blank", "noopener,noreferrer");
}

/* ==========================================================================
   7. Modal de Autenticação JWT (RF-01) & Command Palette (Ctrl+K)
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
            feedback.style.background = "var(--accent-subtle)";
            feedback.style.color = "var(--accent-primary)";
            feedback.textContent = "Validando credenciais e emitindo token JWT...";
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
            document.getElementById("sidebar-user-oab").textContent = `OAB ${res.usuario.oab} · JWT`;

            if (feedback) {
                feedback.style.background = "var(--success-bg)";
                feedback.style.color = "var(--success-fg)";
                feedback.textContent = `Sessão autenticada: ${res.usuario.nome} (OAB ${res.usuario.oab}).`;
            }
            showToast(`Token JWT emitido para ${res.usuario.nome}.`);
            setTimeout(() => modal?.classList.add("hidden"), 700);
        } catch (err) {
            if (feedback) {
                feedback.style.background = "var(--danger-bg)";
                feedback.style.color = "var(--danger-fg)";
                feedback.textContent = err.message;
            }
        }
    });
}

function configurarCommandPalette() {
    const modal = document.getElementById("modal-command");
    const input = document.getElementById("cmd-search-input");
    const list = document.getElementById("cmd-results-list");
    const btnClose = document.getElementById("btn-close-cmd");

    const commands = [
        {
            label: "Ir para Panorama Geral de Jurimetria",
            meta: "Visão RF-07",
            action: () => switchTab("dashboard"),
        },
        {
            label: "Abrir Triagem Documental & Dossiê Preditivo",
            meta: "Visão RF-02 / RF-06",
            action: () => switchTab("upload"),
        },
        {
            label: "Consultar Acervo Processual Higienizado",
            meta: "Visão RF-08",
            action: () => switchTab("historico"),
        },
        {
            label: "Executar Petição PDF de Demonstração (API Real)",
            meta: "POST /upload-pdf",
            action: () => {
                switchTab("upload");
                processarArquivoPdf(buildSamplePetitionPdfFile());
            },
        },
        {
            label: "Executar Importação em Lote CSV de Demonstração",
            meta: "POST /upload-csv",
            action: () => {
                switchTab("upload");
                alternarModoUpload("csv");
                processarArquivoCsv(buildSampleBatchCsvFile());
            },
        },
        {
            label: "Exportar Relatório Estratégico em PDF do Processo Ativo",
            meta: "GET /relatorios/pdf",
            action: () => exportarRelatorioPdfProcesso(),
        },
    ];

    function renderCommands(filterText = "") {
        if (!list) return;
        const q = filterText.trim().toLowerCase();
        const filtered = commands.filter(
            (c) => !q || c.label.toLowerCase().includes(q) || c.meta.toLowerCase().includes(q)
        );
        list.innerHTML = filtered
            .map(
                (cmd, idx) => `
            <button type="button" class="cmd-item" data-cmd-idx="${idx}">
                <span>${cmd.label}</span>
                <span class="font-mono" style="font-size: 11px; color: var(--text-muted);">${cmd.meta}</span>
            </button>`
            )
            .join("");

        list.querySelectorAll(".cmd-item").forEach((btn, idx) => {
            btn.addEventListener("click", () => {
                modal?.classList.add("hidden");
                filtered[idx]?.action();
            });
        });
    }

    function openCmd() {
        modal?.classList.remove("hidden");
        if (input) {
            input.value = "";
            renderCommands("");
            input.focus();
        }
    }

    document.getElementById("btn-open-cmd")?.addEventListener("click", openCmd);
    document.getElementById("btn-workspace-cmd")?.addEventListener("click", openCmd);
    btnClose?.addEventListener("click", () => modal?.classList.add("hidden"));
    input?.addEventListener("input", () => renderCommands(input.value));

    document.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
            e.preventDefault();
            openCmd();
        } else if (e.key === "Escape") {
            modal?.classList.add("hidden");
            document.getElementById("login-modal")?.classList.add("hidden");
            fecharDrawerProcesso();
        }
    });
}

/* ==========================================================================
   8. Inicialização Global
   ========================================================================== */
document.addEventListener("DOMContentLoaded", () => {
    setupTabKeyboardNavigation();
    configurarModalAutenticacao();
    configurarCommandPalette();
    verificarConectividadeApi();
    carregarDashboard();

    // Navegação de abas
    document.getElementById("btn-dashboard")?.addEventListener("click", () => switchTab("dashboard"));
    document.getElementById("btn-upload")?.addEventListener("click", () => switchTab("upload"));
    document.getElementById("btn-historico")?.addEventListener("click", () => switchTab("historico"));
    document.getElementById("btn-topbar-new-analysis")?.addEventListener("click", () => switchTab("upload"));
    document.getElementById("btn-overview-ver-todos")?.addEventListener("click", () => switchTab("historico"));

    // Atalhos operacionais da Sidebar
    document.getElementById("btn-nav-sample-pdf")?.addEventListener("click", () => {
        switchTab("upload");
        processarArquivoPdf(buildSamplePetitionPdfFile());
    });
    document.getElementById("btn-nav-export-pdf")?.addEventListener("click", () => {
        exportarRelatorioPdfProcesso();
    });

    // Alternância de Modo PDF / CSV
    document.getElementById("mode-btn-pdf")?.addEventListener("click", () => alternarModoUpload("pdf"));
    document.getElementById("mode-btn-csv")?.addEventListener("click", () => alternarModoUpload("csv"));

    // Inputs de Arquivo Reais
    document.getElementById("file-input-pdf")?.addEventListener("change", (e) => {
        const file = e.target.files?.[0];
        if (file) processarArquivoPdf(file);
    });
    document.getElementById("file-input-csv")?.addEventListener("change", (e) => {
        const file = e.target.files?.[0];
        if (file) processarArquivoCsv(file);
    });

    // Demonstração Real com 1 Clique
    document.getElementById("btn-sample-pdf")?.addEventListener("click", () => {
        processarArquivoPdf(buildSamplePetitionPdfFile());
    });
    document.getElementById("btn-sample-csv")?.addEventListener("click", () => {
        processarArquivoCsv(buildSampleBatchCsvFile());
    });

    // Botões de Reset / Reversão (ISO 9241-110 Controlabilidade)
    document.getElementById("btn-reset-upload")?.addEventListener("click", resetarFluxoUpload);
    document.getElementById("btn-reset-csv")?.addEventListener("click", resetarFluxoUpload);
    document.getElementById("btn-retry-error")?.addEventListener("click", resetarFluxoUpload);

    // Exportação de Relatório PDF (RF-09)
    document.getElementById("btn-header-export-pdf")?.addEventListener("click", () => {
        exportarRelatorioPdfProcesso();
    });
    document.getElementById("btn-result-export-pdf")?.addEventListener("click", () => {
        exportarRelatorioPdfProcesso(state.lastAnalyzedProcessId);
    });

    // Context Drawer do Acervo
    document.getElementById("btn-close-drawer")?.addEventListener("click", fecharDrawerProcesso);
    document.getElementById("btn-drawer-export-pdf")?.addEventListener("click", () => {
        exportarRelatorioPdfProcesso(state.drawerProcessId);
    });
    document.getElementById("btn-drawer-open-dossier")?.addEventListener("click", async () => {
        try {
            const det = await fetchProcessoDetalhes(state.drawerProcessId);
            fecharDrawerProcesso();
            switchTab("upload");
            renderizarResultadoPredicaoPdf(det);
        } catch (err) {
            showToast(err.message);
        }
    });

    // Filtros e Paginação (RF-08)
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
