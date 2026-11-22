import { preverAnonimizacao, salvarProcesso } from "../services/api.js";

export function configurarFormularioJulgado({ obterDetalhes, aoSalvar }) {
    const porId = (id) => document.getElementById(id);
    const modal = porId("julgado-modal");
    const form = porId("julgado-form");
    if (!modal || !form) return;
    const erro = porId("julgado-erro");
    const previaStatus = porId("julgado-previa-status");
    const previaConteudo = porId("julgado-previa-conteudo");
    const botaoSalvar = porId("btn-salvar-julgado");
    const botaoCancelar = porId("btn-cancelar-julgado");
    const camposPrivados = ["autor", "reu", "resumo"];
    let idProcesso;
    let timer;
    let consulta;
    let salvando = false;

    function cancelarPrevia() {
        clearTimeout(timer);
        consulta?.abort();
    }

    function atualizarPrevia() {
        cancelarPrevia();
        previaConteudo.hidden = true;
        const dados = Object.fromEntries(camposPrivados.map((nome) => [
            nome, form.elements.namedItem(nome).value.trim(),
        ]));
        if (!Object.values(dados).some(Boolean)) {
            previaStatus.textContent = "Preencha as partes ou a síntese para ver a prévia.";
            return;
        }

        previaStatus.textContent = "Atualizando prévia…";
        const controller = new AbortController();
        consulta = controller;
        timer = setTimeout(async () => {
            try {
                const previa = await preverAnonimizacao(dados, controller.signal);
                if (controller.signal.aborted) return;
                for (const parte of ["autor", "reu"]) {
                    porId(`julgado-previa-${parte}`).textContent =
                        dados[parte] ? previa.partes_anonimizadas[parte] : "—";
                }
                porId("julgado-previa-resumo").textContent = previa.resumo;
                previaConteudo.hidden = false;
                previaStatus.textContent = "Prévia atualizada.";
            } catch {
                if (!controller.signal.aborted) {
                    previaStatus.textContent = "Prévia indisponível. O servidor reaplica a anonimização ao salvar.";
                }
            }
        }, 350);
    }

    function abrir(detalhes = null) {
        form.reset();
        erro.textContent = "";
        idProcesso = detalhes?.id_processo;
        porId("julgado-titulo").textContent = idProcesso ? "Editar julgado" : "Cadastrar julgado";
        if (detalhes) {
            const meta = detalhes.metadados_extraidos;
            const valores = {
                numero_processo: meta.numero_processo,
                tema: meta.tema,
                magistrado: meta.magistrado,
                comarca: meta.comarca,
                autor: meta.partes_anonimizadas.autor,
                reu: meta.partes_anonimizadas.reu,
                resumo: detalhes.resumo_nlp,
                resultado: detalhes.resultado,
                data_julgamento: detalhes.data_julgamento ?? "",
            };
            for (const [nome, valor] of Object.entries(valores)) {
                form.elements.namedItem(nome).value = valor;
            }
        }
        modal.showModal();
        atualizarPrevia();
    }

    porId("btn-novo-julgado")?.addEventListener("click", () => abrir());
    porId("btn-editar-julgado")?.addEventListener("click", () => {
        const detalhes = obterDetalhes();
        if (detalhes) abrir(detalhes);
    });
    botaoCancelar?.addEventListener("click", () => modal.close());
    modal.addEventListener("cancel", (event) => {
        if (salvando) event.preventDefault();
    });
    modal.addEventListener("close", () => {
        cancelarPrevia();
        form.reset();
        previaConteudo.hidden = true;
        for (const nome of camposPrivados) porId(`julgado-previa-${nome}`).textContent = "";
    });
    form.addEventListener("input", (event) => {
        erro.textContent = "";
        if (camposPrivados.includes(event.target.name)) atualizarPrevia();
    });
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (salvando) return;

        const dados = Object.fromEntries([...new FormData(form)].map(([nome, valor]) => [nome, valor.trim()]));
        const campoCurto = [...form.elements].find((campo) =>
            campo.minLength > 0 && (campo.required || dados[campo.name]) && dados[campo.name].length < campo.minLength
        );
        if (campoCurto) {
            erro.textContent = `Revise o campo “${campoCurto.labels[0].textContent}”. Informe ao menos ${campoCurto.minLength} caracteres.`;
            campoCurto.focus();
            return;
        }
        if (!dados.comarca) delete dados.comarca;
        dados.data_julgamento ||= null;

        erro.textContent = "";
        salvando = true;
        const controles = [...form.elements];
        controles.forEach((campo) => { campo.disabled = true; });
        botaoSalvar.textContent = "Salvando…";
        let detalhes;
        try {
            detalhes = await salvarProcesso(dados, idProcesso);
        } catch (error) {
            erro.textContent = error instanceof TypeError
                ? "Não foi possível conectar ao servidor. Tente novamente."
                : error.message;
        } finally {
            salvando = false;
            controles.forEach((campo) => { campo.disabled = false; });
            botaoSalvar.textContent = "Salvar julgado";
        }
        if (detalhes) {
            modal.close();
            aoSalvar(detalhes, Boolean(idProcesso));
        } else {
            botaoSalvar.focus();
        }
    });
}
