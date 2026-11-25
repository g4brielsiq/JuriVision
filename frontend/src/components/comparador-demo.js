export const casosComparador = {
    voo: {
        titulo: "Atraso de voo e despesas de hospedagem",
        descricao: "As partes concordam sobre a data e a despesa com hotel, mas divergem sobre a assistência prestada. A defesa atribui o atraso ao mau tempo.",
        guia: "Comece por Convergentes e confira a data e o valor nas duas peças. Em Divergentes, compare as versões sobre a assistência. Depois procure a inversão do ônus em Omissões e a alegação de mau tempo em Fato Novo Defesa.",
        processo: "0000001-00.2026.8.02.0001",
        inicial: [
            [
                "DOS FATOS",
                "Em 18/07/2026, o voo de Maceió para Recife atrasou onze horas.",
                "A autora esperou no aeroporto até o encerramento do embarque.",
                "O bilhete e o aviso de reacomodação registram a alteração.",
            ],
            [
                "DO MÉRITO",
                "A ausência de voucher constituiu falha na assistência material.",
                "A diária de hotel custou R$ 480,00, conforme recibo anexado.",
                "O extrato do cartão registra a despesa na mesma noite.",
                "A autora pede ressarcimento da diária e reparação por dano moral.",
            ],
            [
                "DAS PROVAS E DOS PEDIDOS",
                "Pede-se a inversão do ônus da prova sobre a oferta de voucher.",
                "Requer-se a exibição do registro de atendimento no aeroporto.",
                "A autora indica o bilhete, o aviso de alteração e o recibo do hotel.",
            ],
        ],
        contestacao: [
            [
                "DOS FATOS ADMITIDOS",
                "A companhia confirma que o voo de 18/07/2026 atrasou onze horas.",
                "A companhia reconhece a despesa de R$ 480,00 com a diária de hotel.",
                "O relatório do embarque confirma o horário da reacomodação.",
            ],
            [
                "DO MÉRITO",
                "A ré alega inexistência de falha e diz que ofertou voucher no balcão.",
                "O voucher, segundo a ré, estava disponível até a meia-noite.",
                "A ré sustenta que o atraso e a espera não configuram dano moral.",
            ],
            [
                "DO EVENTO METEOROLÓGICO",
                "A ré alega força maior por fechamento temporário da pista.",
                "A defesa indica boletim meteorológico e aviso operacional.",
                "Requer que o juízo examine os registros da operação do voo.",
            ],
        ],
    },
    cobranca: {
        titulo: "Cobrança após cancelamento de assinatura",
        descricao: "A consumidora contesta um débito após pedir o cancelamento. A empresa discorda da data e do valor e alega que outra integrante do grupo recebeu a cobrança.",
        guia: "Abra Divergentes e confira a data do cancelamento e os valores nos trechos destacados. Em Fato Novo Defesa, combine o filtro com Preliminares para localizar a alegação de ilegitimidade passiva.",
        processo: "0000002-00.2026.8.02.0001",
        inicial: [
            [
                "DOS FATOS",
                "A autora diz ter solicitado o cancelamento em 04/08/2026.",
                "O protocolo C-104 registra o contato pelo chat da plataforma.",
                "Mesmo após o pedido, um débito apareceu na fatura do cartão.",
            ],
            [
                "DO MÉRITO",
                "A autora atribui a cobrança a uma falha no cancelamento.",
                "A fatura registra um débito de R$ 299,90 após o cancelamento.",
                "O comprovante identifica a marca exibida no extrato do cartão.",
            ],
            [
                "DAS PROVAS E DOS PEDIDOS",
                "Pede-se inversão do ônus da prova para acesso aos registros do chat.",
                "A autora pede restituição do débito e reparação por dano moral.",
                "Indica como provas o protocolo e a fatura do cartão.",
            ],
        ],
        contestacao: [
            [
                "DO POLO PASSIVO",
                "A ré alega ilegitimidade passiva e aponta a gestora de assinaturas.",
                "Segundo a defesa, essa empresa é a emissora da cobrança.",
                "A ré indica o recibo comercial para verificar a titularidade.",
            ],
            [
                "DO CANCELAMENTO E DA COBRANÇA",
                "A ré alega excesso no valor de R$ 299,90 e aponta débito de R$ 199,90.",
                "A ré impugna a data do cancelamento e indica 14/08/2026.",
                "A defesa aponta o histórico da assinatura e o recibo mensal.",
            ],
            [
                "DO MÉRITO E DAS PROVAS",
                "A ré alega inexistência de falha na cobrança da mensalidade.",
                "A ré alega que não cabe inversão do ônus da prova neste caso.",
                "Requer o exame dos registros de atendimento e de faturamento.",
            ],
        ],
    },
};

// Usa literais ASCII com escapes octais para que offsets e tamanhos sejam em bytes.
function literalPdf(texto) {
    return texto.replace(/[^\x20-\x7e]|[()\\]/gu, (caractere) =>
        `\\${caractere.charCodeAt(0).toString(8).padStart(3, "0")}`,
    );
}

function criarPdfPeca(nome, titulo, processo, paginas) {
    const objetos = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ];
    const referenciasPaginas = paginas.map((linhas) => {
        const idPagina = objetos.length + 1;
        const idConteudo = idPagina + 1;
        const conteudo = [
            "BT /F1 12 Tf 50 770 Td 22 TL",
            ...[titulo, `Processo fictício: ${processo}`, "", ...linhas]
                .map((linha) => `(${literalPdf(linha)}) Tj T*`),
            "ET\n",
        ].join("\n");
        objetos.push(
            `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents ${idConteudo} 0 R >>`,
            `<< /Length ${conteudo.length} >>\nstream\n${conteudo}endstream`,
        );
        return `${idPagina} 0 R`;
    });
    objetos[1] = `<< /Type /Pages /Kids [${referenciasPaginas.join(" ")}] /Count ${paginas.length} >>`;

    let pdf = "%PDF-1.4\n";
    const offsets = objetos.map((objeto, index) => {
        const offset = pdf.length;
        pdf += `${index + 1} 0 obj\n${objeto}\nendobj\n`;
        return `${String(offset).padStart(10, "0")} 00000 n \n`;
    });
    const inicioXref = pdf.length;
    const tamanho = objetos.length + 1;
    pdf += `xref\n0 ${tamanho}\n0000000000 65535 f \n${offsets.join("")}`;
    pdf += `trailer\n<< /Size ${tamanho} /Root 1 0 R >>\nstartxref\n${inicioXref}\n%%EOF\n`;
    return new File([pdf], nome, { type: "application/pdf" });
}

export function criarPecasDemonstrativas(idCaso) {
    const { processo, inicial, contestacao } = casosComparador[idCaso];
    return {
        inicial: criarPdfPeca(`peticao_inicial_${idCaso}.pdf`, "PETIÇÃO INICIAL", processo, inicial),
        contestacao: criarPdfPeca(`contestacao_${idCaso}.pdf`, "CONTESTAÇÃO", processo, contestacao),
    };
}
