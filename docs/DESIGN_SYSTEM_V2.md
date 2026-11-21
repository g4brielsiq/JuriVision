# Guia de Estilo v2 — JuriVision (Repertório Jurídico Contemporâneo)

## 1. Direção Visual
O JuriVision é uma ferramenta de pesquisa jurisprudencial, jurimetria e análise de petições para advogados (acervo TJAL).
- **Estética:** repertório jurídico editorial + jornalismo de dados sóbrio (pense em uma publicação jurídica moderna e no *Financial Times* aplicados a software).
- **Princípio central:** substituir "caixas dentro de caixas" e barras grossas coloridas por **superfícies calmas, filetes horizontais finos (`1px`), espaço em branco e contraste tipográfico**.
- **Stack obrigatória:** HTML5 semântico + CSS puro (`frontend/src/components/design-tokens.css`) + ES Modules (`frontend/src/app.js`) + Chart.js. Sem Tailwind CDN, sem FontAwesome, sem migração de framework.

---

## 2. Paleta Calibrada (100% compatível com `test_frontend_accessibility.py`)
Preservar `--color-navy: #20364A` e `--bg-ivory: #F6F4EF`, mas **harmonizar todos os neutros para temperatura quente** (eliminando os cinzas azulados frios `#F3F5F6` / `#E3E6E8` e os estilos inline `#475569` / `#e2e8f0`).

### Base e superfícies
- `--bg-ivory: #F6F4EF` (canvas principal — obrigatório nos testes)
- `--bg-surface: #FFFFFF` (folhas de leitura, formulários e superfícies elevadas)
- `--bg-auxiliary: #EFECE5` (papel/pedra quente: sidebar clara, cabeçalhos de tabela, hover sutil)
- `--bg-hover: #E7E3DA`
- `--border-default: #DFDBD2` (filetes quentes e discretos)
- `--border-strong: #C9C3B8` (contornos de input e foco neutro)

### Tinta e marca
- `--color-navy: #20364A` (obrigatório nos testes — ação primária, item ativo, títulos de destaque)
- `--color-navy-hover: #162635`
- `--color-navy-subtle: #EAEFF3`
- `--text-primary: #1F2933`
- `--text-secondary: #525D68`
- `--text-muted: #6C757E` (manter contraste >= 4.5:1 sobre `#FFFFFF` e `#F6F4EF`)

### Acentos comedidos (uso estritamente funcional)
- `--color-sage: #3F6356` | `--color-sage-subtle: #EEF4F1` | `--color-sage-border: #C3D6CE` (favorável / procedente)
- `--color-gold: #9A7B4F` | `--color-gold-subtle: #F8F3E8` | `--color-gold-border: #E0D3B8` (decisão salva / nota metodológica)
- `--status-error-fg: #942628` | `--status-error-bg: #FCF1F1` | `--status-error-border: #E8C1C2` (improcedente / alerta real)

---

## 3. Tipografia
- **Títulos de página, nomes de tese/matéria e leitura de decisões:** `Source Serif 4` (obrigatório nos testes — dar presença real a ela nos títulos de decisões, títulos de seção e números de jurimetria).
- **Interface, navegação, botões e tabelas:** substituir `Inter` por `IBM Plex Sans` ou `DM Sans` (pesos 400, 500, 600 — mais editorial e humana que a `Inter` padrão de IA).
- **Identificadores jurídicos e dados numéricos:** `JetBrains Mono` (com `tabular-nums`) usada exclusivamente para números CNJ (`0088210-12.2026.8.02.0001`), datas, percentuais e denominadores (`7/10`).

---

## 4. Navegação e Shell (limpando a sidebar pesada sem quebrar contratos)
- **Sidebar clara e silenciosa (236px, fundo `#EFECE5`, borda direita `1px solid #DFDBD2`):** abandonar o bloco azul-marinho escuro pesado com caixas translúcidas.
  - **Marca:** tipografia limpa `JuriVision` em `Source Serif 4` 21px semibold (`#20364A`) + linha discreta `Acervo · Jurimetria` em `IBM Plex Sans` 11.5px (`#525D68`). **Remover o quadrado `.brand-monogram` com a letra "J" e bordinha dourada.**
  - **Itens de navegação:** texto limpo em `#1F2933`; item ativo destacado por tinta `#20364A` semibold + fundo `#E5E0D6` sutil (ou pequeno traço lateral de 2px apenas no item ativo). Remover ícones decorativos repetitivos da seção secundária e remover `.nav-badge` em pill chamativa (mostrar contagem como número tabular discreto à direita).
  - **Bloco de acervo (`sidebar-saved-desc`):** remover a caixa com borda e bolinha verde (`dot-success`). Manter como nota discreta no rodapé da navegação (`Acervo TJAL · Maceió`), preservando a classe `sidebar-saved-desc` exigida pelo teste.
  - **Perfil do advogado:** linha compacta no rodapé sem avatar circular colorido gigante e sem caixa pesada.
- **Cabeçalho de contexto (`.context-header`):** manter visível (exigido pelo teste), mas integrá-lo ao fundo `#F6F4EF` com altura enxuta (`48px`) e filete inferior `1px solid #DFDBD2` — eliminando a "barra branca grossa" que compete com o título da página. Remover ações duplicadas no topo quando já existem na navegação.

---

## 5. Regras Específicas por Tela

### Tela 1 (Âncora) — Pesquisa de Precedentes (`#panel-historico`)
- **Desempilhar o topo:** remover `border-top: 3px` e sombra da `.search-chamber`. Tratar a busca como um bloco leve e integrado: campo de busca + botão `Pesquisar` **na mesma linha principal** (inline), com os 4 filtros (`filtro-tema`, `filtro-juiz`, `filtro-ordenacao`, `filtro-colecao`) organizados em uma faixa compacta e silenciosa logo abaixo (preservando todos os `<label for="...">` e `id="..."`).
- **Ação `DataJud (CNJ)`:** posicionar discretamente ao lado da busca ou na linha de ações secundárias com ícone coerente de documento/consulta (nunca ícone de *Play*).
- **Corrigir `#datajud-result-box`:** remover todos os `style="..."` inline com cores Tailwind frias e `border-left: 4px`, estilizando-o com os tokens quentes do guia.
- **Eliminar caixas redundantes acima da lista:**
  - `.results-scope-toolbar` deixa de ser um card branco com borda e vira uma linha editorial simples (`10 decisões encontradas` à esquerda | `Cartões / Tabela` à direita) sobre o fundo `#F6F4EF`.
  - `.active-filters-strip` só aparece com destaque visual quando houver filtros aplicados pelo usuário (ou integra-se sutilmente à linha de resultados, sem virar uma faixa cinza vazia permanente).
- **Lista de Decisões (`.decisions-list` e `.decision-card`) — cara de repertório jurídico real:**
  - **ZERO `border-left: 3px` no card e ZERO `border-left: 2px` dourado no resumo.**
  - **ZERO caixa cinza dentro do card** (`.decision-excerpt-box` perde fundo cinza e borda esquerda; vira texto de ementa/síntese direto em leitura confortável `max-width: 72ch`).
  - **ZERO 3 divisórias internas no mesmo card** (`border-bottom` no header + box no meio + `border-top` no footer). Em vez disso: lista contínua dentro de uma superfície branca limpa `#FFFFFF` com borda `1px solid #DFDBD2` e itens separados por filete `1px solid #DFDBD2` (ou cartões bem planos sem sombra e sem listras laterais), estruturados em 3 respiros claros:
    1. Metadados em linha compacta: `TJAL · Vara` · `CNJ` em `JetBrains Mono` · `Magistrado` · `Data` + badge discreto de resultado à direita.
    2. Título da matéria/tese em `Source Serif 4` 19px (`#20364A`).
    3. Síntese limpa + ações discretas no rodapé (apenas `Ler decisão` com peso principal; `Salvar` e `PDF` como ações textuais sutis).

### Tela 2 — Análise Jurimétrica (`#panel-dashboard`)
- **Escopo metodológico (`.methodology-scope-banner`):** remover `border-left: 4px` e o card branco pesado; transformar em linha discreta de metadados (`Varas Cíveis e Trabalhistas de Maceió (TJAL) · 2025–2026 · Dados anonimizados (LGPD)`).
- **Faixa de indicadores (`.indicators-grid`):** substituir os 4 cards soltos com sombra por uma **faixa contínua de métricas** (`background: #FFFFFF`, `border: 1px solid #DFDBD2`) dividida internamente por filetes verticais de `1px`. Tratar o 4º indicador (`Classificação`) com sobriedade tipográfica para não competir visualmente com os números percentuais.
- **Gráficos (Chart.js em `app.js`):** atualizar a fonte dos gráficos para `IBM Plex Sans`/`DM Sans`, usar `#20364A` (favoráveis) e `#CFC9BE` (improcedentes — pedra quente em vez de cinza frio `#CBD2D8`), grades horizontais quase invisíveis (`#EAE6DD`) e menos espaçamento desperdiçado.

### Tela 3 — Análise Comparativa de Petição (`#panel-upload`)
- **Eliminar o estado vazio de landing page:** reduzir `.result-empty-card` (tirar `min-height: 480px`, tirar o círculo gigante de `64px` e tirar o grid de 3 colunas de marketing `.result-empty-features`). Substituir por um estado vazio calmo e objetivo em 2–3 linhas (o que acontece ao enviar a petição + opção direta de testar o modelo de exemplo) ou layout em 2 colunas equilibrado em telas largas.
- **Folha de parecer (`.document-sheet` e `.thesis-card`):** remover `border-top: 4px` e `border-left: 3px`. Tratar como uma folha limpa de laudo jurídico com títulos em `Source Serif 4` e separação por filetes horizontais sutis.

---

## 6. Proibições Explícitas (Anti-padrões — NUNCA usar)
1. NÃO manter o quadrado `.brand-monogram` com a letra "J" e bordinha dourada.
2. NÃO usar `border-left` ou `border-top` grossos (2px, 3px ou 4px) em cards, banners, caixas de citação, DataJud ou folhas de documento.
3. NÃO colocar caixa cinza dentro de card branco para o resumo de decisão (`.decision-excerpt-box`).
4. NÃO usar `Inter` como fonte principal nem cores frias hardcoded (`#F3F5F6`, `#E3E6E8`, `#475569`, `#0f172a`, `#64748b`, `#e2e8f0`, `#CBD2D8`).
5. NÃO manter `.results-scope-toolbar` ou `.active-filters-strip` como cards separados empilhados acima da lista.
6. NÃO manter estado vazio de `480px` com círculo gigante de ícone e 3 cards promocionais em `#panel-upload`.
7. NÃO deixar `style="..."` inline de cores/bordas no HTML (tudo deve usar variáveis de `design-tokens.css`).
8. NÃO quebrar nenhum seletor, `id`, `aria-*`, `label[for]`, token ou regra verificada por `backend/tests/test_frontend_accessibility.py`.