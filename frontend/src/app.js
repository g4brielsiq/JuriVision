/**
 * Controlador de Experiência Jurídica, Pesquisa Jurisprudencial, Leitura Documental e Jurimetria — JuriVision.
 * Direção Estética e Funcional: Institucional Contemporâneo (Azul-Marinho Institucional + Branco/Cinza Neutro)
 * Referência: Padrões de Usabilidade Jurídica (Jusbrasil, STF/SCON, Turivius, Astrea)
 * Rastreabilidade:
 * - Requisitos Funcionais: RF-01 a RF-09
 * - Requisitos Não Funcionais: RNF-04 (ISO 9241-110 & Nielsen), RNF-09 (WCAG 2.2 AA), RNF-10 (Leis de UX & Gestalt)
 */

import { configurarFormularioJulgado } from "./components/julgado-form.js";
import {
    atualizarPlanoAssinatura,
    buildSampleBatchCsvFile,
    buildSamplePetitionPdfFile,
    checkApiHealth,
    consultarProcessoDatajud,
    excluirProcesso,
    fetchDashboardMetricas,
    fetchFiltrosProcessos,
    fetchProcessoDetalhes,
    fetchProcessos,
    fetchStatusPlano,
    fetchUsuarioAtual,
    getRelatorioPdfUrl,
    loginAdvogado,
    logoutAdvogado,
    registerAdvogado,
    sincronizarLoteDatajud,
    uploadProcessoPdf,
    uploadProcessosCsv,
} from "./services/api.js";

const EMPTY_METRICAS = {
    taxa_exito_global: 0,
    tempo_medio_tramitacao_meses: 0,
    total_processos_analisados: 0,
    distribuicao_resultados: {
        procedentes: 0,
        acordos: 0,
        improcedentes: 0,
        em_analise: 0,
    },
    decisoes_por_juiz: [],
    volume_por_tema: [],
};

function getSavedStorageKey(userId) {
    return userId ? `jurivision_saved_decisions_${userId}` : "jurivision_saved_decisions_anon";
}

function loadSavedIds(userId = null) {
    if (!userId) return new Set();
    try {
        const raw = window.localStorage.getItem(getSavedStorageKey(userId));
        if (raw) {
            const parsed = JSON.parse(raw);
            if (Array.isArray(parsed)) return new Set(parsed);
        }
    } catch {
        // Ignorar erro de localStorage em ambientes restritos
    }
    return new Set();
}

function persistSavedIds(savedSet, userId = null) {
    if (!userId) return;
    try {
        window.localStorage.setItem(
            getSavedStorageKey(userId),
            JSON.stringify(Array.from(savedSet))
        );
    } catch {
        // Ignorar erro de localStorage
    }
}

const DEFAULT_FREE_PLAN = {
    plano: "FREE",
    analises_realizadas: 0,
    limite_analises_free: 3,
    analises_restantes: 3,
    recursos_pro_liberados: false,
    lote_csv_liberado: false,
    tese_aprofundada_liberada: false,
};

let abrirContaModal = null;

const state = {
    viewMode: "landing", // "landing" | "workspace"
    selectedLandingGoal: "historico",
    activeTab: "historico",
    resultsViewMode: "cards", // "cards" (documental) | "table" (comparativa)
    uploadMode: "pdf",
    apiOnline: false,
    lastApiLoaded: false,
    currentUser: {
        id: null,
        nome: "",
        oab: "",
        authenticated: false,
    },
    savedDecisions: new Set(),
    lastAnalyzedProcessId: null,
    drawerProcessId: null,
    currentDrawerPayload: null,
    paginaAtual: 1,
    limitePorPagina: 8,
    totalProcessosLista: 0,
    lastLoadedItems: [],
    planStatus: { ...DEFAULT_FREE_PLAN },
    dashboardFiltroTema: "",
    dashboardFiltroJuiz: "",
    juizChartMode: "qtd",
    temaChartMode: "vol",
    lastDashboardMetricas: null,
    chartResultadosInstance: null,
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
    }, 3400);
}

function formatarDataJulgamento(isoStr) {
    if (!isoStr) return "Data não informada na origem";
    const parts = String(isoStr).split("-");
    if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    return isoStr;
}

function updateSavedCounterUI() {
    const badge = document.getElementById("sidebar-saved-count");
    if (badge) {
        badge.textContent = String(state.savedDecisions.size);
    }
}

export function toggleSalvarDecisao(idProcesso) {
    if (!idProcesso) return;
    if (state.savedDecisions.has(idProcesso)) {
        state.savedDecisions.delete(idProcesso);
        showToast("Decisão removida da biblioteca do escritório.");
    } else {
        state.savedDecisions.add(idProcesso);
        showToast("Decisão salva na biblioteca para consulta futura.");
    }
    persistSavedIds(state.savedDecisions, state.currentUser?.id);
    updateSavedCounterUI();
    renderizarListaDecisoes(state.lastLoadedItems);
}

export async function copiarReferenciaDecisao(item) {
    if (!item) return;
    const orgao = item.comarca || "Órgão julgador cadastrado";
    const num = item.numero_processo || item.id_processo;
    const rel = item.magistrado || "Magistrado(a) não especificado(a)";
    const data = formatarDataJulgamento(item.data_julgamento);
    const assunto = item.tema || "Assunto processual";

    const refTexto = `TJAL. ${orgao}. Processo nº ${num}. Assunto: ${assunto}. Magistrado(a): ${rel}. Julgamento em: ${data}.`;

    try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(refTexto);
        }
        showToast(`Referência copiada: Processo nº ${num}`);
    } catch {
        showToast(`Referência pronta: ${refTexto}`);
    }
}

/* ==========================================================================
   1. Visibilidade Imediata e Navegação Principal (WAI-ARIA 1.2)
   ========================================================================== */
function setupScrollReveal() {
    document.documentElement.classList.remove("js-motion-ready");
    document.querySelectorAll("[data-reveal]").forEach((el) => {
        el.classList.add("is-revealed");
    });
}

function refreshScrollReveal(scope = document) {
    scope.querySelectorAll("[data-reveal]").forEach((el) => {
        el.classList.add("is-revealed");
    });
}

export function switchTab(tabId, moveFocus = false) {
    state.activeTab = tabId;
    const tabs = ["historico", "dashboard", "upload"];
    let activePanel = null;

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
                activePanel = panel;
            } else {
                panel.classList.remove("active");
                panel.setAttribute("hidden", "hidden");
            }
        }
    });

    const titles = {
        historico: "Pesquisa Jurisprudencial",
        dashboard: "Análise Jurimétrica do Conjunto",
        upload: "Análise Comparativa de Petição e Importação",
    };
    const headerTitle = document.getElementById("header-title");
    if (headerTitle) headerTitle.textContent = titles[tabId] || "JuriVision";

    announceStatus(`Área ativa: ${titles[tabId]}`);

    if (activePanel) {
        refreshScrollReveal(activePanel);
    }

    if (tabId === "dashboard") {
        carregarDashboard();
    } else if (tabId === "historico") {
        carregarBaseConhecimento();
    }
}

function setupTabKeyboardNavigation() {
    const tabOrder = ["historico", "dashboard", "upload"];
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
   2. Disponibilidade da Base Jurisprudencial (Seção 18.6)
   ========================================================================== */
async function verificarConectividadeApi() {
    const badge = document.getElementById("api-status-badge");
    try {
        await checkApiHealth();
        state.apiOnline = true;
        if (badge) {
            badge.innerHTML = `<span class="dot dot-success" aria-hidden="true"></span><span>Servidor conectado</span>`;
        }
    } catch {
        state.apiOnline = false;
        if (badge) {
            badge.innerHTML = `<span class="dot dot-warning" aria-hidden="true"></span><span>Base Local</span>`;
        }
    }
}

/* ==========================================================================
   3. Jurimetria e Análise Estatística Dinâmica (RF-07)
   ========================================================================== */
function atualizarResumoFiltrosDashboard() {
    const summaryEl = document.getElementById("dash-filter-summary");
    const clearBtn = document.getElementById("btn-dash-limpar-filtros");
    const partes = [];
    if (state.dashboardFiltroTema) partes.push(`Assunto: ${state.dashboardFiltroTema}`);
    if (state.dashboardFiltroJuiz) partes.push(`Magistrado(a): ${state.dashboardFiltroJuiz}`);

    if (summaryEl) {
        summaryEl.textContent = partes.length
            ? `Recorte ativo — ${partes.join(" · ")}`
            : "Exibindo todo o acervo analisado";
    }
    if (clearBtn) {
        clearBtn.classList.toggle("hidden", partes.length === 0);
    }
}

async function carregarDashboard() {
    const tema = state.dashboardFiltroTema || "";
    const juiz = state.dashboardFiltroJuiz || "";
    atualizarResumoFiltrosDashboard();

    let metricas = {
        ...EMPTY_METRICAS,
        distribuicao_resultados: { ...EMPTY_METRICAS.distribuicao_resultados },
        decisoes_por_juiz: [],
        volume_por_tema: [],
    };
    let apiLoaded = false;
    try {
        metricas = await fetchDashboardMetricas({ tema, juiz });
        state.apiOnline = true;
        apiLoaded = true;
    } catch {
        // Servidor indisponível: exibe métricas zeradas reais
    }

    state.lastDashboardMetricas = metricas;
    const total = Number(metricas.total_processos_analisados ?? 0);
    const dist = obterDistribuicaoResultados(metricas);
    const decididos = Number(
        metricas.total_decididos ?? dist.procedentes + dist.acordos + dist.improcedentes
    );
    const favCount = dist.procedentes + dist.acordos;
    const pct = (Number(metricas.taxa_exito_global ?? 0) * 100).toFixed(1);
    const prazoMeses = Number(metricas.tempo_medio_tramitacao_meses ?? 0);
    const temFiltros = Boolean(tema || juiz);

    // Usuário novo (acervo vazio, sem filtros): um único estado vazio no lugar de gráficos em branco
    const acervoVazio = apiLoaded && total === 0 && !temFiltros;
    document.getElementById("dashboard-empty-state")?.classList.toggle("hidden", !acervoVazio);
    document.getElementById("dashboard-content")?.classList.toggle("hidden", acervoVazio);
    if (!temFiltros) atualizarRecorteAcervo(metricas.recorte, total, apiLoaded);

    const elTaxa = document.getElementById("kpi-taxa-exito");
    const elDenom = document.getElementById("kpi-taxa-denominador");
    const elPrazo = document.getElementById("kpi-tempo-medio");
    const elTotal = document.getElementById("kpi-total-processos");
    const elTotalDenom = document.getElementById("kpi-total-denominador");
    const elSidebarCount = document.getElementById("sidebar-total-count");

    if (elTaxa) elTaxa.textContent = decididos > 0 ? `${pct}%` : "—";
    if (elDenom) {
        if (!apiLoaded) {
            elDenom.textContent = "Aguardando conexão com o servidor";
        } else if (decididos > 0) {
            elDenom.textContent = `${favCount} favoráveis em ${decididos} ${decididos === 1 ? "decisão" : "decisões"} com desfecho`;
        } else {
            elDenom.textContent = total > 0
                ? "Nenhuma decisão com desfecho no recorte"
                : "Sem decisões no recorte atual";
        }
    }
    const elEmAnalise = document.getElementById("kpi-em-analise");
    const elEmAnaliseDenom = document.getElementById("kpi-em-analise-denominador");
    if (elEmAnalise) elEmAnalise.textContent = String(dist.em_analise);
    if (elEmAnaliseDenom) {
        elEmAnaliseDenom.textContent = dist.em_analise > 0
            ? "Sem desfecho · fora do cálculo da proporção"
            : "Todas as decisões têm desfecho";
    }
    if (elPrazo) elPrazo.textContent = total > 0 ? `${prazoMeses} Meses` : "—";
    if (elTotal) elTotal.textContent = String(total);
    if (elTotalDenom) {
        elTotalDenom.textContent = total > 0
            ? (total === 1 ? "Decisão indexada no recorte" : "Decisões indexadas no recorte")
            : "Aguardando acervo para análise";
    }
    if (elSidebarCount && !tema && !juiz) elSidebarCount.textContent = String(total);

    renderizarGraficos(metricas);
    preencherTabelasAcessiveisGraficos(metricas);
    carregarPrecedentesRecentesOverview({ tema, juiz });
}

function descreverRecorte(recorte) {
    const orgaos = recorte?.orgaos_julgadores || [];
    const totalOrgaos = Number(recorte?.total_orgaos_julgadores || orgaos.length);
    const partes = [];
    if (totalOrgaos === 1 && orgaos[0]) {
        partes.push(orgaos[0]);
    } else if (totalOrgaos > 1) {
        partes.push(`${totalOrgaos} órgãos julgadores`);
    }
    const ini = recorte?.ano_inicial;
    const fim = recorte?.ano_final;
    if (ini && fim) partes.push(ini === fim ? `Julgados em ${ini}` : `Julgados de ${ini} a ${fim}`);
    return partes.join(" · ");
}

function atualizarRecorteAcervo(recorte, total, apiLoaded = true) {
    const descricao = descreverRecorte(recorte);
    const scopeNote = document.getElementById("jurimetria-scope-note");
    const originMeta = document.getElementById("scope-origin-meta");
    const footerNote = document.getElementById("footer-acervo-note");

    let textoPainel;
    if (!apiLoaded) {
        textoPainel = "Recorte indisponível sem conexão com o servidor";
    } else if (total === 0) {
        textoPainel = "Seu acervo ainda não tem decisões";
    } else {
        textoPainel = descricao || `${total} ${total === 1 ? "decisão" : "decisões"} no acervo`;
    }
    if (scopeNote) scopeNote.textContent = textoPainel;
    if (originMeta) originMeta.textContent = total > 0 && descricao ? `· ${descricao}` : "";
    if (footerNote) footerNote.textContent = total > 0 && descricao ? `Acervo pessoal · ${descricao}` : "Acervo pessoal";
}

function escapeHtml(value) {
    const entities = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return String(value ?? "").replace(/[&<>"']/g, (character) => entities[character]);
}

function aplicarFiltroPesquisaENavegar({ tema = "", juiz = "" }) {
    const selectTema = document.getElementById("filtro-tema");
    const selectJuiz = document.getElementById("filtro-juiz");

    if (tema && selectTema) {
        const exists = Array.from(selectTema.options).some((opt) => opt.value === tema);
        if (!exists) {
            const opt = document.createElement("option");
            opt.value = tema;
            opt.textContent = tema;
            selectTema.appendChild(opt);
        }
        selectTema.value = tema;
        if (selectJuiz) selectJuiz.value = "";
        switchTab("historico");
        showToast(`Exibindo decisões do assunto: ${tema}`);
        return;
    }

    if (juiz && selectJuiz) {
        const cleaned = juiz.replace(/^Dra?\.\s*/i, "");
        const exactOption = Array.from(selectJuiz.options).find(
            (opt) => opt.value === juiz || opt.value === cleaned
        );
        if (exactOption) {
            selectJuiz.value = exactOption.value;
        } else {
            const opt = document.createElement("option");
            opt.value = juiz;
            opt.textContent = juiz;
            selectJuiz.appendChild(opt);
            selectJuiz.value = juiz;
        }
        if (selectTema) selectTema.value = "";
        switchTab("historico");
        showToast(`Exibindo decisões filtradas por: ${juiz}`);
    }
}

function obterDistribuicaoResultados(metricas) {
    const dist = metricas?.distribuicao_resultados;
    if (
        dist &&
        (dist.procedentes || dist.acordos || dist.improcedentes || dist.em_analise)
    ) {
        return {
            procedentes: Number(dist.procedentes || 0),
            acordos: Number(dist.acordos || 0),
            improcedentes: Number(dist.improcedentes || 0),
            em_analise: Number(dist.em_analise || 0),
        };
    }

    const totalFav = (metricas?.decisoes_por_juiz || []).reduce(
        (acc, d) => acc + Number(d.procedentes || 0),
        0
    );
    const totalImpr = (metricas?.decisoes_por_juiz || []).reduce(
        (acc, d) => acc + Number(d.improcedentes || 0),
        0
    );
    return {
        procedentes: totalFav,
        acordos: 0,
        improcedentes: totalImpr,
        em_analise: 0,
    };
}

function normalizarTemasMetricas(metricas) {
    const totalGlobal = Math.max(Number(metricas?.total_processos_analisados || 0), 1);
    const taxaFallback = Number((Number(metricas?.taxa_exito_global || 0) * 100).toFixed(1));
    const prazoFallback = Number(metricas?.tempo_medio_tramitacao_meses || 12);

    return (metricas?.volume_por_tema || []).map((t) => {
        const totalTema =
            typeof t.total === "number" && t.total > 0
                ? t.total
                : Math.max(1, Math.round((Number(t.percentual || 0) / 100) * totalGlobal));
        return {
            tema: t.tema,
            percentual: Number(t.percentual || 0),
            total: totalTema,
            favoraveis: typeof t.favoraveis === "number" ? t.favoraveis : Math.round((taxaFallback / 100) * totalTema),
            taxa_favoravel: typeof t.taxa_favoravel === "number" ? Number(t.taxa_favoravel) : taxaFallback,
            tempo_medio_meses: typeof t.tempo_medio_meses === "number" ? Number(t.tempo_medio_meses) : prazoFallback,
        };
    });
}

function renderizarGraficos(metricas) {
    if (!metricas) return;

    const dist = obterDistribuicaoResultados(metricas);
    const totalResultados = Math.max(
        dist.procedentes + dist.acordos + dist.improcedentes + dist.em_analise,
        0
    );

    const itensRosca = [
        { label: "Procedentes", count: dist.procedentes, color: "#185A43" },
        { label: "Acordos", count: dist.acordos, color: "#2B598A" },
        { label: "Improcedentes", count: dist.improcedentes, color: "#C2555E" },
    ];
    if (dist.em_analise > 0) {
        itensRosca.push({ label: "Em análise", count: dist.em_analise, color: "#94A3B8" });
    }

    const legendContainer = document.getElementById("resultados-legend-list");
    if (legendContainer) {
        if (totalResultados === 0) {
            legendContainer.innerHTML = `<p class="donut-empty-note">${
                state.dashboardFiltroTema || state.dashboardFiltroJuiz
                    ? "Nenhum julgado encontrado para os filtros aplicados."
                    : "Nenhum julgado no acervo ainda."
            }</p>`;
        } else {
            legendContainer.innerHTML = itensRosca
                .map((item) => {
                    const pct = ((item.count / totalResultados) * 100).toFixed(1);
                    return `
                    <div class="donut-legend-row">
                        <span class="donut-legend-label">
                            <span class="donut-swatch" style="background-color: ${item.color};" aria-hidden="true"></span>
                            <span>${escapeHtml(item.label)}</span>
                        </span>
                        <span class="donut-legend-values tabular-nums">
                            <strong>${item.count}</strong>
                            <span class="donut-legend-pct">(${pct}%)</span>
                        </span>
                    </div>`;
                })
                .join("");
        }
    }

    if (typeof window.Chart === "undefined") return;

    const prefersReducedMotion =
        window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false;
    const v1Tooltip = {
        backgroundColor: "#142233",
        titleColor: "#FFFFFF",
        bodyColor: "#FFFFFF",
        cornerRadius: 6,
        padding: 10,
        titleFont: { family: "Source Sans 3", size: 12.5, weight: "600" },
        bodyFont: { family: "Source Sans 3", size: 12 },
    };

    const canvasResultados = document.getElementById("chartResultados");
    if (canvasResultados) {
        if (state.chartResultadosInstance) state.chartResultadosInstance.destroy();
        const centerTotalPlugin = {
            id: "centerTotalPlugin",
            afterDraw(chart) {
                const { ctx, chartArea } = chart;
                if (!chartArea) return;
                const centerX = (chartArea.left + chartArea.right) / 2;
                const centerY = (chartArea.top + chartArea.bottom) / 2;
                ctx.save();
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillStyle = "#142233";
                ctx.font = '600 26px "Lora", Georgia, serif';
                ctx.fillText(String(totalResultados), centerX, centerY - 8);
                ctx.fillStyle = "#4B5B6E";
                ctx.font = '500 12px "Source Sans 3", sans-serif';
                ctx.fillText(totalResultados === 1 ? "julgado" : "julgados", centerX, centerY + 14);
                ctx.restore();
            },
        };

        const roscaVazia = totalResultados === 0;
        state.chartResultadosInstance = new window.Chart(canvasResultados, {
            type: "doughnut",
            data: {
                labels: roscaVazia ? ["Sem dados"] : itensRosca.map((i) => i.label),
                datasets: [
                    {
                        data: roscaVazia ? [1] : itensRosca.map((i) => i.count),
                        backgroundColor: roscaVazia ? ["#E2E8F0"] : itensRosca.map((i) => i.color),
                        borderColor: "#FFFFFF",
                        borderWidth: 2,
                        hoverOffset: roscaVazia ? 0 : 4,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "66%",
                animation: prefersReducedMotion ? false : { duration: 380 },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        ...v1Tooltip,
                        enabled: !roscaVazia,
                        callbacks: {
                            label(ctx) {
                                const val = Number(ctx.raw || 0);
                                const pct = totalResultados ? ((val / totalResultados) * 100).toFixed(1) : "0.0";
                                return `${ctx.label}: ${val} julgados (${pct}%)`;
                            },
                        },
                    },
                },
            },
            plugins: [centerTotalPlugin],
        });
    }

    const canvasJuizes = document.getElementById("chartJuizes");
    if (canvasJuizes) {
        if (state.chartJuizesInstance) state.chartJuizesInstance.destroy();
        const juizesLista = metricas.decisoes_por_juiz || [];
        const isPct = state.juizChartMode === "pct";

        const dadosFav = juizesLista.map((d) => {
            if (!isPct) return d.procedentes;
            const tot = Math.max(d.procedentes + d.improcedentes, 1);
            return Math.round((d.procedentes / tot) * 100);
        });
        const dadosImpr = juizesLista.map((d) => {
            if (!isPct) return d.improcedentes;
            const tot = Math.max(d.procedentes + d.improcedentes, 1);
            return 100 - Math.round((d.procedentes / tot) * 100);
        });

        state.chartJuizesInstance = new window.Chart(canvasJuizes, {
            type: "bar",
            data: {
                labels: juizesLista.map((d) => d.juiz),
                datasets: [
                    {
                        label: isPct ? "Favoráveis (%)" : "Favoráveis (Procedentes / Acordos)",
                        data: dadosFav,
                        backgroundColor: isPct ? "#185A43" : "#20364A",
                        borderRadius: 4,
                        barThickness: 22,
                    },
                    {
                        label: isPct ? "Improcedentes (%)" : "Improcedentes",
                        data: dadosImpr,
                        backgroundColor: isPct ? "#D7DFE8" : "#CBD5E1",
                        borderRadius: 4,
                        barThickness: 22,
                    },
                ],
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                animation: prefersReducedMotion ? false : { duration: 380 },
                onHover(event, elements) {
                    if (event?.native?.target) {
                        event.native.target.style.cursor = elements.length ? "pointer" : "default";
                    }
                },
                onClick(_event, elements) {
                    if (!elements.length) return;
                    const idx = elements[0].index;
                    const juizSelecionado = juizesLista[idx]?.juiz;
                    if (juizSelecionado) aplicarFiltroPesquisaENavegar({ juiz: juizSelecionado });
                },
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            boxWidth: 10,
                            boxHeight: 10,
                            color: "#4B5B6E",
                            font: { size: 12, family: "Source Sans 3" },
                        },
                    },
                    tooltip: {
                        ...v1Tooltip,
                        callbacks: {
                            title(items) {
                                return items[0]?.label || "";
                            },
                            label(ctx) {
                                const d = juizesLista[ctx.dataIndex];
                                if (!d) return "";
                                const totalJ = Math.max(d.procedentes + d.improcedentes, 1);
                                const favPct = Math.round((d.procedentes / totalJ) * 100);
                                if (ctx.datasetIndex === 0) {
                                    return `Favoráveis: ${d.procedentes} de ${totalJ} julgados (${favPct}%) · clique para ver`;
                                }
                                return `Improcedentes: ${d.improcedentes} de ${totalJ} julgados (${100 - favPct}%) · clique para ver`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        stacked: true,
                        beginAtZero: true,
                        max: isPct ? 100 : undefined,
                        border: { display: false },
                        grid: { color: "#E6ECF2" },
                        ticks: {
                            stepSize: isPct ? 25 : 1,
                            color: "#4B5B6E",
                            font: { size: 11, family: "IBM Plex Mono" },
                            callback(val) {
                                return isPct ? `${val}%` : val;
                            },
                        },
                        title: {
                            display: true,
                            text: isPct ? "Proporção (%)" : "Nº de decisões",
                            color: "#4B5B6E",
                            font: { size: 11.5, family: "Source Sans 3" },
                        },
                    },
                    y: {
                        stacked: true,
                        grid: { display: false },
                        border: { display: false },
                        ticks: {
                            color: "#142233",
                            font: { size: 12, family: "Source Sans 3", weight: "600" },
                        },
                    },
                },
            },
        });
    }

    const canvasTemas = document.getElementById("chartTemas");
    if (canvasTemas) {
        if (state.chartTemasInstance) state.chartTemasInstance.destroy();
        const temasLista = normalizarTemasMetricas(metricas);
        const isTaxa = state.temaChartMode === "taxa";

        state.chartTemasInstance = new window.Chart(canvasTemas, {
            type: "bar",
            data: {
                labels: temasLista.map((t) => t.tema),
                datasets: [
                    {
                        label: isTaxa ? "Taxa favorável (%)" : "Julgados no acervo",
                        data: temasLista.map((t) => (isTaxa ? t.taxa_favoravel : t.total)),
                        backgroundColor: isTaxa ? "#185A43" : "#20364A",
                        borderRadius: 4,
                        barThickness: 20,
                    },
                ],
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                animation: prefersReducedMotion ? false : { duration: 380 },
                onHover(event, elements) {
                    if (event?.native?.target) {
                        event.native.target.style.cursor = elements.length ? "pointer" : "default";
                    }
                },
                onClick(_event, elements) {
                    if (!elements.length) return;
                    const idx = elements[0].index;
                    const temaSelecionado = temasLista[idx]?.tema;
                    if (temaSelecionado) aplicarFiltroPesquisaENavegar({ tema: temaSelecionado });
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        ...v1Tooltip,
                        callbacks: {
                            label(ctx) {
                                const t = temasLista[ctx.dataIndex];
                                if (!t) return "";
                                return `${t.total} julgados (${t.percentual}% do acervo) · ${t.taxa_favoravel}% favoráveis · prazo médio ~${t.tempo_medio_meses} meses`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        max: isTaxa ? 100 : undefined,
                        border: { display: false },
                        grid: { color: "#E6ECF2" },
                        ticks: {
                            stepSize: isTaxa ? 25 : 1,
                            color: "#4B5B6E",
                            font: { size: 11, family: "IBM Plex Mono" },
                            callback(val) {
                                return isTaxa ? `${val}%` : val;
                            },
                        },
                        title: {
                            display: true,
                            text: isTaxa ? "Taxa favorável (%)" : "Quantidade de julgados",
                            color: "#4B5B6E",
                            font: { size: 11.5, family: "Source Sans 3" },
                        },
                    },
                    y: {
                        grid: { display: false },
                        border: { display: false },
                        ticks: {
                            color: "#142233",
                            font: { size: 12, family: "Source Sans 3", weight: "600" },
                        },
                    },
                },
            },
        });
    }
}

function alternarModoGraficoJuizes(modo) {
    state.juizChartMode = modo;
    const btnQtd = document.getElementById("btn-juiz-mode-qtd");
    const btnPct = document.getElementById("btn-juiz-mode-pct");
    const isPct = modo === "pct";

    btnQtd?.classList.toggle("active", !isPct);
    btnQtd?.setAttribute("aria-pressed", String(!isPct));
    btnPct?.classList.toggle("active", isPct);
    btnPct?.setAttribute("aria-pressed", String(isPct));

    if (state.lastDashboardMetricas) {
        renderizarGraficos(state.lastDashboardMetricas);
    }
}

function alternarModoGraficoTemas(modo) {
    state.temaChartMode = modo;
    const btnVol = document.getElementById("btn-tema-mode-vol");
    const btnTaxa = document.getElementById("btn-tema-mode-taxa");
    const isTaxa = modo === "taxa";

    btnVol?.classList.toggle("active", !isTaxa);
    btnVol?.setAttribute("aria-pressed", String(!isTaxa));
    btnTaxa?.classList.toggle("active", isTaxa);
    btnTaxa?.setAttribute("aria-pressed", String(isTaxa));

    if (state.lastDashboardMetricas) {
        renderizarGraficos(state.lastDashboardMetricas);
    }
}

function preencherTabelasAcessiveisGraficos(metricas) {
    const tbodyResultados = document.getElementById("a11y-table-resultados");
    if (tbodyResultados) {
        const dist = obterDistribuicaoResultados(metricas);
        const total = Math.max(
            dist.procedentes + dist.acordos + dist.improcedentes + dist.em_analise,
            1
        );
        const linhas = [
            { label: "Procedentes", count: dist.procedentes },
            { label: "Acordos", count: dist.acordos },
            { label: "Improcedentes", count: dist.improcedentes },
        ];
        if (dist.em_analise > 0) {
            linhas.push({ label: "Em análise", count: dist.em_analise });
        }
        tbodyResultados.innerHTML = linhas
            .map(
                (item) => `
            <tr>
                <td>${escapeHtml(item.label)}</td>
                <td class="tabular-nums">${item.count}</td>
                <td class="tabular-nums">${((item.count / total) * 100).toFixed(1)}%</td>
            </tr>`
            )
            .join("");
    }

    const tbodyJuizes = document.getElementById("a11y-table-juizes");
    if (tbodyJuizes) {
        tbodyJuizes.innerHTML = (metricas.decisoes_por_juiz || [])
            .map(
                (item) => `
            <tr>
                <td>${escapeHtml(item.juiz)}</td>
                <td class="tabular-nums">${item.procedentes}</td>
                <td class="tabular-nums">${item.improcedentes}</td>
            </tr>`
            )
            .join("");
    }

    const tbodyTemas = document.getElementById("a11y-table-temas");
    if (tbodyTemas) {
        const temasLista = normalizarTemasMetricas(metricas);
        tbodyTemas.innerHTML = temasLista
            .map(
                (item) => `
            <tr>
                <td>${escapeHtml(item.tema)}</td>
                <td class="tabular-nums">${item.total}</td>
                <td class="tabular-nums">${item.percentual}%</td>
                <td class="tabular-nums">${item.taxa_favoravel}%</td>
                <td class="tabular-nums">${item.tempo_medio_meses} meses</td>
            </tr>`
            )
            .join("");
    }
}

async function carregarPrecedentesRecentesOverview({ tema = "", juiz = "" } = {}) {
    const tbody = document.getElementById("overview-recent-tbody");
    if (!tbody) return;

    let lista = { itens: [] };
    try {
        lista = await fetchProcessos({ tema, juiz, pagina: 1, limite: 5 });
    } catch {
        // Sem dados locais fictícios caso a API não responda
    }

    const itens = lista.itens || [];
    if (itens.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="table-empty-cell">
                    Nenhuma decisão registrada ainda para este recorte.
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = itens
        .map((item) => {
            const resLower = (item.resultado || "").toLowerCase();
            const badgeClass =
                resLower === "improcedente" ? "badge-unfavorable" : "badge-favorable";

            return `
            <tr>
                <td class="table-proc-cnj">${escapeHtml(item.numero_processo)}</td>
                <td class="table-proc-subject">${escapeHtml(item.tema)}</td>
                <td>${escapeHtml(item.magistrado)}</td>
                <td class="table-proc-parties">${escapeHtml(item.partes_anonimizadas)}</td>
                <td>
                    <span class="badge-editorial ${badgeClass}">${escapeHtml(item.resultado)}</span>
                </td>
                <td class="table-actions-cell">
                    <button type="button" class="btn btn-secondary btn-sm btn-open-dossier-overview" data-proc-id="${escapeHtml(item.id_processo)}">
                        Ler decisão
                    </button>
                </td>
            </tr>`;
        })
        .join("");

    tbody.querySelectorAll(".btn-open-dossier-overview").forEach((btn) => {
        btn.addEventListener("click", () => {
            const idProc = btn.getAttribute("data-proc-id");
            if (idProc) abrirDrawerProcesso(idProc);
        });
    });
}

/* ==========================================================================
   4. Pesquisa Jurisprudencial, Cartões Documentais e Filtros (Seções 9, 10, 11)
   ========================================================================== */
function renderizarChipsFiltrosAtivos() {
    const bar = document.getElementById("active-filters-bar");
    const container = document.getElementById("dynamic-filter-chips");
    if (!container) return;

    const busca = document.getElementById("filtro-busca")?.value.trim() || "";
    const tema = document.getElementById("filtro-tema")?.value || "";
    const juiz = document.getElementById("filtro-juiz")?.value || "";
    const colecao = document.getElementById("filtro-colecao")?.value || "todos";

    const chips = [];
    if (busca) {
        chips.push(
            `<button type="button" class="filter-chip" data-clear-field="filtro-busca">Termo: "${busca}" ×</button>`
        );
    }
    if (tema) {
        chips.push(
            `<button type="button" class="filter-chip" data-clear-field="filtro-tema">Assunto: ${tema} ×</button>`
        );
    }
    if (juiz) {
        chips.push(
            `<button type="button" class="filter-chip" data-clear-field="filtro-juiz">Magistrado(a): ${juiz} ×</button>`
        );
    }
    if (colecao === "salvos") {
        chips.push(
            `<button type="button" class="filter-chip" data-clear-field="filtro-colecao">Apenas decisões salvas ×</button>`
        );
    }

    container.innerHTML = chips.join("");
    if (bar) {
        bar.classList.toggle("hidden", chips.length === 0);
    }

    container.querySelectorAll("[data-clear-field]").forEach((btn) => {
        btn.addEventListener("click", () => {
            const fieldId = btn.getAttribute("data-clear-field");
            const el = document.getElementById(fieldId);
            if (el) {
                el.value = fieldId === "filtro-colecao" ? "todos" : "";
                carregarBaseConhecimento(1);
            }
        });
    });
}

function popularSelectOpcoes(selectEl, defaultLabel, items, normalizeMatch = false) {
    if (!selectEl || !Array.isArray(items)) return;
    const atual = selectEl.value;
    selectEl.innerHTML = `<option value="">${escapeHtml(defaultLabel)}</option>`;
    items.forEach((val) => {
        const opt = document.createElement("option");
        opt.value = val;
        opt.textContent = val;
        selectEl.appendChild(opt);
    });
    if (atual) {
        const match = Array.from(selectEl.options).find((opt) =>
            normalizeMatch
                ? opt.value === atual || opt.value.replace(/^Dra?\.\s*/i, "") === atual
                : opt.value === atual
        );
        if (match) selectEl.value = match.value;
    }
}

export async function carregarFiltrosDinamicos() {
    try {
        const filtros = await fetchFiltrosProcessos();
        popularSelectOpcoes(document.getElementById("filtro-tema"), "Todos os assuntos", filtros.temas);
        popularSelectOpcoes(document.getElementById("dash-filtro-tema"), "Todos os assuntos", filtros.temas);
        popularSelectOpcoes(document.getElementById("filtro-juiz"), "Todos os magistrados", filtros.magistrados, true);
        popularSelectOpcoes(document.getElementById("dash-filtro-juiz"), "Todos os magistrados", filtros.magistrados, true);
    } catch {
        // Fallback silencioso mantendo as opções iniciais do HTML
    }
}

export async function carregarBaseConhecimento(novaPagina = null) {
    if (novaPagina !== null) {
        state.paginaAtual = novaPagina;
    }

    const busca = document.getElementById("filtro-busca")?.value.trim() || "";
    const tema = document.getElementById("filtro-tema")?.value || "";
    const juiz = document.getElementById("filtro-juiz")?.value || "";
    const ordenacao = document.getElementById("filtro-ordenacao")?.value || "recentes";
    const colecao = document.getElementById("filtro-colecao")?.value || "todos";
    const ids = colecao === "salvos" ? Array.from(state.savedDecisions).join(",") : null;

    renderizarChipsFiltrosAtivos();

    const cardsContainer = document.getElementById("decisions-cards-container");
    cardsContainer?.classList.add("is-refreshing");

    let lista = {
        total: 0,
        pagina: 1,
        itens: [],
    };
    let apiLoaded = false;

    if (colecao === "salvos" && state.savedDecisions.size === 0) {
        apiLoaded = state.apiOnline;
        state.lastApiLoaded = apiLoaded;
        cardsContainer?.classList.remove("is-refreshing");
    } else {
        try {
            lista = await fetchProcessos({
                tema,
                juiz,
                busca,
                ordenacao,
                ids,
                pagina: state.paginaAtual,
                limite: state.limitePorPagina,
            });
            apiLoaded = true;
            state.apiOnline = true;
            state.lastApiLoaded = true;
        } catch {
            state.lastApiLoaded = false;
        } finally {
            cardsContainer?.classList.remove("is-refreshing");
        }
    }

    const itens = Array.isArray(lista.itens) ? [...lista.itens] : [];
    state.lastLoadedItems = itens;
    state.totalProcessosLista = Number(lista.total ?? itens.length ?? 0);

    const countLabel = document.getElementById("historico-total-label");
    if (countLabel) {
        const total = state.totalProcessosLista;
        countLabel.textContent = `${total} ${total === 1 ? "decisão encontrada" : "decisões encontradas"}`;
    }

    const hasActiveFilters = Boolean(busca || tema || juiz || colecao === "salvos");
    renderizarListaDecisoes(itens, { apiLoaded, hasActiveFilters, colecao });
    atualizarControlesPaginacao();
}

function renderizarListaDecisoes(itens, { apiLoaded = state.lastApiLoaded, hasActiveFilters = false, colecao = "todos" } = {}) {
    const cardsContainer = document.getElementById("decisions-cards-container");
    const tbody = document.getElementById("historico-tbody");

    if (!itens || itens.length === 0) {
        let emptyTitle = "Nenhuma decisão foi encontrada com esses critérios";
        let emptyText =
            "Remova um dos filtros ativos ou experimente pesquisar por outro assunto, magistrado ou expressão jurídica.";
        let actionsHtml = "";

        if (!apiLoaded && !(colecao === "salvos" && state.savedDecisions.size === 0)) {
            emptyTitle = "Não foi possível carregar o acervo no momento";
            emptyText =
                "Verifique se o servidor da plataforma está em execução e tente pesquisar novamente.";
        } else if (colecao === "salvos" && state.savedDecisions.size === 0) {
            emptyTitle = "Você ainda não marcou decisões nos favoritos";
            emptyText =
                "Clique em \"Salvar\" em qualquer decisão do acervo para montar sua coletânea pessoal.";
        } else if (!hasActiveFilters) {
            emptyTitle = "Seu acervo ainda está vazio";
            emptyText =
                "Comece sincronizando precedentes públicos do DataJud (CNJ), cadastrando um julgado manualmente ou analisando sua primeira petição em PDF.";
            actionsHtml = `
                <div class="empty-onboarding-actions">
                    <button type="button" id="btn-empty-sync-datajud" class="btn btn-primary btn-sm">Sincronizar DataJud (CNJ)</button>
                    <button type="button" id="btn-empty-new-julgado" class="btn btn-secondary btn-sm">Cadastrar julgado</button>
                    <button type="button" id="btn-empty-upload-pdf" class="btn btn-secondary btn-sm">Analisar petição PDF</button>
                </div>`;
        }

        const emptyHtml = `
            <div class="decisions-empty-state">
                <strong class="decisions-empty-title">
                    ${escapeHtml(emptyTitle)}
                </strong>
                <p class="decisions-empty-text">
                    ${escapeHtml(emptyText)}
                </p>
                ${actionsHtml}
            </div>`;
        if (cardsContainer) {
            cardsContainer.innerHTML = emptyHtml;
            document.getElementById("btn-empty-sync-datajud")?.addEventListener("click", () => {
                document.getElementById("btn-sincronizar-datajud")?.click();
            });
            document.getElementById("btn-empty-new-julgado")?.addEventListener("click", () => {
                document.getElementById("btn-novo-julgado")?.click();
            });
            document.getElementById("btn-empty-upload-pdf")?.addEventListener("click", () => {
                switchTab("upload");
                window.scrollTo({ top: 0, behavior: "smooth" });
            });
        }
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="table-empty-cell">
                        ${escapeHtml(emptyTitle)}. ${escapeHtml(emptyText)}
                    </td>
                </tr>`;
        }
        return;
    }

    if (cardsContainer) {
        cardsContainer.innerHTML = itens
            .map((item) => {
                const resLower = (item.resultado || "").toLowerCase();
                const badgeClass =
                    resLower === "improcedente" ? "badge-unfavorable" : "badge-favorable";
                const isSaved = state.savedDecisions.has(item.id_processo);
                const dataJulg = formatarDataJulgamento(item.data_julgamento);
                const comarca = item.comarca || "Acervo Judicial";
                const sintese =
                    item.resumo_curto ||
                    `Decisão judicial proferida nos autos do processo nº ${item.numero_processo} sob relatoria/juízo de ${item.magistrado} (${comarca}), envolvendo ${item.partes_anonimizadas}.`;

                return `
                <article class="decision-card" data-card-proc-id="${escapeHtml(item.id_processo)}">
                    <div class="decision-card-top">
                        <div class="decision-meta-line">
                            <span>TJAL · ${escapeHtml(comarca)}</span>
                            <span aria-hidden="true">·</span>
                            <span class="decision-cnj">${escapeHtml(item.numero_processo)}</span>
                            <span aria-hidden="true">·</span>
                            <span>${escapeHtml(item.magistrado)}</span>
                            <span aria-hidden="true">·</span>
                            <span>${dataJulg}</span>
                        </div>

                        <div class="decision-badges">
                            ${
                                isSaved
                                    ? `<span class="badge-editorial badge-saved">Salva</span>`
                                    : ""
                            }
                            <span class="badge-editorial ${badgeClass}">
                                ${escapeHtml(item.resultado)}
                            </span>
                        </div>
                    </div>

                    <div class="decision-card-body">
                        <h3 class="decision-subject-title">${escapeHtml(item.tema)}</h3>

                        <p class="decision-excerpt">
                            ${escapeHtml(sintese)}
                        </p>
                        <p class="decision-parties">
                            Partes: ${escapeHtml(item.partes_anonimizadas)}
                        </p>
                    </div>

                    <div class="decision-card-footer">
                        <button type="button" class="btn-read-decision btn-inspecionar-proc" data-inspect-id="${escapeHtml(item.id_processo)}">
                            <span>Ler decisão</span>
                            <span class="arrow-glyph" aria-hidden="true">→</span>
                        </button>

                        <div class="decision-secondary-actions">
                            <button type="button" class="btn-text-action btn-salvar-proc${isSaved ? " is-saved" : ""}" data-save-id="${escapeHtml(item.id_processo)}">
                                ${isSaved ? "Salva ✓" : "Salvar"}
                            </button>
                            <button type="button" class="btn-text-action btn-copiar-ref" data-ref-id="${escapeHtml(item.id_processo)}">
                                Copiar referência
                            </button>
                            <button type="button" class="btn-text-action btn-text-muted btn-exportar-pdf" data-pdf-id="${escapeHtml(item.id_processo)}">
                                Exportar PDF
                            </button>
                        </div>
                    </div>
                </article>`;
            })
            .join("");
    }

    if (tbody) {
        tbody.innerHTML = itens
            .map((item) => {
                const resLower = (item.resultado || "").toLowerCase();
                const badgeClass =
                    resLower === "improcedente" ? "badge-unfavorable" : "badge-favorable";
                const dataJulg = formatarDataJulgamento(item.data_julgamento);

                return `
                <tr data-row-proc-id="${escapeHtml(item.id_processo)}">
                    <td>
                        <div class="table-proc-cnj">${escapeHtml(item.numero_processo)}</div>
                        <div class="table-proc-date">${dataJulg}</div>
                    </td>
                    <td class="table-proc-subject">${escapeHtml(item.tema)}</td>
                    <td>
                        <div>${escapeHtml(item.magistrado)}</div>
                        <div class="table-proc-court">${escapeHtml(item.comarca || "TJAL")}</div>
                    </td>
                    <td>
                        <span>${escapeHtml(item.partes_anonimizadas)}</span>
                    </td>
                    <td>
                        <span class="badge-editorial ${badgeClass}">${escapeHtml(item.resultado)}</span>
                    </td>
                    <td class="table-actions-cell">
                        <button type="button" data-inspect-id="${escapeHtml(item.id_processo)}" class="btn btn-read-decision btn-inspecionar-proc">
                            Abrir
                        </button>
                        <button type="button" data-pdf-id="${escapeHtml(item.id_processo)}" class="btn-text-action btn-text-muted btn-exportar-pdf">
                            PDF
                        </button>
                    </td>
                </tr>`;
            })
            .join("");
    }

    document.querySelectorAll(".btn-inspecionar-proc").forEach((btn) => {
        btn.addEventListener("click", () => {
            const idProc = btn.getAttribute("data-inspect-id");
            if (idProc) abrirDrawerProcesso(idProc);
        });
    });

    document.querySelectorAll(".btn-salvar-proc").forEach((btn) => {
        btn.addEventListener("click", () => {
            const idProc = btn.getAttribute("data-save-id");
            if (idProc) toggleSalvarDecisao(idProc);
        });
    });

    document.querySelectorAll(".btn-copiar-ref").forEach((btn) => {
        btn.addEventListener("click", () => {
            const idProc = btn.getAttribute("data-ref-id");
            const found = itens.find((i) => i.id_processo === idProc);
            if (found) copiarReferenciaDecisao(found);
        });
    });

    document.querySelectorAll(".btn-exportar-pdf").forEach((btn) => {
        btn.addEventListener("click", () => {
            const idProc = btn.getAttribute("data-pdf-id");
            if (idProc) exportarRelatorioPdfProcesso(idProc);
        });
    });
}

export function alternarVisaoResultados(modo) {
    state.resultsViewMode = modo;
    const btnCards = document.getElementById("btn-view-cards");
    const btnTable = document.getElementById("btn-view-table");
    const cardsBox = document.getElementById("decisions-cards-container");
    const tableBox = document.getElementById("decisions-table-container");

    if (modo === "cards") {
        btnCards?.classList.add("active");
        btnCards?.setAttribute("aria-pressed", "true");
        btnTable?.classList.remove("active");
        btnTable?.setAttribute("aria-pressed", "false");
        cardsBox?.classList.remove("hidden");
        tableBox?.classList.add("hidden");
    } else {
        btnTable?.classList.add("active");
        btnTable?.setAttribute("aria-pressed", "true");
        btnCards?.classList.remove("active");
        btnCards?.setAttribute("aria-pressed", "false");
        tableBox?.classList.remove("hidden");
        cardsBox?.classList.add("hidden");
    }
}

/* ==========================================================================
   5. Leitura Individual de Decisão Judicial (Seção 12)
   ========================================================================== */
async function abrirDrawerProcesso(idProcesso) {
    const drawer = document.getElementById("drawer-processo");
    if (!drawer) return;

    try {
        const det = await fetchProcessoDetalhes(idProcesso);
        exibirDrawerProcesso(det);
    } catch (err) {
        showToast(err.message);
    }
}

function exibirDrawerProcesso(det) {
    const drawer = document.getElementById("drawer-processo");
    state.drawerProcessId = det.id_processo;
    state.currentDrawerPayload = det;
    const meta = det.metadados_extraidos;
    const pred = det.analise_preditiva;

    document.getElementById("drawer-proc-id").textContent = det.id_processo;
    document.getElementById("drawer-proc-cnj").textContent = `Processo nº ${meta.numero_processo}`;
    document.getElementById("drawer-proc-tema").textContent = meta.tema;
    document.getElementById("drawer-proc-juiz").textContent = meta.magistrado;
    document.getElementById("drawer-proc-comarca").textContent = `TJAL · ${meta.comarca}`;
    document.getElementById("drawer-proc-autor").textContent = meta.partes_anonimizadas.autor;
    document.getElementById("drawer-proc-reu").textContent = meta.partes_anonimizadas.reu;
    const origemMetodo =
        pred.provedor_ia === "local_heuristic" || !pred.provedor_ia
            ? "estimativa heurística local"
            : `IA (${pred.provedor_ia})`;
    document.getElementById("drawer-proc-prob").textContent =
        `${Math.round(pred.probabilidade_deferimento * 100)}% em ${pred.casos_similares_encontrados ?? 0} decisões semelhantes (${origemMetodo})`;
    document.getElementById("drawer-proc-resumo").textContent = det.resumo_nlp;
    document.getElementById("drawer-proc-tese").textContent = pred.tese_recomendada;

    const saveBtn = document.getElementById("btn-drawer-save");
    if (saveBtn) {
        saveBtn.textContent = state.savedDecisions.has(det.id_processo)
            ? "Salva na biblioteca"
            : "Salvar decisão";
    }

    drawer.classList.remove("hidden");
    announceStatus(`Leitura da decisão aberta para o processo ${meta.numero_processo}.`);
}

function fecharDrawerProcesso() {
    document.getElementById("drawer-processo")?.classList.add("hidden");
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
   6. Análise Comparativa de Petição e Importação CSV (RF-02 a RF-06)
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

function atualizarEtapasPipeline(fase = "idle") {
    const tracker = document.getElementById("petition-pipeline-tracker");
    if (!tracker) return;

    const steps = tracker.querySelectorAll("[data-pipeline-step]");
    steps.forEach((el) => {
        const stepNum = Number(el.getAttribute("data-pipeline-step"));
        const statusEl = el.querySelector(".step-status-label");
        el.classList.remove("is-current", "is-done", "is-processing", "is-error");

        if (fase === "idle") {
            if (stepNum === 1) {
                el.classList.add("is-current");
                if (statusEl) statusEl.textContent = "Aguardando arquivo";
            } else if (statusEl) {
                statusEl.textContent = "Pendente";
            }
        } else if (fase === "processing") {
            if (stepNum === 1) {
                el.classList.add("is-done");
                if (statusEl) statusEl.textContent = "Recebido";
            } else if (stepNum >= 2 && stepNum <= 5) {
                el.classList.add("is-processing");
                if (statusEl) statusEl.textContent = "Em execução";
            } else if (statusEl) {
                statusEl.textContent = "Aguardando";
            }
        } else if (fase === "error") {
            if (stepNum === 1) {
                el.classList.add("is-done");
                if (statusEl) statusEl.textContent = "Recebido";
            } else if (stepNum === 2) {
                el.classList.add("is-error");
                if (statusEl) statusEl.textContent = "Interrompido";
            } else if (statusEl) {
                statusEl.textContent = "Pendente";
            }
        } else if (fase === "completed") {
            el.classList.add("is-done");
            if (stepNum === 6) {
                el.classList.add("is-current");
            }
            if (statusEl) statusEl.textContent = "Concluído";
        }
    });
}

export function resetarFluxoUpload() {
    document.getElementById("upload-selection-container")?.classList.remove("hidden");
    document.getElementById("loading-state")?.classList.add("hidden");
    document.getElementById("error-state")?.classList.add("hidden");
    document.getElementById("csv-result-state")?.classList.add("hidden");
    document.getElementById("result-state")?.classList.add("hidden");
    document.getElementById("result-empty-state")?.classList.remove("hidden");

    const inputPdf = document.getElementById("file-input-pdf");
    const inputCsv = document.getElementById("file-input-csv");
    if (inputPdf) inputPdf.value = "";
    if (inputCsv) inputCsv.value = "";

    atualizarEtapasPipeline("idle");
    announceStatus("Formulário de submissão de documentos pronto.");
}

function exibirErroUpload(mensagem) {
    document.getElementById("upload-selection-container")?.classList.add("hidden");
    document.getElementById("loading-state")?.classList.add("hidden");
    document.getElementById("csv-result-state")?.classList.add("hidden");

    const errBox = document.getElementById("error-state");
    const errMsg = document.getElementById("error-message-text");
    if (errMsg) errMsg.textContent = mensagem;
    errBox?.classList.remove("hidden");

    atualizarEtapasPipeline("error");
    announceStatus(`Não foi possível concluir a leitura: ${mensagem}`);
}

export async function processarArquivoPdf(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
        exibirErroUpload(
            "O arquivo selecionado não está em formato PDF. Selecione um documento com extensão .PDF para prosseguir."
        );
        return;
    }

    document.getElementById("upload-selection-container")?.classList.add("hidden");
    document.getElementById("error-state")?.classList.add("hidden");
    document.getElementById("loading-state")?.classList.remove("hidden");
    atualizarEtapasPipeline("processing");
    announceStatus("Examinando documento e aplicando proteção de dados pessoais...");

    try {
        const resultado = await uploadProcessoPdf(file);
        document.getElementById("loading-state")?.classList.add("hidden");
        document.getElementById("upload-selection-container")?.classList.remove("hidden");
        renderizarResultadoPredicaoPdf(resultado);
        showToast(
            `Estudo comparativo concluído para o processo ${resultado.metadados_extraidos.numero_processo}.`
        );
        carregarStatusPlano();
        carregarFiltrosDinamicos();
        carregarDashboard();
    } catch (err) {
        exibirErroUpload(err.message || "Não foi possível ler o arquivo PDF enviado.");
        if (err && (err.status === 402 || String(err.message || "").includes("LimitePlanoFree"))) {
            abrirModalUpgrade(err.message);
        }
    }
}

export async function processarArquivoCsv(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
        exibirErroUpload("Selecione uma planilha no formato .CSV para importar decisões em lote.");
        return;
    }

    document.getElementById("upload-selection-container")?.classList.add("hidden");
    document.getElementById("error-state")?.classList.add("hidden");
    document.getElementById("csv-result-state")?.classList.add("hidden");
    document.getElementById("loading-state")?.classList.remove("hidden");
    atualizarEtapasPipeline("processing");
    announceStatus("Processando planilha de decisões...");

    try {
        const resCsv = await uploadProcessosCsv(file);
        document.getElementById("loading-state")?.classList.add("hidden");
        const csvBox = document.getElementById("csv-result-state");
        csvBox?.classList.remove("hidden");

        document.getElementById("csv-res-arquivo").textContent = resCsv.arquivo_nome;
        document.getElementById("csv-res-lidos").textContent = String(resCsv.total_registros_lidos);
        document.getElementById("csv-res-importados").textContent = String(resCsv.total_importados_com_sucesso);
        document.getElementById("csv-res-lgpd").textContent = String(resCsv.total_entidades_anonimizadas_lgpd);

        atualizarEtapasPipeline("completed");
        showToast(`${resCsv.total_importados_com_sucesso} decisões adicionadas ao acervo.`);
        carregarStatusPlano();
        carregarFiltrosDinamicos();
        carregarDashboard();
    } catch (err) {
        exibirErroUpload(err.message || "Não foi possível importar a planilha CSV.");
        if (err && (err.status === 402 || String(err.message || "").includes("RecursoExclusivoPro"))) {
            abrirModalUpgrade(err.message);
        }
    }
}

export function renderizarResultadoPredicaoPdf(payload) {
    document.getElementById("result-empty-state")?.classList.add("hidden");
    const resultEl = document.getElementById("result-state");
    if (resultEl) {
        resultEl.classList.remove("hidden");
        resultEl.classList.remove("is-fresh");
        void resultEl.offsetWidth;
        resultEl.classList.add("is-fresh");
    }
    atualizarEtapasPipeline("completed");
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

    document.getElementById("res-id-processo").textContent = `Ref. ${payload.id_processo}`;
    document.getElementById("res-numero-cnj").textContent = meta.numero_processo;
    document.getElementById("res-probabilidade").textContent = `${probPct}%`;
    document.getElementById("res-margem").textContent = `±${margemPct}% na amostra`;
    document.getElementById("res-prazo").textContent = `${pred.tempo_estimado_sentenca_meses} meses`;
    document.getElementById("res-similares").textContent = `${pred.casos_similares_encontrados ?? 0} julgados`;
    document.getElementById("res-provedor-ia").textContent =
        pred.provedor_ia === "local_heuristic" || !pred.provedor_ia
            ? "Estimativa Heurística Local (Base TJAL)"
            : `Análise por IA (${pred.provedor_ia})`;

    document.getElementById("res-tema").textContent = meta.tema;
    document.getElementById("res-magistrado").textContent = meta.magistrado;
    document.getElementById("res-comarca").textContent = meta.comarca;
    document.getElementById("res-autor").textContent = meta.partes_anonimizadas.autor;
    document.getElementById("res-reu").textContent = meta.partes_anonimizadas.reu;

    const docsProtegidos = Number(lgpd.total_cpfs_mascarados || 0);
    const nomesProtegidos = Number(lgpd.total_nomes_mascarados || 0);
    document.getElementById("res-lgpd-badge").textContent =
        docsProtegidos + nomesProtegidos > 0
            ? `${docsProtegidos} doc(s) e ${nomesProtegidos} nome(s) protegidos`
            : "Dados pessoais protegidos";

    document.getElementById("res-resumo-nlp").textContent = payload.resumo_nlp;
    document.getElementById("res-tese-recomendada").textContent = pred.tese_recomendada;
    document.getElementById("res-tendencia-juiz").textContent = pred.tendencia_juiz;
    atualizarUIPlano();
}

/* ==========================================================================
   7. Exportação de Relatório Analítico em PDF (RF-09)
   ========================================================================== */
export function exportarRelatorioPdfProcesso(idProcesso = null) {
    const targetId = idProcesso || state.lastAnalyzedProcessId;
    if (!targetId) {
        showToast("Analise uma petição ou selecione uma decisão para exportar o relatório em PDF.");
        return;
    }
    const url = getRelatorioPdfUrl(targetId);
    showToast(`Preparando relatório analítico em PDF (${targetId})...`);
    window.open(url, "_blank", "noopener,noreferrer");
}

/* ==========================================================================
   8. Modais de Autenticação (RF-01) e Metodologia (Seção 21.3)
   ========================================================================== */

/* ==========================================================================
   Consulta Oficial ao DataJud (CNJ / TJAL) - EAP 1.4.2
   ========================================================================== */
function exibirResultadoDataJud(data) {
    const box = document.getElementById("datajud-result-box");
    if (!box) return;

    document.getElementById("dj-badge-tribunal").textContent = `CNJ · ${data.tribunal || "TJAL"}`;
    document.getElementById("dj-badge-fonte").textContent = data.fonte === "datajud_api"
        ? "API Pública DataJud (CNJ)"
        : "Base Local Homologada (TJAL)";
    document.getElementById("dj-numero-processo").textContent = `Processo nº ${data.numero_processo}`;
    document.getElementById("dj-classe").textContent = data.classe || "Procedimento Comum Cível";
    document.getElementById("dj-assunto").textContent = data.assunto_principal || "Dano Moral";
    document.getElementById("dj-orgao").textContent = data.orgao_julgador || "Não informado pelo DataJud";

    let dataFormatada = "Não informada";
    if (data.data_ajuizamento) {
        try {
            dataFormatada = new Date(data.data_ajuizamento).toLocaleDateString("pt-BR");
        } catch (_) {
            dataFormatada = String(data.data_ajuizamento);
        }
    }
    document.getElementById("dj-data").textContent = dataFormatada;

    const listUl = document.getElementById("dj-movimentacoes-list");
    listUl.innerHTML = "";
    if (data.movimentos_recentes && data.movimentos_recentes.length > 0) {
        data.movimentos_recentes.forEach(m => {
            const li = document.createElement("li");
            const dtStr = m.data_hora ? ` (${m.data_hora.substring(0, 10)})` : "";
            li.textContent = `${m.nome}${dtStr}`;
            listUl.appendChild(li);
        });
    } else {
        const li = document.createElement("li");
        li.textContent = "Nenhuma movimentação adicional indexada no tribunal.";
        listUl.appendChild(li);
    }

    document.getElementById("dj-mensagem-status").textContent = data.mensagem || "";
    box.classList.remove("hidden");
    box.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function dispararConsultaDataJud() {
    const inputBusca = document.getElementById("filtro-busca");
    const termo = (inputBusca?.value || "").trim();
    const numeroCnj = termo || "0710802-55.2018.8.02.0001";

    showToast("Consultando metadados na API Pública do DataJud (CNJ)...");
    announceStatus("Consultando processo no DataJud...");

    try {
        const data = await consultarProcessoDatajud(numeroCnj);
        exibirResultadoDataJud(data);
        showToast("Dados do DataJud recuperados com sucesso!");
    } catch (err) {
        showToast(`Consulta ao DataJud: ${err.message}`);
    }
}

async function dispararSincronizacaoDataJud() {
    const btnSync = document.getElementById("btn-sincronizar-datajud");
    const temaSelecionado = document.getElementById("filtro-tema")?.value || "";

    if (btnSync) btnSync.disabled = true;
    showToast("Coletando e sincronizando lote de jurisprudências do DataJud (CNJ)...");
    announceStatus("Sincronizando lote de jurisprudências do DataJud com a base histórica...");

    try {
        const res = await sincronizarLoteDatajud({
            tribunal: "TJAL",
            tema: temaSelecionado,
            limite: 3,
        });
        await carregarFiltrosDinamicos();
        await carregarBaseConhecimento(1);
        carregarDashboard();
        showToast(res.mensagem || "Base histórica atualizada com lote do DataJud (CNJ).");
        announceStatus(res.mensagem || "Sincronização do DataJud concluída.");
    } catch (err) {
        showToast(`Sincronização DataJud: ${err.message}`);
    } finally {
        if (btnSync) btnSync.disabled = false;
    }
}

/* ==========================================================================
   Intro da Marca: pilastras se afastam e formam "JuriVision"
   A decisão de exibir é tomada no <head> (classe jv-intro-on), antes do primeiro
   paint; aqui só tratamos o pulo e a saída (logotipo pousando no cabeçalho).
   ========================================================================== */
const INTRO_PAUSA_FINAL_MS = 320; // respiro com o nome completo antes de pousar no cabeçalho
const INTRO_LIMITE_MS = 4500; // salvaguarda caso a animação não reporte o fim
let introEncerrada = !document.documentElement.classList.contains("jv-intro-on");
let introConfigurada = false;

/** Com token salvo a decisão foi adiada: só depois de validar a sessão sabemos se cai na landing. */
function iniciarIntroAdiada(vaiParaLanding) {
    const html = document.documentElement;
    if (!html.classList.contains("jv-intro-adiada")) return;
    html.classList.remove("jv-intro-adiada");
    if (!vaiParaLanding || !window.__jvIntroElegivel) return;
    html.classList.add("jv-intro-on");
    window.__jvIntroInicio = performance.now();
    introEncerrada = false;
    configurarIntroMarca();
}

function obterLogoCabecalhoVisivel() {
    return (
        document.querySelector("#landing-view:not(.hidden) .lp-header .brand-logo-img") ||
        document.querySelector("#app-shell:not(.hidden) .site-header .brand-logo-img")
    );
}

function esperarMs(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function animarEntradaHero() {
    document.getElementById("landing-view")?.classList.add("lp-hero-animate");
}

function encerrarIntroMarca() {
    if (introEncerrada) return;
    introEncerrada = true;
    document.documentElement.classList.remove("jv-intro-on");
    document.getElementById("jv-intro")?.remove();
    try {
        window.sessionStorage.setItem("jv_intro_vista", "1");
    } catch {
        // armazenamento indisponível: a intro pode reaparecer na próxima visita
    }
}

function pularIntroMarca() {
    if (introEncerrada) return;
    encerrarIntroMarca();
    animarEntradaHero();
}

function configurarIntroMarca() {
    if (introEncerrada || introConfigurada) return;
    introConfigurada = true;
    const intro = document.getElementById("jv-intro");
    if (!intro) {
        encerrarIntroMarca();
        return;
    }
    document.getElementById("btn-jv-intro-pular")?.addEventListener("click", pularIntroMarca);
    intro.addEventListener("pointerdown", (event) => {
        if (event.target.closest?.("#btn-jv-intro-pular")) return;
        pularIntroMarca();
    });
    const pularPorInteracao = () => pularIntroMarca();
    window.addEventListener("keydown", pularPorInteracao, { once: true });
    window.addEventListener("wheel", pularPorInteracao, { once: true, passive: true });
    window.addEventListener("touchmove", pularPorInteracao, { once: true, passive: true });
}

async function concluirIntroMarca() {
    if (introEncerrada) {
        animarEntradaHero();
        return;
    }
    // Sincroniza com o fim real da última letra (o "J"), não com um relógio fixo:
    // em conexões lentas a animação só começa quando o CSS termina de carregar.
    const ultimaLetra = document.querySelector('#jv-intro .jv-letter[style*="--ring:3"]');
    const animacao = ultimaLetra?.getAnimations?.()[0];
    const decorrido = performance.now() - (window.__jvIntroInicio ?? performance.now());
    await Promise.race([
        animacao ? animacao.finished.catch(() => {}) : esperarMs(2100),
        esperarMs(Math.max(0, INTRO_LIMITE_MS - decorrido)),
    ]);
    await esperarMs(INTRO_PAUSA_FINAL_MS);
    if (introEncerrada) return;
    window.scrollTo({ top: 0, behavior: "auto" });

    const intro = document.getElementById("jv-intro");
    const logo = intro?.querySelector(".jv-intro-logo");
    const alvo = obterLogoCabecalhoVisivel();
    if (!intro || !logo || !alvo) {
        pularIntroMarca();
        return;
    }

    // FLIP: mede origem e destino (mesmo viewBox 433×123) e desloca/escala o logotipo
    const de = logo.getBoundingClientRect();
    const para = alvo.getBoundingClientRect();
    intro.classList.add("is-leaving");
    logo.style.transformOrigin = "0 0";
    void logo.getBoundingClientRect();
    logo.style.transform =
        `translate(${para.left - de.left}px, ${para.top - de.top}px) scale(${para.width / de.width})`;
    if (state.viewMode === "landing") animarEntradaHero();
    await esperarMs(680);
    encerrarIntroMarca();
}

function mostrarLanding() {
    state.viewMode = "landing";
    document.getElementById("landing-view")?.classList.remove("hidden");
    document.getElementById("app-shell")?.classList.add("hidden");
    window.scrollTo({ top: 0, behavior: "auto" });
}

function mostrarWorkspace(tabId = state.selectedLandingGoal || "historico") {
    // ?intro=1 deixa a intro terminar mesmo para quem já está logado (demonstração)
    if (!window.__jvIntroForcada) encerrarIntroMarca();
    state.viewMode = "workspace";
    document.getElementById("landing-view")?.classList.add("hidden");
    document.getElementById("app-shell")?.classList.remove("hidden");
    carregarFiltrosDinamicos();
    switchTab(tabId);
    if (tabId !== "dashboard") {
        carregarDashboard();
    }
    window.scrollTo({ top: 0, behavior: "auto" });
}

function configurarLandingPage() {
    const landingView = document.getElementById("landing-view");
    if (!landingView) return;

    const goalLabels = {
        historico: "Pesquisar precedentes e DataJud (CNJ)",
        dashboard: "Analisar perfil de magistrados",
        upload: "Confrontar petição em PDF",
    };

    const goalButtons = landingView.querySelectorAll("[data-lp-goal]");
    const goalSelectedLabel = document.getElementById("lp-goal-selected-label");

    goalButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            const goal = btn.getAttribute("data-lp-goal") || "historico";
            state.selectedLandingGoal = goal;
            goalButtons.forEach((item) => {
                const isSelected = item === btn;
                item.classList.toggle("is-selected", isSelected);
                item.setAttribute("aria-pressed", isSelected ? "true" : "false");
            });
            if (goalSelectedLabel) {
                goalSelectedLabel.textContent = goalLabels[goal] || goalLabels.historico;
            }
        });
    });

    const demoTabs = Array.from(landingView.querySelectorAll("[data-lp-demo]"));
    const demoPanels = landingView.querySelectorAll("[data-lp-demo-panel]");

    function selectDemoTab(demoKey, moveFocus = false) {
        demoTabs.forEach((tab) => {
            const isSelected = tab.getAttribute("data-lp-demo") === demoKey;
            tab.classList.toggle("active", isSelected);
            tab.setAttribute("aria-selected", isSelected ? "true" : "false");
            if (isSelected && moveFocus) tab.focus();
        });
        demoPanels.forEach((panel) => {
            const isMatch = panel.getAttribute("data-lp-demo-panel") === demoKey;
            panel.classList.toggle("active", isMatch);
            panel.hidden = !isMatch;
        });
    }

    demoTabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            const demoKey = tab.getAttribute("data-lp-demo");
            if (demoKey) selectDemoTab(demoKey);
        });
        tab.addEventListener("keydown", (event) => {
            const currentIndex = demoTabs.indexOf(tab);
            if (currentIndex === -1) return;
            if (event.key === "ArrowRight") {
                event.preventDefault();
                const next = demoTabs[(currentIndex + 1) % demoTabs.length];
                selectDemoTab(next.getAttribute("data-lp-demo"), true);
            } else if (event.key === "ArrowLeft") {
                event.preventDefault();
                const prev = demoTabs[(currentIndex - 1 + demoTabs.length) % demoTabs.length];
                selectDemoTab(prev.getAttribute("data-lp-demo"), true);
            }
        });
    });

    document.getElementById("btn-lp-login")?.addEventListener("click", () => {
        abrirContaModal?.(false);
    });

    const handleRegisterOrEnter = (targetTab = null) => {
        if (targetTab) state.selectedLandingGoal = targetTab;
        if (state.currentUser?.authenticated) {
            mostrarWorkspace(state.selectedLandingGoal || "historico");
            return;
        }
        abrirContaModal?.(true);
    };

    document.getElementById("btn-lp-register")?.addEventListener("click", () => handleRegisterOrEnter());
    document.getElementById("btn-lp-hero-register")?.addEventListener("click", () => handleRegisterOrEnter());
    document.getElementById("btn-lp-goal-register")?.addEventListener("click", () => {
        handleRegisterOrEnter(state.selectedLandingGoal);
    });
    document.getElementById("btn-lp-plan-free")?.addEventListener("click", () => handleRegisterOrEnter());
    document.getElementById("btn-lp-plan-pro")?.addEventListener("click", () => {
        if (state.currentUser?.authenticated) {
            mostrarWorkspace(state.selectedLandingGoal || "historico");
            abrirModalUpgrade();
            return;
        }
        abrirContaModal?.(true);
    });

    document.getElementById("btn-lp-explore")?.addEventListener("click", () => {
        mostrarWorkspace("historico");
    });
    document.getElementById("btn-lp-goal-explore")?.addEventListener("click", () => {
        mostrarWorkspace(state.selectedLandingGoal || "historico");
    });

    document.getElementById("btn-brand-home")?.addEventListener("click", () => {
        mostrarLanding();
    });

    const revealSections = landingView.querySelectorAll(".lp-reveal");
    const prefersReduced =
        window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false;

    if (prefersReduced || typeof window.IntersectionObserver !== "function") {
        revealSections.forEach((el) => el.classList.add("is-visible"));
    } else {
        landingView.classList.add("lp-motion-ready");
        const observer = new window.IntersectionObserver(
            (entries, obs) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("is-visible");
                        obs.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.12 }
        );
        revealSections.forEach((el) => observer.observe(el));
    }
}

function atualizarEstadoContaHeader() {
    const isAuth = Boolean(state.currentUser?.authenticated);
    const btnUpgrade = document.getElementById("btn-open-upgrade-modal");
    const btnRegister = document.getElementById("btn-open-register");
    const btnAccount = document.getElementById("btn-open-login");
    const profileInfo = document.getElementById("account-profile-info");
    const loginLabel = document.getElementById("account-login-label");

    if (btnUpgrade) btnUpgrade.classList.toggle("hidden", !isAuth);
    if (btnRegister) btnRegister.classList.toggle("hidden", isAuth);
    if (profileInfo) profileInfo.classList.toggle("hidden", !isAuth);
    if (loginLabel) loginLabel.classList.toggle("hidden", isAuth);
    if (btnAccount) {
        btnAccount.classList.toggle("btn-secondary", isAuth);
        btnAccount.classList.toggle("account-profile-btn", isAuth);
        btnAccount.classList.toggle("btn-primary", !isAuth);
    }

    const btnLpLogin = document.getElementById("btn-lp-login");
    const btnLpRegister = document.getElementById("btn-lp-register");
    if (btnLpLogin) {
        btnLpLogin.textContent = isAuth ? (state.currentUser?.nome || "Minha conta") : "Entrar";
    }
    if (btnLpRegister) {
        btnLpRegister.textContent = isAuth ? "Acessar plataforma" : "Criar conta gratuita";
    }
}

function atualizarPerfilSidebar(usuario) {
    if (!usuario) return;
    const nameEl = document.getElementById("sidebar-user-name");
    const oabEl = document.getElementById("sidebar-user-oab");
    const avatar = document.querySelector(".lawyer-avatar");
    if (nameEl) nameEl.textContent = usuario.nome || "";
    if (oabEl) oabEl.textContent = usuario.oab ? `OAB ${usuario.oab}` : "";
    if (avatar) {
        avatar.textContent = usuario.nome
            ? usuario.nome
                  .split(/\s+/)
                  .slice(0, 2)
                  .map((parte) => [...parte][0])
                  .join("")
                  .toUpperCase()
            : "";
    }
    atualizarEstadoContaHeader();
}

async function restaurarSessaoAutenticada() {
    if (typeof window === "undefined") return false;
    const token = localStorage.getItem("jurivision_token") || sessionStorage.getItem("jurivision_token");
    if (!token) {
        state.currentUser = { id: null, nome: "", oab: "", authenticated: false };
        state.savedDecisions = new Set();
        updateSavedCounterUI();
        atualizarEstadoContaHeader();
        return false;
    }
    try {
        const usuario = await fetchUsuarioAtual();
        state.currentUser = {
            ...usuario,
            authenticated: true,
            token,
        };
        state.savedDecisions = loadSavedIds(usuario.id);
        updateSavedCounterUI();
        atualizarPerfilSidebar(usuario);
        return true;
    } catch (err) {
        if (err && (err.status === 401 || err.status === 403)) {
            logoutAdvogado();
            state.currentUser = { id: null, nome: "", oab: "", authenticated: false };
            state.savedDecisions = new Set();
            updateSavedCounterUI();
            atualizarEstadoContaHeader();
        }
        return false;
    }
}

function configurarModais() {
    const accountDialog = document.getElementById("login-modal");
    const title = document.getElementById("login-modal-title");
    const sessionPanel = document.getElementById("account-session-panel");
    const loginForm = document.getElementById("login-form");
    const loginEmail = document.getElementById("login-email");
    const loginSenha = document.getElementById("login-senha");
    const loginFeedback = document.getElementById("login-feedback");
    const loginSubmit = loginForm.querySelector('[type="submit"]');
    const registerForm = document.getElementById("register-form");
    const registerFeedback = document.getElementById("register-feedback");
    const registerSubmit = registerForm.querySelector('[type="submit"]');

    function mostrarFeedback(elemento, mensagem, erro = false) {
        elemento.dataset.error = String(erro);
        elemento.textContent = mensagem;
    }

    function abrirConta(cadastro = false, forceForm = false) {
        const showSession = Boolean(state.currentUser?.authenticated) && !cadastro && !forceForm;
        if (sessionPanel) {
            sessionPanel.hidden = !showSession;
        }
        if (showSession) {
            title.textContent = "Sua conta";
            loginForm.hidden = true;
            registerForm.hidden = true;

            const sName = document.getElementById("session-user-name");
            const sOab = document.getElementById("session-user-oab");
            const sPlan = document.getElementById("session-user-plan");
            const isPro = Boolean(state.planStatus?.recursos_pro_liberados || state.planStatus?.plano === "PRO");
            const used = Number(state.planStatus?.analises_realizadas ?? 0);
            const limit = Number(state.planStatus?.limite_analises_free ?? 3);

            if (sName) sName.textContent = state.currentUser.nome || "Advogado(a)";
            if (sOab) sOab.textContent = state.currentUser.oab ? `OAB ${state.currentUser.oab}` : "";
            if (sPlan) {
                sPlan.textContent = isPro
                    ? "Plano ativo: JuriVision PRO"
                    : `Plano ativo: Gratuito (FREE) · ${used}/${limit} análises PDF`;
            }

            if (!accountDialog.open) accountDialog.showModal();
            document.getElementById("btn-switch-account")?.focus();
            return;
        }

        title.textContent = cadastro ? "Cadastro de advogado" : "Entrar na conta";
        loginForm.hidden = cadastro;
        registerForm.hidden = !cadastro;
        if (!accountDialog.open) accountDialog.showModal();
        (cadastro ? registerForm.elements.nome : loginEmail).focus();
    }

    abrirContaModal = abrirConta;

    document.getElementById("btn-open-login")?.addEventListener("click", () => abrirConta());
    document.getElementById("btn-open-register")?.addEventListener("click", () => abrirConta(true));
    document.getElementById("btn-switch-to-register")?.addEventListener("click", () => abrirConta(true));
    document.getElementById("btn-open-login-from-register")?.addEventListener("click", () => abrirConta(false, true));
    document.getElementById("btn-switch-account")?.addEventListener("click", () => abrirConta(false, true));
    document.getElementById("btn-session-manage-plan")?.addEventListener("click", () => {
        accountDialog?.close();
        abrirModalUpgrade();
    });
    document.getElementById("btn-close-login")?.addEventListener("click", () => accountDialog?.close());
    accountDialog?.addEventListener("close", () => {
        if (registerForm?.elements?.senha) registerForm.elements.senha.value = "";
    });

    registerForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (registerSubmit.disabled) return;
        const payload = Object.fromEntries(new FormData(registerForm));
        registerSubmit.disabled = true;
        mostrarFeedback(registerFeedback, "Criando conta…");
        try {
            const usuario = await registerAdvogado(payload);
            registerForm.reset();
            mostrarFeedback(registerFeedback, "");
            if (accountDialog.open && registerForm.hidden) {
                showToast("Conta criada. Entre com o e-mail cadastrado.");
                return;
            }
            loginEmail.value = usuario.email;
            loginSenha.value = "";
            if (accountDialog.open) abrirConta(false, true);
            mostrarFeedback(loginFeedback, "Conta criada. Entre com sua senha.");
            if (!accountDialog.open) showToast("Conta criada. Acesse sua conta para entrar.");
        } catch (err) {
            const mensagem = err instanceof TypeError
                ? "Não foi possível conectar ao servidor. Tente novamente."
                : err.message;
            mostrarFeedback(registerFeedback, mensagem, true);
        } finally {
            registerSubmit.disabled = false;
        }
    });

    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (loginSubmit.disabled) return;
        const email = loginEmail.value.trim();
        const senha = loginSenha.value;
        loginSubmit.disabled = true;
        mostrarFeedback(loginFeedback, "Verificando credenciais do advogado…");

        try {
            const res = await loginAdvogado(email, senha);
            state.currentUser = {
                ...res.usuario,
                authenticated: true,
                token: res.access_token,
            };
            state.savedDecisions = loadSavedIds(res.usuario.id);
            updateSavedCounterUI();
            atualizarPerfilSidebar(res.usuario);
            loginSenha.value = "";
            mostrarFeedback(loginFeedback, "");
            showToast(`Bem-vindo(a), ${res.usuario.nome}.`);
            if (accountDialog.open && !loginForm.hidden) accountDialog.close();
            await carregarStatusPlano();
            mostrarWorkspace(state.selectedLandingGoal || "historico");
        } catch (err) {
            mostrarFeedback(loginFeedback, err.message || "Não foi possível autenticar com as credenciais informadas.", true);
        } finally {
            loginSubmit.disabled = false;
        }
    });

    document.getElementById("btn-logout-account")?.addEventListener("click", () => {
        logoutAdvogado();
        state.currentUser = {
            id: null,
            nome: "",
            oab: "",
            authenticated: false,
        };
        state.savedDecisions = new Set();
        state.planStatus = { ...DEFAULT_FREE_PLAN };
        state.lastAnalyzedProcessId = null;
        state.drawerProcessId = null;
        state.currentDrawerPayload = null;
        updateSavedCounterUI();
        atualizarPerfilSidebar(state.currentUser);
        atualizarUIPlano();
        mostrarFeedback(loginFeedback, "");
        if (accountDialog.open) accountDialog.close();
        fecharDrawerProcesso();
        carregarFiltrosDinamicos();
        mostrarLanding();
        showToast("Sessão encerrada.");
    });

    // Modal de Informações e Privacidade
    const methModal = document.getElementById("methodology-modal");
    document.getElementById("btn-close-methodology")?.addEventListener("click", () => {
        methModal?.classList.add("hidden");
    });
}

function atualizarUIPlano() {
    const status = state.planStatus || {};
    const isPro = Boolean(status.recursos_pro_liberados || status.plano === "PRO");
    const utilizadas = Number(status.analises_realizadas ?? 0);
    const limite = Number(status.limite_analises_free ?? 3);

    const badgeBtn = document.getElementById("btn-open-upgrade-modal");
    const badgeLabel = document.getElementById("plan-status-badge");
    if (badgeBtn) {
        badgeBtn.classList.toggle("plan-badge-pro", isPro);
        badgeBtn.classList.toggle("plan-badge-free", !isPro);
    }
    if (badgeLabel) {
        badgeLabel.textContent = isPro
            ? "Plano PRO"
            : `Plano FREE · ${utilizadas}/${limite}`;
    }

    const summaryEl = document.getElementById("upgrade-quota-summary");
    if (summaryEl) {
        summaryEl.textContent = isPro
            ? "Plano atual: PRO · Análises de PDF/CSV ilimitadas, Tese Estratégica RAG completa e relatórios PDF habilitados."
            : `Plano atual: FREE · ${utilizadas} de ${limite} análises gratuitas de PDF utilizadas.`;
    }

    const thesisCard = document.getElementById("res-thesis-card");
    const lockBanner = document.getElementById("thesis-pro-lock-banner");
    const teseLiberada = isPro || Boolean(status.tese_aprofundada_liberada);
    if (thesisCard) {
        thesisCard.classList.toggle("is-free-locked", !teseLiberada);
    }
    if (lockBanner) {
        lockBanner.classList.toggle("hidden", teseLiberada);
    }
}

async function carregarStatusPlano() {
    if (!state.currentUser?.authenticated) {
        state.planStatus = { ...DEFAULT_FREE_PLAN };
        atualizarUIPlano();
        return;
    }
    try {
        const status = await fetchStatusPlano();
        state.planStatus = status;
    } catch {
        // Mantém estado local atual caso servidor não responda
    }
    atualizarUIPlano();
}

export function abrirModalUpgrade(motivo = "") {
    const dialog = document.getElementById("upgrade-modal");
    const reasonEl = document.getElementById("upgrade-reason-banner");
    const feedbackEl = document.getElementById("upgrade-feedback");
    if (feedbackEl) feedbackEl.textContent = "";
    if (reasonEl) {
        if (motivo) {
            reasonEl.textContent = motivo;
            reasonEl.classList.remove("hidden");
        } else {
            reasonEl.textContent = "";
            reasonEl.classList.add("hidden");
        }
    }
    atualizarUIPlano();
    if (dialog && !dialog.open) {
        dialog.showModal();
    }
}

function configurarModalUpgrade() {
    const dialog = document.getElementById("upgrade-modal");
    const feedbackEl = document.getElementById("upgrade-feedback");
    const btnOpen = document.getElementById("btn-open-upgrade-modal");
    const btnUnlockThesis = document.getElementById("btn-unlock-thesis-pro");
    const btnClose = document.getElementById("btn-close-upgrade");
    const btnActivatePro = document.getElementById("btn-activate-pro");
    const btnSimulateFree = document.getElementById("btn-simulate-free");

    btnOpen?.addEventListener("click", () => abrirModalUpgrade());
    btnUnlockThesis?.addEventListener("click", () =>
        abrirModalUpgrade("Desbloqueie a Tese Estratégica Completa e análises ilimitadas com o plano JuriVision PRO.")
    );
    btnClose?.addEventListener("click", () => dialog?.close());

    async function aplicarPlano(targetPlano) {
        const token = typeof window !== "undefined"
            ? localStorage.getItem("jurivision_token") || sessionStorage.getItem("jurivision_token")
            : null;
        if (!token) {
            state.planStatus = {
                ...state.planStatus,
                plano: targetPlano,
                recursos_pro_liberados: targetPlano === "PRO",
                lote_csv_liberado: targetPlano === "PRO",
                tese_aprofundada_liberada: targetPlano === "PRO",
                analises_restantes: targetPlano === "PRO" ? 999999 : 3,
            };
            atualizarUIPlano();
            if (feedbackEl) {
                feedbackEl.dataset.error = "false";
                feedbackEl.textContent = targetPlano === "PRO"
                    ? "Modo demonstração PRO ativado (cortesia CONAD 2026)."
                    : "Modo demonstração FREE ativado para visualizar o paywall. Faça login para persistir cotas.";
            }
            return;
        }

        try {
            const atualizado = await atualizarPlanoAssinatura(targetPlano, "CONAD2026");
            state.planStatus = atualizado;
            atualizarUIPlano();
            if (feedbackEl) {
                feedbackEl.dataset.error = "false";
                feedbackEl.textContent = targetPlano === "PRO"
                    ? "Plano JuriVision PRO ativado com sucesso (Cortesia CONAD 2026)!"
                    : "Plano alternado para FREE para demonstração de cotas e paywall.";
            }
            showToast(`Plano atualizado para ${targetPlano}.`);
        } catch (err) {
            if (feedbackEl) {
                feedbackEl.dataset.error = "true";
                feedbackEl.textContent = err.message || "Não foi possível alterar o plano.";
            }
        }
    }

    btnActivatePro?.addEventListener("click", () => aplicarPlano("PRO"));
    btnSimulateFree?.addEventListener("click", () => aplicarPlano("FREE"));
}

/* ==========================================================================
   9. Inicialização de Eventos da Aplicação
   ========================================================================== */
async function initApp() {
    configurarIntroMarca();
    updateSavedCounterUI();
    atualizarEstadoContaHeader();
    setupTabKeyboardNavigation();
    configurarModais();
    configurarModalUpgrade();

    // Abas principais
    document.getElementById("btn-historico")?.addEventListener("click", () => switchTab("historico"));
    document.getElementById("btn-dashboard")?.addEventListener("click", () => switchTab("dashboard"));
    document.getElementById("btn-upload")?.addEventListener("click", () => switchTab("upload"));

    // Ações de navegação contextual
    document.getElementById("btn-go-jurimetria-from-search")?.addEventListener("click", () => {
        switchTab("dashboard");
        showToast("Exibindo indicadores jurimétricos do acervo consultado.");
    });

    // Estado vazio da Jurimetria: mesmas ações de primeiro passo da Pesquisa
    document.getElementById("btn-dash-empty-sync")?.addEventListener("click", dispararSincronizacaoDataJud);
    document.getElementById("btn-dash-empty-julgado")?.addEventListener("click", () => {
        document.getElementById("btn-novo-julgado")?.click();
    });
    document.getElementById("btn-dash-empty-upload")?.addEventListener("click", () => {
        switchTab("upload");
        window.scrollTo({ top: 0, behavior: "auto" });
    });

    document.getElementById("btn-overview-ver-todos")?.addEventListener("click", () => {
        switchTab("historico");
    });

    // Filtros dinâmicos e alternância de visualização na Análise Jurimétrica
    document.getElementById("dash-filtro-tema")?.addEventListener("change", (e) => {
        state.dashboardFiltroTema = e.target.value || "";
        carregarDashboard();
    });
    document.getElementById("dash-filtro-juiz")?.addEventListener("change", (e) => {
        state.dashboardFiltroJuiz = e.target.value || "";
        carregarDashboard();
    });
    document.getElementById("btn-dash-limpar-filtros")?.addEventListener("click", () => {
        state.dashboardFiltroTema = "";
        state.dashboardFiltroJuiz = "";
        const selTema = document.getElementById("dash-filtro-tema");
        const selJuiz = document.getElementById("dash-filtro-juiz");
        if (selTema) selTema.value = "";
        if (selJuiz) selJuiz.value = "";
        carregarDashboard();
    });

    document.getElementById("btn-juiz-mode-qtd")?.addEventListener("click", () => alternarModoGraficoJuizes("qtd"));
    document.getElementById("btn-juiz-mode-pct")?.addEventListener("click", () => alternarModoGraficoJuizes("pct"));
    document.getElementById("btn-tema-mode-vol")?.addEventListener("click", () => alternarModoGraficoTemas("vol"));
    document.getElementById("btn-tema-mode-taxa")?.addEventListener("click", () => alternarModoGraficoTemas("taxa"));

    // Alternância entre Cartões de Decisão e Tabela Comparativa
    document.getElementById("btn-view-cards")?.addEventListener("click", () => alternarVisaoResultados("cards"));
    document.getElementById("btn-view-table")?.addEventListener("click", () => alternarVisaoResultados("table"));

    // Submissão de PDF / CSV
    document.getElementById("mode-btn-pdf")?.addEventListener("click", () => alternarModoUpload("pdf"));
    document.getElementById("mode-btn-csv")?.addEventListener("click", () => alternarModoUpload("csv"));

    const inputPdf = document.getElementById("file-input-pdf");
    const inputCsv = document.getElementById("file-input-csv");
    inputPdf?.addEventListener("change", (e) => {
        const file = e.target.files?.[0];
        if (file) processarArquivoPdf(file);
    });
    inputCsv?.addEventListener("change", (e) => {
        const file = e.target.files?.[0];
        if (file) processarArquivoCsv(file);
    });

    // Suporte a Arrastar e Soltar (Drag & Drop)
    const boxPdf = document.getElementById("upload-box-pdf");
    if (boxPdf) {
        ["dragenter", "dragover"].forEach((evt) => {
            boxPdf.addEventListener(evt, (e) => {
                e.preventDefault();
                boxPdf.classList.add("dragover");
            });
        });
        ["dragleave", "drop"].forEach((evt) => {
            boxPdf.addEventListener(evt, (e) => {
                e.preventDefault();
                boxPdf.classList.remove("dragover");
            });
        });
        boxPdf.addEventListener("drop", (e) => {
            const files = e.dataTransfer?.files;
            if (files && files.length > 0) {
                processarArquivoPdf(files[0]);
            }
        });
    }

    const boxCsv = document.getElementById("upload-box-csv");
    if (boxCsv) {
        ["dragenter", "dragover"].forEach((evt) => {
            boxCsv.addEventListener(evt, (e) => {
                e.preventDefault();
                boxCsv.classList.add("dragover");
            });
        });
        ["dragleave", "drop"].forEach((evt) => {
            boxCsv.addEventListener(evt, (e) => {
                e.preventDefault();
                boxCsv.classList.remove("dragover");
            });
        });
        boxCsv.addEventListener("drop", (e) => {
            const files = e.dataTransfer?.files;
            if (files && files.length > 0) {
                processarArquivoCsv(files[0]);
            }
        });
    }

    document.getElementById("btn-sample-pdf")?.addEventListener("click", () => {
        processarArquivoPdf(buildSamplePetitionPdfFile());
    });
    document.getElementById("btn-sample-csv")?.addEventListener("click", () => {
        processarArquivoCsv(buildSampleBatchCsvFile());
    });

    document.getElementById("btn-reset-upload")?.addEventListener("click", resetarFluxoUpload);
    document.getElementById("btn-reset-csv")?.addEventListener("click", resetarFluxoUpload);
    document.getElementById("btn-retry-error")?.addEventListener("click", resetarFluxoUpload);

    // Exportação PDF (RF-09)
    document.getElementById("btn-result-export-pdf")?.addEventListener("click", () => {
        exportarRelatorioPdfProcesso(state.lastAnalyzedProcessId);
    });

    // Filtros e paginação na Pesquisa Jurisprudencial (RF-08)
    
    // Consulta Oficial e Sincronização em Lote DataJud (CNJ)
    document.getElementById("btn-consultar-datajud")?.addEventListener("click", dispararConsultaDataJud);
    document.getElementById("btn-sincronizar-datajud")?.addEventListener("click", dispararSincronizacaoDataJud);
    document.getElementById("btn-fechar-datajud")?.addEventListener("click", () => {
        document.getElementById("datajud-result-box")?.classList.add("hidden");
    });

    document.getElementById("form-filtros-historico")?.addEventListener("submit", (e) => {
        e.preventDefault();
        carregarBaseConhecimento(1);
    });

    ["filtro-tema", "filtro-juiz", "filtro-ordenacao", "filtro-colecao"].forEach((id) => {
        document.getElementById(id)?.addEventListener("change", () => carregarBaseConhecimento(1));
    });

    document.getElementById("btn-limpar-filtros")?.addEventListener("click", () => {
        const fBusca = document.getElementById("filtro-busca");
        const fTema = document.getElementById("filtro-tema");
        const fJuiz = document.getElementById("filtro-juiz");
        const fCol = document.getElementById("filtro-colecao");
        if (fBusca) fBusca.value = "";
        if (fTema) fTema.value = "";
        if (fJuiz) fJuiz.value = "";
        if (fCol) fCol.value = "todos";
        carregarBaseConhecimento(1);
    });

    document.getElementById("btn-page-prev")?.addEventListener("click", () => {
        if (state.paginaAtual > 1) carregarBaseConhecimento(state.paginaAtual - 1);
    });
    document.getElementById("btn-page-next")?.addEventListener("click", () => {
        carregarBaseConhecimento(state.paginaAtual + 1);
    });

    // Leitor Individual de Decisão (#drawer-processo)
    document.getElementById("btn-close-drawer")?.addEventListener("click", fecharDrawerProcesso);
    document.getElementById("btn-drawer-export-pdf")?.addEventListener("click", () => {
        exportarRelatorioPdfProcesso(state.drawerProcessId);
    });
    document.getElementById("btn-drawer-open-dossier")?.addEventListener("click", () => {
        if (state.currentDrawerPayload) {
            renderizarResultadoPredicaoPdf(state.currentDrawerPayload);
        }
        fecharDrawerProcesso();
        switchTab("upload");
    });
    document.getElementById("btn-drawer-save")?.addEventListener("click", () => {
        toggleSalvarDecisao(state.drawerProcessId);
        const saveBtn = document.getElementById("btn-drawer-save");
        if (saveBtn) {
            saveBtn.textContent = state.savedDecisions.has(state.drawerProcessId)
                ? "Salva na biblioteca"
                : "Salvar decisão";
        }
    });
    document.getElementById("btn-drawer-copy-ref")?.addEventListener("click", () => {
        if (state.currentDrawerPayload) {
            const meta = state.currentDrawerPayload.metadados_extraidos;
            copiarReferenciaDecisao({
                numero_processo: meta.numero_processo,
                comarca: meta.comarca,
                magistrado: meta.magistrado,
                tema: meta.tema,
                data_julgamento: state.currentDrawerPayload.data_julgamento,
            });
        }
    });

    document.getElementById("btn-excluir-julgado")?.addEventListener("click", async () => {
        const idProc = state.drawerProcessId;
        if (!idProc) return;
        const btnExcluir = document.getElementById("btn-excluir-julgado");
        if (btnExcluir) btnExcluir.disabled = true;
        try {
            await excluirProcesso(idProc);
            state.savedDecisions.delete(idProc);
            persistSavedIds(state.savedDecisions, state.currentUser?.id);
            updateSavedCounterUI();
            fecharDrawerProcesso();
            await Promise.all([
                carregarFiltrosDinamicos(),
                carregarBaseConhecimento(1),
                carregarDashboard(),
            ]);
            showToast("Julgado excluído do acervo.");
        } catch (err) {
            showToast(err.message || "Não foi possível excluir o julgado.");
        } finally {
            if (btnExcluir) btnExcluir.disabled = false;
        }
    });

    configurarFormularioJulgado({
        obterDetalhes: () => state.currentDrawerPayload,
        aoSalvar: (detalhes, edicao) => {
            if (edicao) exibirDrawerProcesso(detalhes);
            carregarFiltrosDinamicos();
            carregarBaseConhecimento(edicao ? state.paginaAtual : 1);
            carregarDashboard();
            showToast(edicao ? "Julgado atualizado." : "Julgado cadastrado.");
        },
    });

    // Navegação do rodapé institucional
    document.querySelectorAll("[data-footer-tab]").forEach((btn) => {
        btn.addEventListener("click", () => {
            const tabId = btn.getAttribute("data-footer-tab");
            if (tabId) {
                switchTab(tabId);
                const prefersReduced =
                    window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false;
                window.scrollTo({ top: 0, behavior: prefersReduced ? "auto" : "smooth" });
            }
        });
    });

    document.querySelectorAll("[data-footer-action='methodology']").forEach((btn) => {
        btn.addEventListener("click", () => {
            document.getElementById("methodology-modal")?.classList.remove("hidden");
        });
    });

    document.querySelectorAll("[data-footer-action='landing']").forEach((btn) => {
        btn.addEventListener("click", () => {
            mostrarLanding();
        });
    });

    // Atalho global Escape para fechar janelas sobrepostas
    window.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !document.querySelector("dialog[open]")) {
            fecharDrawerProcesso();
            document.getElementById("methodology-modal")?.classList.add("hidden");
        }
    });

    setupScrollReveal();
    configurarLandingPage();
    let isAuthenticated = false;
    try {
        isAuthenticated = await restaurarSessaoAutenticada();
    } finally {
        iniciarIntroAdiada(!isAuthenticated);
    }
    await carregarStatusPlano();
    verificarConectividadeApi();
    if (isAuthenticated) {
        mostrarWorkspace("historico");
    } else {
        mostrarLanding();
    }
    concluirIntroMarca();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initApp);
} else {
    initApp();
}
