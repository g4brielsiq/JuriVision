"""
Verificação Automatizada de Engenharia de UX/UI e Acessibilidade Front-End (ISO/IEC/IEEE 29119).
Rastreabilidade:
- Normas: W3C WCAG 2.2 AA (ISO/IEC 40500), WAI-ARIA 1.2, ISO 9241-110/112, 10 Heurísticas de Nielsen
- MODELING.md: RNF-04, RNF-09, RNF-10 e Seção 2.4
"""
from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = REPO_ROOT / "frontend" / "index.html"
TOKENS_CSS = REPO_ROOT / "frontend" / "src" / "components" / "design-tokens.css"
API_JS = REPO_ROOT / "frontend" / "src" / "services" / "api.js"
APP_JS = REPO_ROOT / "frontend" / "src" / "app.js"


def test_rnf09_wai_aria_landmarks_e_tab_pattern():
    """Verifica conformidade com WAI-ARIA 1.2 (tablist, tab, tabpanel, aria-selected, aria-controls, aria-live)."""
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert 'role="tablist"' in html
    assert 'role="tab"' in html
    assert 'role="tabpanel"' in html
    assert 'aria-selected="true"' in html
    assert 'aria-controls="panel-dashboard"' in html
    assert 'aria-controls="panel-upload"' in html
    assert 'aria-controls="panel-historico"' in html
    assert 'aria-live="polite"' in html
    assert 'role="alert"' in html
    assert 'href="#main-content"' in html


def test_rnf09_wcag_inputs_labels_e_tabelas_semanticas():
    """Verifica WCAG 2.1.1 (Teclado), 3.3.2 (Labels explícitos) e 1.3.1 (Tabelas com scope='col')."""
    html = INDEX_HTML.read_text(encoding="utf-8")

    # Controles nativos de upload de arquivo (corrige NC-UX-01)
    assert 'id="file-input-pdf"' in html and 'type="file"' in html
    assert 'id="file-input-csv"' in html
    assert 'for="file-input-pdf"' in html
    assert 'for="file-input-csv"' in html

    # Rótulos explícitos nos filtros e login (corrige NC-UX-06)
    for field_id in ("filtro-busca", "filtro-tema", "filtro-juiz", "login-email", "login-senha"):
        assert f'for="{field_id}"' in html
        assert f'id="{field_id}"' in html

    # Cabeçalhos de tabela com scope="col" e alternativas para canvas (corrige NC-UX-06 e NC-UX-07)
    assert 'scope="col"' in html
    assert 'id="a11y-table-juizes"' in html
    assert 'id="a11y-table-temas"' in html


def test_rnf09_rnf10_contraste_wcag_e_design_tokens():
    """Verifica ausência de classes/CDNs de template IA (Tailwind/FontAwesome) e presença dos tokens."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    css = TOKENS_CSS.read_text(encoding="utf-8")

    assert "cdn.tailwindcss.com" not in html
    assert "font-awesome" not in html
    assert "text-slate-400" not in html
    assert "text-green-500" not in html
    assert "text-justify" not in html
    assert "--touch-target-min: 44px" in css
    assert ":focus-visible" in css


def test_rnf04_integracao_completa_contratos_api():
    """Verifica que o serviço HTTP front-end referencia todos os endpoints oficiais da Seção 8 de ARCHITECTURE.md."""
    api_code = API_JS.read_text(encoding="utf-8")
    app_code = APP_JS.read_text(encoding="utf-8")

    assert "/api/v1/auth/login" in api_code
    assert "/api/v1/dashboard/metricas" in api_code
    assert "/api/v1/processos/upload-pdf" in api_code
    assert "/api/v1/processos/upload-csv" in api_code
    assert "/api/v1/processos" in api_code
    assert "/api/v1/relatorios/processo/" in api_code
    assert "resetarFluxoUpload" in app_code
