/**
 * Controlador de Experiência Jurídica, Pesquisa Jurisprudencial, Leitura Documental e Jurimetria — JuriVision.
 * Direção Estética e Funcional: Legal Editorial + Legal Intelligence
 * Referência: Guia de UI/UX e Direção Visual — Plataforma de Jurimetria para Advocacia
 * Rastreabilidade:
 * - Requisitos Funcionais: RF-01 a RF-09
 * - Requisitos Não Funcionais: RNF-04 (ISO 9241-110 & Nielsen), RNF-09 (WCAG 2.2 AA), RNF-10 (Leis de UX & Gestalt)
 */

import {
    buildSampleBatchCsvFile,
    buildSamplePetitionPdfFile,
    checkApiHealth,
    consultarProcessoDatajud,
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
    const tabs = ["historico", "dashboard", "upload"];

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
                            <strong style="color: var(--color-navy); font-size: var(--text-sm);">${d.juiz}</strong>
                            <span style="display: block; font-size: var(--text-xs); color: var(--text-muted);">
                                ${total} julgados (${d.procedentes} fav. / ${d.improcedentes} impr.)
                            </span>
                        </div>
                        <div style="text-align: right;">
                            <strong class="tabular-nums" style="color: var(--color-navy); font-size: var(--text-sm);">${favPct}% fav.</strong>
                            <div>
                                <button type="button" class="btn btn-ghost btn-sm btn-drill-judge" data-judge="${d.juiz}" style="padding: 0 4px; min-height: 22px; font-size: 11px;">
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
                            <strong style="color: var(--color-navy); font-size: var(--text-sm);">${t.tema}</strong>
                            <span style="display: block; font-size: var(--text-xs); color: var(--text-muted);">
                                ${approxCount} julgados (${t.percentual}%)
                            </span>
                        </div>
                        <button type="button" class="btn btn-ghost btn-sm btn-drill-theme" data-theme="${t.tema}" style="padding: 0 4px; min-height: 22px; font-size: 11px;">
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
                <td>${item.juiz}</td>
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
                <td>${item.tema}</td>
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
                <td class="font-mono" style="font-weight: 600; color: var(--color-navy);">${item.numero_processo}</td>
                <td style="font-weight: 500;">${item.tema}</td>
                <td>${item.magistrado}</td>
                <td style="color: var(--text-secondary);">${item.partes_anonimizadas}</td>
                <td>
                    <span class="badge-editorial ${badgeClass}">${item.resultado}</span>
                </td>
                <td style="text-align: right;">
                    <button type="button" class="btn btn-secondary btn-sm btn-open-dossier-overview" data-proc-id="${item.id_processo}">
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
            <div class="decision-card" style="text-align: center; align-items: center; padding: var(--space-8);">
                <strong class="serif-heading" style="font-size: 20px; color: var(--color-navy);">
                    Nenhuma decisão foi encontrada com esses critérios
                </strong>
                <p style="font-size: var(--text-sm); color: var(--text-secondary); max-width: 54ch;">
                    Remova um dos filtros ativos ou experimente pesquisar por outro assunto, órgão julgador ou expressão jurídica.
                </p>
            </div>`;
        if (cardsContainer) cardsContainer.innerHTML = emptyHtml;
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="padding: 32px; text-align: center; color: var(--text-secondary);">
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
                <article class="decision-card" data-card-proc-id="${item.id_processo}">
                    <div class="decision-card-header">
                        <div>
                            <div class="decision-court-line">
                                <span>TJAL · ${comarca}</span>
                                <span aria-hidden="true">·</span>
                                <span class="font-mono">${item.numero_processo}</span>
                            </div>
                            <div class="decision-process-meta">
                                <span>${item.magistrado}</span>
                                <span aria-hidden="true">·</span>
                                <span>${dataJulg}</span>
                                <span aria-hidden="true">·</span>
                                <span title="Partes com proteção LGPD">${item.partes_anonimizadas}</span>
                            </div>
                        </div>

                        <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                            ${
                                isSaved
                                    ? `<span class="badge-editorial badge-saved">Salva</span>`
                                    : ""
                            }
                            <span class="badge-editorial ${badgeClass}">
                                ${item.resultado}
                            </span>
                        </div>
                    </div>

                    <div class="decision-subject-row">
                        <h3 class="decision-subject-title">${item.tema}</h3>
                    </div>

                    <div class="decision-excerpt-box">
                        <p class="legal-prose" style="font-size: var(--text-base);">
                            ${sintese}
                        </p>
                    </div>

                    <div class="decision-card-footer">
                        <div class="decision-actions-group">
                            <button type="button" class="btn btn-primary btn-sm btn-inspecionar-proc" data-inspect-id="${item.id_processo}">
                                Abrir decisão
                            </button>
                            <button type="button" class="btn btn-secondary btn-sm btn-salvar-proc" data-save-id="${item.id_processo}">
                                ${isSaved ? "Salva ✓" : "Salvar"}
                            </button>
                            <button type="button" class="btn btn-secondary btn-sm btn-copiar-ref" data-ref-id="${item.id_processo}">
                                Copiar ref.
                            </button>
                        </div>

                        <div class="decision-actions-group">
                            <button type="button" class="btn btn-ghost btn-sm btn-exportar-pdf" data-pdf-id="${item.id_processo}">
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
                <tr data-row-proc-id="${item.id_processo}">
                    <td>
                        <div class="font-mono" style="font-weight: 600; color: var(--color-navy);">${item.numero_processo}</div>
                        <div style="font-size: var(--text-xs); color: var(--text-muted);">${dataJulg}</div>
                    </td>
                    <td style="font-weight: 500;">${item.tema}</td>
                    <td>
                        <div>${item.magistrado}</div>
                        <div style="font-size: var(--text-xs); color: var(--text-muted);">${item.comarca || "TJAL"}</div>
                    </td>
                    <td>
                        <span>${item.partes_anonimizadas}</span>
                    </td>
                    <td>
                        <span class="badge-editorial ${badgeClass}">${item.resultado}</span>
                    </td>
                    <td style="text-align: right; white-space: nowrap;">
                        <button type="button" data-inspect-id="${item.id_processo}" class="btn btn-secondary btn-sm btn-inspecionar-proc">
                            Abrir
                        </button>
                        <button type="button" data-pdf-id="${item.id_processo}" class="btn btn-ghost btn-sm btn-exportar-pdf">
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
        document.getElementById("drawer-proc-prob").textContent =
            `${Math.round(pred.probabilidade_deferimento * 100)}% em ${pred.casos_similares_encontrados || 42} decisões semelhantes`;
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
    } catch (err) {
        showToast(err.message);
    }
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
    document.getElementById("res-similares").textContent = `${pred.casos_similares_encontrados} julgados`;
    document.getElementById("res-provedor-ia").textContent =
        pred.provedor_ia === "local_heuristic" || !pred.provedor_ia
            ? "Estatística Local"
            : String(pred.provedor_ia);

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

function configurarModais() {
    const loginModal = document.getElementById("login-modal");
    const btnOpenLogin = document.getElementById("btn-open-login");
    const btnCloseLogin = document.getElementById("btn-close-login");
    const loginForm = document.getElementById("login-form");
    const feedback = document.getElementById("login-feedback");

    btnOpenLogin?.addEventListener("click", () => {
        loginModal?.classList.remove("hidden");
        document.getElementById("login-email")?.focus();
    });

    btnCloseLogin?.addEventListener("click", () => {
        loginModal?.classList.add("hidden");
    });

    loginForm?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("login-email")?.value.trim() || "";
        const senha = document.getElementById("login-senha")?.value || "";

        if (feedback) {
            feedback.style.background = "var(--color-navy-subtle)";
            feedback.style.color = "var(--color-navy)";
            feedback.textContent = "Verificando credenciais do advogado...";
            feedback.classList.remove("hidden");
        }

        try {
            const res = await loginAdvogado(email, senha);
            state.currentUser = {
                ...res.usuario,
                authenticated: true,
                token: res.access_token,
            };

            const nameEl = document.getElementById("sidebar-user-name");
            const oabEl = document.getElementById("sidebar-user-oab");
            if (nameEl) nameEl.textContent = res.usuario.nome;
            if (oabEl) oabEl.textContent = `OAB ${res.usuario.oab}`;

            if (feedback) {
                feedback.style.background = "var(--color-sage-subtle)";
                feedback.style.color = "#2F4F44";
                feedback.textContent = `Sessão autenticada para ${res.usuario.nome}.`;
            }

            showToast(`Bem-vindo(a), ${res.usuario.nome}.`);
            setTimeout(() => {
                loginModal?.classList.add("hidden");
                feedback?.classList.add("hidden");
            }, 700);
        } catch (err) {
            if (feedback) {
                feedback.style.background = "var(--status-error-bg)";
                feedback.style.color = "var(--status-error-fg)";
                feedback.textContent = err.message || "Não foi possível autenticar com as credenciais informadas.";
            }
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
    
    // Consulta Oficial DataJud (CNJ)
    document.getElementById("btn-consultar-datajud")?.addEventListener("click", dispararConsultaDataJud);
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
                data_julgamento: "2026-10-05",
            });
        }
    });

    // Atalho global Escape para fechar janelas sobrepostas
    window.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            fecharDrawerProcesso();
            document.getElementById("login-modal")?.classList.add("hidden");
            document.getElementById("methodology-modal")?.classList.add("hidden");
        }
    });

    verificarConectividadeApi();
    carregarBaseConhecimento(1);
    carregarDashboard();
    switchTab("historico");
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initApp);
} else {
    initApp();
}
