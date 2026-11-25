/**
 * Controlador de Experiência Jurídica, Pesquisa Jurisprudencial, Leitura Documental e Jurimetria — JuriVision.
 * Direção Estética e Funcional: Legal Editorial + Legal Intelligence
 * Referência: Guia de UI/UX e Direção Visual — Plataforma de Jurimetria para Advocacia
 * Rastreabilidade:
 * - Requisitos Funcionais: RF-01 a RF-09
 * - Requisitos Não Funcionais: RNF-04 (ISO 9241-110 & Nielsen), RNF-09 (WCAG 2.2 AA), RNF-10 (Leis de UX & Gestalt)
 */

import { configurarFormularioJulgado } from "./components/julgado-form.js";
import { casosComparador, criarPecasDemonstrativas } from "./components/comparador-demo.js";
import {
    buildSampleBatchCsvFile,
    buildSamplePetitionPdfFile,
    checkApiHealth,
    compararPecas,
    consultarProcessoDatajud,
    fetchDashboardMetricas,
    fetchProcessoDetalhes,
    fetchProcessos,
    getRelatorioPdfUrl,
    loginAdvogado,
    registerAdvogado,
    sincronizarLoteDatajud,
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
        resumo_curto:
            "Responsabilidade civil no transporte aéreo. Cancelamento de voo e atraso superior a quatro horas sem prestação de assistência material adequada ao passageiro.",
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
        resumo_curto:
            "Inscrição indevida em cadastro de proteção ao crédito decorrente de cobrança de dívida já quitada. Dano moral configurado in re ipsa.",
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
        resumo_curto:
            "Reclamação trabalhista referente a verbas rescisórias e horas extras. Composição amigável homologada em audiência.",
    },
];

function loadSavedIds() {
    try {
        const raw = window.localStorage.getItem("jurivision_saved_decisions");
        if (raw) {
            const parsed = JSON.parse(raw);
            if (Array.isArray(parsed)) return new Set(parsed);
        }
    } catch {
        // Ignorar erro de localStorage em ambientes restritos
    }
    return new Set(["proc-1004", "proc-1001"]);
}

function persistSavedIds(savedSet) {
    try {
        window.localStorage.setItem(
            "jurivision_saved_decisions",
            JSON.stringify(Array.from(savedSet))
        );
    } catch {
        // Ignorar erro de localStorage
    }
}

const state = {
    activeTab: "historico",
    resultsViewMode: "cards", // "cards" (documental) | "table" (comparativa)
    uploadMode: "pdf",
    apiOnline: false,
    currentUser: {
        id: "usr-01",
        nome: "Dr. Lucas Gabriel",
        oab: "OAB/AL 12.345",
        authenticated: true,
    },
    savedDecisions: loadSavedIds(),
    lastAnalyzedProcessId: "proc-1004",
    drawerProcessId: "proc-1004",
    currentDrawerPayload: null,
    paginaAtual: 1,
    limitePorPagina: 8,
    totalProcessosLista: 0,
    lastLoadedItems: [],
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
    persistSavedIds(state.savedDecisions);
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
   1. Navegação Principal entre Áreas (WAI-ARIA 1.2 Tab Pattern + Teclado)
   ========================================================================== */
export function switchTab(tabId, moveFocus = false) {
    state.activeTab = tabId;
    const tabs = ["historico", "dashboard", "upload", "comparador"];

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
        historico: "Pesquisa Jurisprudencial",
        dashboard: "Análise Jurimétrica do Conjunto",
        upload: "Análise Comparativa de Petição e Importação",
        comparador: "Visualizador Comparativo de Peças (Art. 357 CPC)",
    };
    const headerTitle = document.getElementById("header-title");
    if (headerTitle) headerTitle.textContent = titles[tabId] || "JuriVision";

    announceStatus(`Área ativa: ${titles[tabId]}`);

    if (tabId === "dashboard") {
        carregarDashboard();
    } else if (tabId === "historico") {
        carregarBaseConhecimento();
    }
}

function setupTabKeyboardNavigation() {
    const tabOrder = ["historico", "dashboard", "upload", "comparador"];
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
    const motorEl = document.getElementById("kpi-motor-ia");
    try {
        const health = await checkApiHealth();
        state.apiOnline = true;
        const provider = health.ai_provider_configured || "local";
        if (badge) {
            badge.innerHTML = `<span class="dot dot-success" aria-hidden="true"></span><span>TJAL Conectado</span>`;
        }
        if (motorEl) {
            motorEl.textContent =
                provider === "local" ? "Estruturada" : `Classificação (${provider})`;
        }
    } catch {
        state.apiOnline = false;
        if (badge) {
            badge.innerHTML = `<span class="dot dot-warning" aria-hidden="true"></span><span>Base Local</span>`;
        }
    }
}

/* ==========================================================================
   3. Jurimetria e Análise Estatística com Denominadores e Aprofundamento (RF-07)
   ========================================================================== */
async function carregarDashboard() {
    let metricas = FALLBACK_METRICAS;
    try {
        metricas = await fetchDashboardMetricas();
        state.apiOnline = true;
    } catch {
        // Fallback demonstrativo resiliente
    }

    const total = metricas.total_processos_analisados || 10;
    const pct = (metricas.taxa_exito_global * 100).toFixed(1);
    const favCount = Math.round(metricas.taxa_exito_global * total);

    const elTaxa = document.getElementById("kpi-taxa-exito");
    const elDenom = document.getElementById("kpi-taxa-denominador");
    const elPrazo = document.getElementById("kpi-tempo-medio");
    const elTotal = document.getElementById("kpi-total-processos");
    const elSidebarCount = document.getElementById("sidebar-total-count");

    if (elTaxa) elTaxa.textContent = `${pct}%`;
    if (elDenom) {
        elDenom.textContent = `${favCount} favoráveis em ${total} julgados`;
    }
    if (elPrazo) elPrazo.textContent = `${metricas.tempo_medio_tramitacao_meses} Meses`;
    if (elTotal) elTotal.textContent = String(total);
    if (elSidebarCount) elSidebarCount.textContent = String(total);

    renderizarMatrizesPrecisao(metricas);
    renderizarGraficos(metricas);
    preencherTabelasAcessiveisGraficos(metricas);
    carregarPrecedentesRecentesOverview();
}

function escapeHtml(value) {
    const entities = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return String(value ?? "").replace(/[&<>"']/g, (character) => entities[character]);
}

function renderizarMatrizesPrecisao(metricas) {
    const judgeList = document.getElementById("judge-matrix-list");
    if (judgeList) {
        judgeList.innerHTML = metricas.decisoes_por_juiz
            .map((d) => {
                const total = Math.max(d.procedentes + d.improcedentes, 1);
                const favPct = Math.round((d.procedentes / total) * 100);
                return `
                <div class="comparative-bar-row">
                    <div class="comparative-row-top">
                        <div>
                            <strong style="color: var(--color-navy); font-size: var(--text-sm);">${escapeHtml(d.juiz)}</strong>
                            <span style="display: block; font-size: var(--text-xs); color: var(--text-muted);">
                                ${total} julgados (${d.procedentes} fav. / ${d.improcedentes} impr.)
                            </span>
                        </div>
                        <div style="text-align: right;">
                            <strong class="tabular-nums" style="color: var(--color-navy); font-size: var(--text-sm);">${favPct}% fav.</strong>
                            <div>
                                <button type="button" class="btn btn-ghost btn-sm btn-drill-judge" data-judge="${escapeHtml(d.juiz)}" style="padding: 0 4px; min-height: 22px; font-size: 11px;">
                                    Filtrar (${total})
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="comparative-track" aria-hidden="true">
                        <div class="comparative-fill-primary" style="width: ${favPct}%;"></div>
                    </div>
                </div>`;
            })
            .join("");

        judgeList.querySelectorAll(".btn-drill-judge").forEach((btn) => {
            btn.addEventListener("click", () => {
                const rawJudge = btn.getAttribute("data-judge") || "";
                const selectJuiz = document.getElementById("filtro-juiz");
                if (selectJuiz) {
                    const cleaned = rawJudge.replace(/^Dra?\.\s*/i, "");
                    selectJuiz.value = cleaned;
                }
                switchTab("historico");
                showToast(`Exibindo decisões filtradas por: ${rawJudge}`);
            });
        });
    }

    const totalGlobal = metricas.total_processos_analisados || 10;
    const themeList = document.getElementById("theme-matrix-list");
    if (themeList) {
        themeList.innerHTML = metricas.volume_por_tema
            .map((t) => {
                const approxCount = Math.max(1, Math.round((t.percentual / 100) * totalGlobal));
                return `
                <div class="comparative-bar-row">
                    <div class="comparative-row-top">
                        <div>
                            <strong style="color: var(--color-navy); font-size: var(--text-sm);">${escapeHtml(t.tema)}</strong>
                            <span style="display: block; font-size: var(--text-xs); color: var(--text-muted);">
                                ${approxCount} julgados (${t.percentual}%)
                            </span>
                        </div>
                        <button type="button" class="btn btn-ghost btn-sm btn-drill-theme" data-theme="${escapeHtml(t.tema)}" style="padding: 0 4px; min-height: 22px; font-size: 11px;">
                            Filtrar (${approxCount})
                        </button>
                    </div>
                    <div class="comparative-track" aria-hidden="true">
                        <div class="comparative-fill-secondary" style="width: ${t.percentual}%;"></div>
                    </div>
                </div>`;
            })
            .join("");

        themeList.querySelectorAll(".btn-drill-theme").forEach((btn) => {
            btn.addEventListener("click", () => {
                const tema = btn.getAttribute("data-theme") || "";
                const selectTema = document.getElementById("filtro-tema");
                if (selectTema) selectTema.value = tema;
                switchTab("historico");
                showToast(`Exibindo decisões do assunto: ${tema}`);
            });
        });
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
                        label: "Favoráveis (Procedentes / Acordos)",
                        data: metricas.decisoes_por_juiz.map((d) => d.procedentes),
                        backgroundColor: "#20364A",
                        barThickness: 22,
                    },
                    {
                        label: "Improcedentes",
                        data: metricas.decisoes_por_juiz.map((d) => d.improcedentes),
                        backgroundColor: "#CBD2D8",
                        barThickness: 22,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { boxWidth: 12, font: { size: 12, family: "Inter" } },
                    },
                },
                scales: {
                    x: { stacked: true, grid: { display: false } },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        ticks: { stepSize: 1 },
                        title: { display: true, text: "Nº de decisões", font: { size: 11 } },
                    },
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
                        label: "Participação no conjunto (%)",
                        data: metricas.volume_por_tema.map((t) => t.percentual),
                        backgroundColor: ["#20364A", "#58796D", "#6F889B", "#B29A74", "#95A5B2"],
                        barThickness: 18,
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
                    x: {
                        beginAtZero: true,
                        max: 100,
                        title: { display: true, text: "Percentual do conjunto (%)", font: { size: 11 } },
                    },
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
                <td>${escapeHtml(item.juiz)}</td>
                <td class="tabular-nums">${item.procedentes}</td>
                <td class="tabular-nums">${item.improcedentes}</td>
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
                <td>${escapeHtml(item.tema)}</td>
                <td class="tabular-nums">${item.percentual}%</td>
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
            const badgeClass =
                resLower === "improcedente" ? "badge-unfavorable" : "badge-favorable";

            return `
            <tr>
                <td class="font-mono" style="font-weight: 600; color: var(--color-navy);">${escapeHtml(item.numero_processo)}</td>
                <td style="font-weight: 500;">${escapeHtml(item.tema)}</td>
                <td>${escapeHtml(item.magistrado)}</td>
                <td style="color: var(--text-secondary);">${escapeHtml(item.partes_anonimizadas)}</td>
                <td>
                    <span class="badge-editorial ${badgeClass}">${escapeHtml(item.resultado)}</span>
                </td>
                <td style="text-align: right;">
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

export async function carregarBaseConhecimento(novaPagina = null) {
    if (novaPagina !== null) {
        state.paginaAtual = novaPagina;
    }

    const busca = document.getElementById("filtro-busca")?.value.trim() || "";
    const tema = document.getElementById("filtro-tema")?.value || "";
    const juiz = document.getElementById("filtro-juiz")?.value || "";
    const ordenacao = document.getElementById("filtro-ordenacao")?.value || "recentes";
    const colecao = document.getElementById("filtro-colecao")?.value || "todos";

    renderizarChipsFiltrosAtivos();

    let lista = {
        total: FALLBACK_PROCESSOS.length,
        pagina: 1,
        itens: [...FALLBACK_PROCESSOS],
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

    let itens = Array.isArray(lista.itens) ? [...lista.itens] : [];

    // Filtro de biblioteca pessoal ("Decisões salvas")
    if (colecao === "salvos") {
        itens = itens.filter((item) => state.savedDecisions.has(item.id_processo));
    }

    // Ordenação transparente conforme Seção 11.6
    itens.sort((a, b) => {
        if (ordenacao === "antigas") {
            return String(a.data_julgamento || "").localeCompare(String(b.data_julgamento || ""));
        }
        if (ordenacao === "assunto") {
            return String(a.tema || "").localeCompare(String(b.tema || ""));
        }
        return String(b.data_julgamento || "").localeCompare(String(a.data_julgamento || ""));
    });

    state.lastLoadedItems = itens;
    state.totalProcessosLista = colecao === "salvos" ? itens.length : lista.total;

    const countLabel = document.getElementById("historico-total-label");
    if (countLabel) {
        countLabel.textContent = `${state.totalProcessosLista} decisões encontradas`;
    }

    renderizarListaDecisoes(itens);
    atualizarControlesPaginacao();
}

function renderizarListaDecisoes(itens) {
    const cardsContainer = document.getElementById("decisions-cards-container");
    const tbody = document.getElementById("historico-tbody");

    if (!itens || itens.length === 0) {
        const emptyHtml = `
            <div class="decisions-empty-state">
                <strong class="decisions-empty-title">
                    Nenhuma decisão foi encontrada com esses critérios
                </strong>
                <p class="decisions-empty-text">
                    Remova um dos filtros ativos ou experimente pesquisar por outro assunto, órgão julgador ou expressão jurídica.
                </p>
            </div>`;
        if (cardsContainer) cardsContainer.innerHTML = emptyHtml;
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="table-empty-cell">
                        Nenhuma decisão foi encontrada com esses critérios. Remova um filtro ou tente uma expressão diferente.
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
                const comarca = item.comarca || "1ª Vara Cível de Maceió";
                const sintese =
                    item.resumo_curto ||
                    `Decisão judicial proferida nos autos do processo nº ${item.numero_processo} sob relatoria/juízo de ${item.magistrado} (${comarca}), envolvendo ${item.partes_anonimizadas}.`;

                return `
                <article class="decision-card" data-card-proc-id="${escapeHtml(item.id_processo)}">
                    <div class="decision-card-header">
                        <div class="decision-meta-line">
                            <span>TJAL · ${escapeHtml(comarca)}</span>
                            <span class="decision-meta-sep" aria-hidden="true">·</span>
                            <span class="decision-cnj">${escapeHtml(item.numero_processo)}</span>
                            <span class="decision-meta-sep" aria-hidden="true">·</span>
                            <span>${escapeHtml(item.magistrado)}</span>
                            <span class="decision-meta-sep" aria-hidden="true">·</span>
                            <span class="decision-date">${dataJulg}</span>
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

                    <h3 class="decision-subject-title">${escapeHtml(item.tema)}</h3>

                    <p class="decision-excerpt">
                        ${escapeHtml(sintese)}
                    </p>
                    <p class="decision-parties" title="Partes com proteção LGPD">
                        Partes: ${escapeHtml(item.partes_anonimizadas)}
                    </p>

                    <div class="decision-card-footer">
                        <div class="decision-actions-group">
                            <button type="button" class="btn btn-read-decision btn-inspecionar-proc" data-inspect-id="${escapeHtml(item.id_processo)}">
                                Ler decisão
                            </button>
                            <button type="button" class="btn-text-action btn-salvar-proc${isSaved ? " is-saved" : ""}" data-save-id="${escapeHtml(item.id_processo)}">
                                ${isSaved ? "Salva ✓" : "Salvar"}
                            </button>
                            <button type="button" class="btn-text-action btn-copiar-ref" data-ref-id="${escapeHtml(item.id_processo)}">
                                Copiar ref.
                            </button>
                        </div>

                        <div class="decision-actions-group">
                            <button type="button" class="btn-text-action btn-text-muted btn-exportar-pdf" data-pdf-id="${escapeHtml(item.id_processo)}">
                                PDF
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
    announceStatus("Examinando documento e aplicando proteção de dados pessoais...");

    try {
        const resultado = await uploadProcessoPdf(file);
        document.getElementById("loading-state")?.classList.add("hidden");
        document.getElementById("upload-selection-container")?.classList.remove("hidden");
        renderizarResultadoPredicaoPdf(resultado);
        showToast(
            `Estudo comparativo concluído para o processo ${resultado.metadados_extraidos.numero_processo}.`
        );
        carregarDashboard();
    } catch (err) {
        exibirErroUpload(err.message || "Não foi possível ler o arquivo PDF enviado.");
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

        showToast(`${resCsv.total_importados_com_sucesso} decisões adicionadas ao acervo.`);
        carregarDashboard();
    } catch (err) {
        exibirErroUpload(err.message || "Não foi possível importar a planilha CSV.");
    }
}

export function renderizarResultadoPredicaoPdf(payload) {
    document.getElementById("result-empty-state")?.classList.add("hidden");
    document.getElementById("result-state")?.classList.remove("hidden");
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

    document.getElementById("res-lgpd-badge").textContent =
        `LGPD: ${lgpd.total_cpfs_mascarados} doc(s) e ${lgpd.total_nomes_mascarados} nome(s) mascarados`;

    document.getElementById("res-resumo-nlp").textContent = payload.resumo_nlp;
    document.getElementById("res-tese-recomendada").textContent = pred.tese_recomendada;
    document.getElementById("res-tendencia-juiz").textContent = pred.tendencia_juiz;
}

/* ==========================================================================
   7. Exportação de Relatório Analítico em PDF (RF-09)
   ========================================================================== */
export function exportarRelatorioPdfProcesso(idProcesso = null) {
    const targetId = idProcesso || state.lastAnalyzedProcessId || "proc-1004";
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
    document.getElementById("dj-orgao").textContent = data.orgao_julgador || "Vara Cível de Maceió";

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

function configurarModais() {
    const accountDialog = document.getElementById("login-modal");
    const title = document.getElementById("login-modal-title");
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

    function abrirConta(cadastro = false) {
        title.textContent = cadastro ? "Cadastro de advogado" : "Entrar na conta";
        loginForm.hidden = cadastro;
        registerForm.hidden = !cadastro;
        if (!accountDialog.open) accountDialog.showModal();
        (cadastro ? registerForm.elements.nome : loginEmail).focus();
    }

    document.getElementById("btn-open-login")?.addEventListener("click", () => abrirConta());
    document.getElementById("btn-open-register")?.addEventListener("click", () => abrirConta(true));
    document.getElementById("btn-switch-to-register")?.addEventListener("click", () => abrirConta(true));
    document.getElementById("btn-open-login-from-register")?.addEventListener("click", () => abrirConta());
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
            if (accountDialog.open) abrirConta();
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

            const nameEl = document.getElementById("sidebar-user-name");
            const oabEl = document.getElementById("sidebar-user-oab");
            const avatar = document.querySelector(".lawyer-avatar");
            if (nameEl) nameEl.textContent = res.usuario.nome;
            if (oabEl) oabEl.textContent = `OAB ${res.usuario.oab}`;
            if (avatar) avatar.textContent = res.usuario.nome.split(/\s+/).slice(0, 2)
                .map((parte) => [...parte][0]).join("").toUpperCase();
            loginSenha.value = "";
            mostrarFeedback(loginFeedback, "");
            showToast(`Bem-vindo(a), ${res.usuario.nome}.`);
            if (accountDialog.open && !loginForm.hidden) accountDialog.close();
        } catch (err) {
            mostrarFeedback(loginFeedback, err.message || "Não foi possível autenticar com as credenciais informadas.", true);
        } finally {
            loginSubmit.disabled = false;
        }
    });

    // Modal de Metodologia
    const methModal = document.getElementById("methodology-modal");
    document.getElementById("btn-open-methodology")?.addEventListener("click", () => {
        methModal?.classList.remove("hidden");
    });
    document.getElementById("btn-close-methodology")?.addEventListener("click", () => {
        methModal?.classList.add("hidden");
    });
}

/* ==========================================================================
   10. Visualizador Comparativo de Peças (Petição Inicial vs. Contestação)
   ========================================================================== */
function setupComparadorInteractions() {
    let fileInicial = null;
    let fileContestacao = null;
    let processando = false;
    let tesesAtuais = [];
    let teseSelecionada = null;

    const btnExecutar = document.getElementById("btn-executar-comparacao");
    const statusFeedback = document.getElementById("comparador-status-feedback");
    const infoInicial = document.getElementById("file-info-inicial");
    const infoContestacao = document.getElementById("file-info-contestacao");
    const inputInicial = document.getElementById("input-peticao-inicial");
    const inputContestacao = document.getElementById("input-contestacao");
    const dropInicial = document.getElementById("dropzone-inicial");
    const dropContestacao = document.getElementById("dropzone-contestacao");
    const btnSelectInicial = document.getElementById("btn-select-inicial");
    const btnSelectContestacao = document.getElementById("btn-select-contestacao");
    const btnDemo = document.getElementById("btn-demo-comparador");
    const selectDemo = document.getElementById("select-demo-comparador");
    const descricaoDemo = document.getElementById("comparador-demo-descricao");
    const statusDemo = document.getElementById("comparador-demo-status");
    const guiaDemo = document.getElementById("comparador-demo-guia");
    const tituloGuiaDemo = document.getElementById("comparador-demo-guia-titulo");
    const resultados = document.getElementById("comparador-resultados");
    const formComparador = document.getElementById("form-comparador-pecas");
    const botoesFiltro = Array.from(resultados.querySelectorAll(".chip-filter"));
    const feedbackFiltro = document.getElementById("comparador-filtro-feedback");

    function atualizarEstadoBotao() {
        if (btnExecutar) {
            btnExecutar.disabled = processando || !(fileInicial && fileContestacao);
        }
        btnDemo.disabled = processando;
        selectDemo.disabled = processando;
    }

    for (const [id, caso] of Object.entries(casosComparador)) {
        selectDemo.add(new Option(caso.titulo, id));
    }
    function atualizarDescricaoDemo() {
        descricaoDemo.textContent = casosComparador[selectDemo.value].descricao;
        statusDemo.textContent = "";
    }
    selectDemo.addEventListener("change", atualizarDescricaoDemo);
    atualizarDescricaoDemo();

    btnSelectInicial?.addEventListener("click", () => inputInicial?.click());
    btnSelectContestacao?.addEventListener("click", () => inputContestacao?.click());

    inputInicial?.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
            fileInicial = e.target.files[0];
            if (infoInicial) infoInicial.textContent = fileInicial.name;
            atualizarEstadoBotao();
        }
    });

    inputContestacao?.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
            fileContestacao = e.target.files[0];
            if (infoContestacao) infoContestacao.textContent = fileContestacao.name;
            atualizarEstadoBotao();
        }
    });

    // Drag & drop Inicial
    dropInicial?.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropInicial.classList.add("dragover");
    });
    dropInicial?.addEventListener("dragleave", () => dropInicial.classList.remove("dragover"));
    dropInicial?.addEventListener("drop", (e) => {
        e.preventDefault();
        dropInicial.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            fileInicial = e.dataTransfer.files[0];
            if (infoInicial) infoInicial.textContent = fileInicial.name;
            atualizarEstadoBotao();
        }
    });

    // Drag & drop Contestação
    dropContestacao?.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropContestacao.classList.add("dragover");
    });
    dropContestacao?.addEventListener("dragleave", () => dropContestacao.classList.remove("dragover"));
    dropContestacao?.addEventListener("drop", (e) => {
        e.preventDefault();
        dropContestacao.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            fileContestacao = e.dataTransfer.files[0];
            if (infoContestacao) infoContestacao.textContent = fileContestacao.name;
            atualizarEstadoBotao();
        }
    });

    btnDemo.addEventListener("click", async () => {
        const idCaso = selectDemo.value;
        const pecas = criarPecasDemonstrativas(idCaso);
        await executarComparacao(pecas.inicial, pecas.contestacao, casosComparador[idCaso]);
    });

    formComparador?.addEventListener("submit", async (e) => {
        e.preventDefault();
        await executarComparacao(fileInicial, fileContestacao);
    });

    async function executarComparacao(inicial, contestacao, casoDemo) {
        if (processando || !inicial || !contestacao) return;

        processando = true;
        atualizarEstadoBotao();
        resultados.classList.add("hidden");
        statusDemo.textContent = "";
        statusFeedback.textContent = "";
        const feedback = casoDemo ? statusDemo : statusFeedback;
        feedback.textContent = "Comparando as peças…";

        try {
            const data = await compararPecas(inicial, contestacao);
            renderizarResultadosComparacao(data, casoDemo);
            feedback.textContent = "Comparação concluída.";
        } catch (err) {
            console.error("Erro na comparação:", err);
            feedback.textContent = err instanceof TypeError
                ? "Não foi possível conectar à API. Verifique a conexão e tente novamente."
                : err.message || "Erro ao processar as peças.";
        } finally {
            processando = false;
            atualizarEstadoBotao();
        }
    }

    function renderizarResultadosComparacao(data, casoDemo) {
        resultados.classList.remove("hidden");
        guiaDemo.classList.toggle("hidden", !casoDemo);
        if (casoDemo) {
            tituloGuiaDemo.textContent = casoDemo.titulo;
            document.getElementById("comparador-demo-guia-texto").textContent = casoDemo.guia;
        }

        const cnjBadge = document.getElementById("badge-comparador-cnj");
        if (cnjBadge) {
            const rotulo = casoDemo ? "CNJ fictício" : "CNJ";
            cnjBadge.textContent = `${rotulo}: ${data.numero_processo || "Não identificado"}`;
        }

        document.getElementById("badge-comparador-motor").textContent =
            data.motor_analise === "gemini" ? "Gemini" : "Análise local";

        const scoreVal = document.getElementById("score-geral-valor");
        const score = data.score_geral_favorabilidade_autor_pct;
        const temScore = Number.isFinite(score);
        scoreVal.textContent = temScore ? `${score}%` : "Estimativa indisponível";
        scoreVal.classList.toggle("estimativa-indisponivel", !temScore);

        const resumoTexto = document.getElementById("resumo-controvertido-geral");
        if (resumoTexto) resumoTexto.textContent = data.resumo_controvertido_geral;

        // Atualizar chips
        const chipTotal = document.getElementById("chip-total-teses");
        if (chipTotal) chipTotal.textContent = data.total_teses;
        const chipConv = document.getElementById("chip-total-conv");
        if (chipConv) chipConv.textContent = data.total_convergencias;
        const chipDiv = document.getElementById("chip-total-div");
        if (chipDiv) chipDiv.textContent = data.total_divergencias;
        const chipOmiss = document.getElementById("chip-total-omiss");
        if (chipOmiss) chipOmiss.textContent = data.total_omissoes;
        const chipFn = document.getElementById("chip-total-fn");
        if (chipFn) chipFn.textContent = data.total_fatos_novos_defesa;

        // Renderizar Colunas
        renderizarColunaTexto("texto-peticao-inicial", data.texto_higienizado_autor || "");
        renderizarColunaTexto("texto-contestacao", data.texto_higienizado_reu || "");
        tesesAtuais = data.teses || [];
        teseSelecionada = null;
        renderizarFeedTeses(tesesAtuais);
        for (const botao of botoesFiltro) {
            atualizarBotaoFiltro(botao, (botao.dataset.filterStatus || botao.dataset.filterTipo) === "todos");
        }
        aplicarFiltros();

        if (document.getElementById("panel-comparador").hidden) return;
        if (casoDemo) tituloGuiaDemo.focus({ preventScroll: true });
        const reduzirMovimento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        resultados.scrollIntoView({ behavior: reduzirMovimento ? "instant" : "smooth", block: "start" });
    }

    function renderizarColunaTexto(elementId, fullText) {
        const container = document.getElementById(elementId);
        if (!container) return;
        container.replaceChildren();
        container.scrollTop = 0;

        const partes = fullText.split(/^\[PÁG (\d+)\][ \t]*\r?$/m);
        for (let i = 0; i < partes.length; i += 2) {
            const pagina = i === 0 ? "" : String(Number(partes[i - 1]));
            if (pagina) {
                const marcador = document.createElement("div");
                marcador.className = "page-marker-pill";
                marcador.textContent = `Página ${pagina}`;
                container.append(marcador);
            }

            const texto = partes[i].trim();
            if (!texto) continue;
            const paragrafo = document.createElement("p");
            paragrafo.className = "comparador-texto-pagina";
            paragrafo.dataset.pagina = pagina;
            paragrafo.textContent = texto;
            container.append(paragrafo);
        }

        if (!container.hasChildNodes()) {
            const mensagem = document.createElement("p");
            mensagem.textContent = "Nenhum texto disponível.";
            container.append(mensagem);
        }
    }

    function destacarTrecho(elementId, trecho, pagina) {
        const coluna = document.getElementById(elementId);
        const destaqueAnterior = coluna.querySelector(".highlight-snippet");
        if (destaqueAnterior) {
            const paragrafo = destaqueAnterior.parentNode;
            destaqueAnterior.replaceWith(destaqueAnterior.textContent);
            paragrafo.normalize();
        }
        if (!trecho?.trim()) return;

        const palavras = trecho.trim().split(/\s+/u);
        const padrao = palavras.map((palavra) => palavra.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("\\s+");
        const cita = new RegExp(padrao, "iu");
        const paginas = Array.from(coluna.querySelectorAll(".comparador-texto-pagina"));
        const paginaIndicada = paginas.find((item) => item.dataset.pagina === String(pagina));
        const candidatas = paginaIndicada
            ? [paginaIndicada, ...paginas.filter((item) => item !== paginaIndicada)]
            : paginas;

        for (const paragrafo of candidatas) {
            const correspondencia = cita.exec(paragrafo.textContent);
            if (!correspondencia) continue;

            const { index } = correspondencia;
            const range = document.createRange();
            range.setStart(paragrafo.firstChild, index);
            range.setEnd(paragrafo.firstChild, index + correspondencia[0].length);
            const destaque = document.createElement("mark");
            destaque.className = "highlight-snippet";
            range.surroundContents(destaque);

            const topoRelativo = destaque.getBoundingClientRect().top - coluna.getBoundingClientRect().top;
            const reduzirMovimento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
            coluna.scrollTo({
                top: coluna.scrollTop + topoRelativo - coluna.clientHeight / 2,
                behavior: reduzirMovimento ? "instant" : "smooth",
            });
            break;
        }
    }

    function renderizarFeedTeses(teses) {
        const feed = document.getElementById("feed-teses-comparacao");
        if (!feed) return;
        feed.innerHTML = "";

        const statusLabels = {
            convergente: "Convergente",
            divergente: "Divergente",
            fato_incontroverso_por_omissao: "Incontroverso (Art. 341 CPC)",
            fato_novo_ou_extintivo_reu: "Fato Novo Réu (Art. 350 CPC)",
        };

        const tipoLabels = {
            preliminar: "Preliminar",
            prejudicial_merito: "Prejudicial",
            fato_ou_valor: "Fato / Valor",
            merito: "Mérito",
            tutela_provisoria: "Tutela de Urgência",
            prova_e_onus: "Provas / Ônus",
            pedido_e_valor_causa: "Pedido / Valor",
        };

        teses.forEach((tese) => {
            const card = document.createElement("article");
            card.className = "tese-card";
            card.setAttribute("tabindex", "0");
            card.setAttribute("role", "article");
            card.setAttribute("aria-label", `${tese.id_tese}: ${tese.tema}`);
            card.dataset.idTese = tese.id_tese;
            card.dataset.status = tese.status;
            card.dataset.tipo = tese.tipo;

            const statusClass = `status-${tese.status}`;
            const statusLabel = statusLabels[tese.status] || tese.status;
            const tipoLabel = tipoLabels[tese.tipo] || tese.tipo;
            const probabilidade = tese.probabilidade_procedencia_pct;
            const estimativa = Number.isFinite(probabilidade)
                ? `<div class="tese-prob-bar-track" aria-hidden="true">
                        <div class="tese-prob-bar-fill" style="width: ${probabilidade}%;"></div>
                    </div>
                    <span class="tese-prob-label">${probabilidade}%</span>`
                : '<span class="estimativa-indisponivel">Estimativa indisponível</span>';

            card.innerHTML = `
                <div class="tese-header-row">
                    <span class="tese-id">${escapeHtml(tese.id_tese)}</span>
                    <span class="tese-tipo-badge">${escapeHtml(tipoLabel)}</span>
                </div>
                <div class="tese-title">${escapeHtml(tese.tema)}</div>
                <div>
                    <span class="tese-status-badge ${statusClass}">
                        <span>●</span>
                        <span>${escapeHtml(statusLabel)}</span>
                    </span>
                </div>
                <p class="card-subtitle">${[
                    Number.isInteger(tese.pagina_autor) && `Inicial, pág. ${tese.pagina_autor}`,
                    Number.isInteger(tese.pagina_reu) && `Contestação, pág. ${tese.pagina_reu}`,
                ].filter(Boolean).join(" · ")}</p>
                <div class="tese-prob-row">
                    <span class="tese-prob-title">Êxito do autor</span>
                    ${estimativa}
                </div>
                <p class="tese-prob-fundamentacao">${escapeHtml(tese.fundamentacao_preditiva)}</p>
                <div class="tese-impacto-alert" role="note">
                    <strong>Orientação:</strong> ${escapeHtml(tese.impacto_processual)}
                </div>
            `;

            card.addEventListener("click", () => selecionarTese(tese));
            card.addEventListener("keydown", (e) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    selecionarTese(tese);
                }
            });

            feed.appendChild(card);
        });
    }

    function selecionarTese(tese) {
        teseSelecionada = tese || null;
        resultados.querySelectorAll(".tese-card").forEach((c) => {
            c.classList.toggle("active-tese", c.dataset.idTese === tese?.id_tese);
        });

        destacarTrecho("texto-peticao-inicial", tese?.trecho_autor, tese?.pagina_autor);
        destacarTrecho("texto-contestacao", tese?.trecho_reu, tese?.pagina_reu);
    }

    function atualizarBotaoFiltro(botao, ativo) {
        botao.classList.toggle("active", ativo);
        botao.setAttribute("aria-pressed", String(ativo));
    }

    function aplicarFiltros() {
        const status = resultados.querySelector("[data-filter-status].active").dataset.filterStatus;
        const tipo = resultados.querySelector("[data-filter-tipo].active").dataset.filterTipo;
        const visiveis = tesesAtuais.filter((tese) =>
            (status === "todos" || tese.status === status) && (tipo === "todos" || tese.tipo === tipo),
        );
        const idsVisiveis = new Set(visiveis.map((tese) => tese.id_tese));
        resultados.querySelectorAll(".tese-card").forEach((card) => {
            card.classList.toggle("hidden", !idsVisiveis.has(card.dataset.idTese));
        });
        feedbackFiltro.textContent = visiveis.length
            ? `${visiveis.length} de ${tesesAtuais.length} teses exibidas.`
            : "Nenhuma tese encontrada para os filtros selecionados.";
        if (!visiveis.includes(teseSelecionada)) selecionarTese(visiveis[0]);
    }

    for (const botao of botoesFiltro) {
        botao.addEventListener("click", () => {
            const grupo = botao.closest(".filter-group");
            for (const item of grupo.querySelectorAll(".chip-filter")) {
                atualizarBotaoFiltro(item, item === botao);
            }
            aplicarFiltros();
        });
    }
}

/* ==========================================================================
   9. Inicialização de Eventos da Aplicação
   ========================================================================== */
function initApp() {
    updateSavedCounterUI();
    setupTabKeyboardNavigation();
    configurarModais();

    // Abas principais
    document.getElementById("btn-historico")?.addEventListener("click", () => switchTab("historico"));
    document.getElementById("btn-dashboard")?.addEventListener("click", () => switchTab("dashboard"));
    document.getElementById("btn-upload")?.addEventListener("click", () => switchTab("upload"));
    document.getElementById("btn-comparador")?.addEventListener("click", () => switchTab("comparador"));

    // Inicialização do módulo de comparação de peças
    setupComparadorInteractions();

    // Ações de navegação contextual (Seção 7.3)
    document.getElementById("btn-go-jurimetria-from-search")?.addEventListener("click", () => {
        switchTab("dashboard");
        showToast("Exibindo indicadores jurimétricos do acervo consultado.");
    });

    document.getElementById("btn-overview-ver-todos")?.addEventListener("click", () => {
        switchTab("historico");
    });

    document.getElementById("btn-nav-saved-decisions")?.addEventListener("click", () => {
        const selectCol = document.getElementById("filtro-colecao");
        if (selectCol) selectCol.value = "salvos";
        switchTab("historico");
        carregarBaseConhecimento(1);
        showToast("Exibindo decisões salvas na biblioteca do escritório.");
    });

    document.getElementById("btn-nav-export-pdf")?.addEventListener("click", () => {
        exportarRelatorioPdfProcesso();
    });

    document.getElementById("btn-topbar-new-analysis")?.addEventListener("click", () => {
        switchTab("upload");
        alternarModoUpload("pdf");
    });

    // Alternância entre Cartões de Decisão e Tabela Comparativa
    document.getElementById("btn-view-cards")?.addEventListener("click", () => alternarVisaoResultados("cards"));
    document.getElementById("btn-view-table")?.addEventListener("click", () => alternarVisaoResultados("table"));

    // Atalhos de pesquisas recentes (Seção 9.4)
    document.querySelectorAll(".recent-chip").forEach((chip) => {
        chip.addEventListener("click", () => {
            const qTema = chip.getAttribute("data-quick-tema") || "";
            const qBusca = chip.getAttribute("data-quick-busca") || "";
            const elTema = document.getElementById("filtro-tema");
            const elBusca = document.getElementById("filtro-busca");
            if (elTema) elTema.value = qTema;
            if (elBusca) elBusca.value = qBusca;
            carregarBaseConhecimento(1);
        });
    });

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
    document.getElementById("btn-header-export-pdf")?.addEventListener("click", () => {
        exportarRelatorioPdfProcesso();
    });
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

    configurarFormularioJulgado({
        obterDetalhes: () => state.currentDrawerPayload,
        aoSalvar: (detalhes, edicao) => {
            if (edicao) exibirDrawerProcesso(detalhes);
            carregarBaseConhecimento(edicao ? state.paginaAtual : 1);
            carregarDashboard();
            showToast(edicao ? "Julgado atualizado." : "Julgado cadastrado.");
        },
    });

    // Atalho global Escape para fechar janelas sobrepostas
    window.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !document.querySelector("dialog[open]")) {
            fecharDrawerProcesso();
            document.getElementById("methodology-modal")?.classList.add("hidden");
        }
    });

    verificarConectividadeApi();
    carregarDashboard();
    switchTab("historico");
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initApp);
} else {
    initApp();
}
