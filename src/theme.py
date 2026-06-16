"""Sistema de diseño central de Publimex.

Una única fuente de verdad para el estilo de toda la app: tipografía Outfit, líneas
rectas (esquinas a 0), rojo/blanco de marca, superficies planas con borde fino y un
ancho de contenido acotado (estilo Claude).

Uso:
- `inject_theme()` una vez en `app.py` (se re-ejecuta en cada rerun de Streamlit).
- `page_header(titulo, subtitulo)` al inicio de cada página.
- `chip(texto, kind)` para etiquetas/estados; `.pm-card` para tarjetas estáticas.
- `use_full_width()` en páginas con tablas/calendarios anchos (Disponibilidades).
"""

import streamlit as st

# ── Tokens (también disponibles como variables CSS en :root) ─────────────────────
RED        = "#E60000"
RED_HOVER  = "#C20000"
RED_SOFT   = "#FDECEC"
INK        = "#1A1A1A"
INK_SOFT   = "#6B6B6B"
BORDER     = "#E6E4DF"
SURFACE    = "#FAFAF9"

# Colores de chips por tipo: (fondo, texto)
CHIP_KINDS = {
    "neutral": ("#F1F0EC", "#5A5A5A"),
    "red":     (RED_SOFT, "#A50000"),
    "green":   ("#E7F4EC", "#1B7A3D"),
    "amber":   ("#FBF0D9", "#8A5A00"),
    "blue":    ("#E7EEF7", "#1F4E79"),
    "gray":    ("#EEEDEA", "#6B6B6B"),
}


def inject_theme():
    """Inyecta @font-face, variables y overrides globales. Llamar una vez en app.py."""
    st.markdown(
        """
<style>
/* ── Tipografía Outfit (servida en app/static) ── */
@font-face {
    font-family: 'Outfit';
    src: url('app/static/fonts/Outfit.ttf') format('truetype');
    font-weight: 100 900;
    font-style: normal;
    font-display: swap;
}

:root {
    --pm-red: #E60000;
    --pm-red-hover: #C20000;
    --pm-red-soft: #FDECEC;
    --pm-ink: #1A1A1A;
    --pm-ink-soft: #6B6B6B;
    --pm-border: #E6E4DF;
    --pm-bg: #FFFFFF;
    --pm-surface: #FAFAF9;
}

html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
    font-family: 'Outfit', -apple-system, system-ui, sans-serif;
}

/* ── Ancho de contenido acotado y centrado (estilo Claude) ── */
.block-container {
    max-width: 1040px !important;
    padding-top: 2.4rem !important;
    padding-bottom: 4rem !important;
}

/* ── Jerarquía tipográfica sobria ── */
h1, h2, h3, h4 {
    font-family: 'Outfit', sans-serif !important;
    color: var(--pm-ink) !important;
    letter-spacing: -0.01em;
    font-weight: 600 !important;
}
h1 { font-size: 1.55rem !important; }
h2 { font-size: 1.25rem !important; }
h3 { font-size: 1.1rem !important; }
p, li, .stMarkdown { color: var(--pm-ink); }

/* ── Cabecera de página (page_header) ── */
.pm-page { margin-bottom: 1.4rem; padding-bottom: 0.9rem; border-bottom: 1px solid var(--pm-border); }
.pm-eyebrow {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.09em; text-transform: uppercase;
    color: var(--pm-red); margin-bottom: 4px;
}
.pm-page-title { font-size: 1.55rem; font-weight: 600; color: var(--pm-ink); line-height: 1.2; letter-spacing: -0.01em; }
.pm-page-sub { font-size: 0.92rem; color: var(--pm-ink-soft); margin-top: 4px; }

/* ── Tarjeta plana ── */
.pm-card {
    background: var(--pm-bg);
    border: 1px solid var(--pm-border);
    border-radius: 0;
    padding: 18px 20px;
    margin-bottom: 14px;
}
.pm-card-title { font-size: 1rem; font-weight: 600; color: var(--pm-ink); margin-bottom: 6px; }
.pm-card-desc { font-size: 0.9rem; color: var(--pm-ink-soft); line-height: 1.55; }

/* ── Tarjetas tipo dashboard (Home) ── */
.pm-dash-title { display: flex; align-items: center; font-size: 1.05rem; font-weight: 600; color: var(--pm-ink); margin-bottom: 6px; }
.pm-ico {
    display: inline-flex; align-items: center; justify-content: center;
    width: 30px; height: 30px; min-width: 30px; background: var(--pm-red); color: #fff; margin-right: 10px;
}
.pm-dash-desc { font-size: 0.88rem; color: var(--pm-ink-soft); line-height: 1.5; }
.pm-stat-row { display: flex; gap: 26px; margin: 14px 0 4px; flex-wrap: wrap; }
.pm-stat-num { font-size: 1.5rem; font-weight: 700; color: var(--pm-ink); line-height: 1; }
.pm-stat-lbl { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--pm-ink-soft); margin-top: 4px; }

/* ── Ficha clave/valor (resumen en lugar de formulario) ── */
.pm-kv { display: grid; grid-template-columns: 1fr 1fr; gap: 16px 32px; }
.pm-kv .lbl { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--pm-ink-soft); margin-bottom: 3px; }
.pm-kv .val { font-size: 0.95rem; color: var(--pm-ink); font-weight: 500; }
.pm-kv .full { grid-column: 1 / -1; }
.pm-muted { color: var(--pm-ink-soft); font-weight: 400; }

/* ── Chip / etiqueta ── */
.pm-chip {
    display: inline-block; padding: 2px 9px; border-radius: 0;
    font-size: 0.72rem; font-weight: 600; white-space: nowrap; line-height: 1.5;
}

/* ── Botones: rectos, sobrios ── */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button, [data-testid="stBaseButton-secondary"] {
    border-radius: 0 !important;
    font-weight: 500 !important;
    letter-spacing: 0 !important;
}
button[kind="secondary"], [data-testid="stBaseButton-secondary"] {
    border: 1px solid var(--pm-border) !important;
    background: var(--pm-bg) !important;
    color: var(--pm-ink) !important;
}
button[kind="secondary"]:hover, [data-testid="stBaseButton-secondary"]:hover {
    border-color: var(--pm-ink) !important;
    color: var(--pm-ink) !important;
}
/* Botones primarios: blancos, borde y texto rojo (no relleno) */
button[kind="primary"], [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
    background: #ffffff !important;
    color: var(--pm-red) !important;
    border: 1px solid var(--pm-red) !important;
}
button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover,
[data-testid="stBaseButton-primaryFormSubmit"]:hover {
    background: var(--pm-red-soft) !important;
    color: var(--pm-red-hover) !important;
    border-color: var(--pm-red-hover) !important;
}

/* ── Inputs / select / textarea ── */
[data-baseweb="input"], [data-baseweb="select"] > div, .stTextInput input,
.stNumberInput input, .stTextArea textarea, .stDateInput input {
    border-radius: 0 !important;
}

/* ── Expanders y contenedores con borde: planos ── */
[data-testid="stExpander"], [data-testid="stExpander"] details {
    border-radius: 0 !important;
    border-color: var(--pm-border) !important;
    box-shadow: none !important;
}
[data-testid="stExpander"] summary { font-weight: 500; }
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 0 !important;
}

/* ── Métricas como celdas planas ── */
[data-testid="stMetric"] {
    border: 1px solid var(--pm-border);
    border-radius: 0;
    padding: 14px 16px;
    background: var(--pm-bg);
}
[data-testid="stMetricValue"] { font-weight: 600; }

/* ── Tabs: subrayado limpio, rojo activo ── */
button[data-baseweb="tab"] { font-weight: 500 !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--pm-red) !important; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { background-color: var(--pm-red) !important; }

/* ── Dataframe: bordes finos, rectos ── */
[data-testid="stDataFrame"], [data-testid="stTable"] { border-radius: 0 !important; }

/* ── Divisores más sutiles ── */
hr { border-color: var(--pm-border) !important; }

/* ── Sidebar: navegación sobria y jerárquica ── */
[data-testid="stSidebar"] { background: var(--pm-bg); }
[data-testid="stSidebarNav"] { padding-top: 8px; }
[data-testid="stSidebarNav"] ul { gap: 1px; }
[data-testid="stSidebarNav"] a {
    border-radius: 0 !important;
    font-weight: 500;
}
[data-testid="stSidebarNav"] span[data-testid="stPageLinkIcon"],
[data-testid="stSidebarNav"] span[data-testid="stIconMaterial"] { color: var(--pm-red) !important; }
[data-testid="stSidebarNav"] li a[aria-current="page"] {
    color: var(--pm-red) !important;
    font-weight: 600 !important;
    background: var(--pm-red-soft) !important;
    border-left: 2px solid var(--pm-red) !important;
}
/* Etiquetas de sección en la navegación agrupada */
[data-testid="stSidebarNav"] [data-testid="stNavSectionHeader"] {
    font-size: 0.7rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--pm-ink-soft) !important;
    font-weight: 600 !important;
    margin-top: 14px;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str | None = None, eyebrow: str | None = None):
    """Cabecera de página consistente (reemplaza los headers 2rem/800 por página)."""
    html = ['<div class="pm-page">']
    if eyebrow:
        html.append(f'<div class="pm-eyebrow">{eyebrow}</div>')
    html.append(f'<div class="pm-page-title">{title}</div>')
    if subtitle:
        html.append(f'<div class="pm-page-sub">{subtitle}</div>')
    html.append('</div>')
    st.markdown("".join(html), unsafe_allow_html=True)


def chip(text: str, kind: str = "neutral") -> str:
    """Devuelve el HTML de un chip; usar con st.markdown(..., unsafe_allow_html=True)."""
    bg, fg = CHIP_KINDS.get(kind, CHIP_KINDS["neutral"])
    return f'<span class="pm-chip" style="background:{bg}; color:{fg};">{text}</span>'


def use_full_width():
    """Rompe el ancho acotado para páginas con tablas/calendarios anchos."""
    st.markdown(
        "<style>.block-container{max-width:100% !important; "
        "padding-left:2.5rem !important; padding-right:2.5rem !important;}</style>",
        unsafe_allow_html=True,
    )
