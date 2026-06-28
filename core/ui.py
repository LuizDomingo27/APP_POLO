"""
core/ui.py
Componentes de interface: injeção de CSS, cabeçalhos, cartões KPI,
tabela HTML customizada e helper de resolução de fonte de dados.

Separado de data_prep.py para manter clara a distinção entre lógica de dados
(testável sem Streamlit) e renderização de UI (requer contexto Streamlit).
"""
from __future__ import annotations

import html as html_lib
import pandas as pd
from pathlib import Path
from typing import Iterable, Optional

import streamlit as st

from core.data_prep import format_date_br, format_float_br, format_int_br


# --------------------------------------------------------------------------- #
# Tema visual — CSS global
# --------------------------------------------------------------------------- #
def inject_global_css() -> None:
    """Injeta o CSS global do app: tipografia, cores e componentes customizados."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&family=Inter:wght@400;500;600;700&display=swap');

        :root{
            --bg-deep:#070D14;
            --bg-base:#0B131C;
            --surface:#101B26;
            --surface-2:#16222F;
            --accent:#2EE6C0;
            --accent-soft:rgba(46,230,192,0.13);
            --accent-border:rgba(46,230,192,0.30);
            --accent-glow:rgba(46,230,192,0.16);
            --text-main:#E7F1F0;
            --text-muted:#7C95A0;
            --danger:#FF6B6B;
            --radius-lg:18px;
            --radius-md:14px;
            --radius-sm:10px;
        }

        html, body, [class*="css"], [data-testid="stAppViewContainer"] {
            font-family:'Inter', sans-serif;
        }

        .stApp{
            background: radial-gradient(circle at 8% -10%, #0F2027 0%, var(--bg-base) 42%, var(--bg-deep) 100%);
            color: var(--text-main);
        }

        section[data-testid="stSidebar"]{
            background: var(--bg-deep);
            border-right: 1px solid rgba(46,230,192,0.08);
        }

        /* ---------- Header ---------- */
        .app-header{
            padding: 1.3rem 1.7rem;
            border-radius: var(--radius-lg);
            background: linear-gradient(135deg, rgba(46,230,192,0.10), rgba(16,32,38,0.55));
            border: 1px solid var(--accent-border);
            margin-bottom: 1.1rem;
        }
        .app-header h1{
            font-family:'Sora', sans-serif;
            font-weight:700;
            font-size:1.6rem;
            margin:0;
            color: var(--text-main);
            letter-spacing:.2px;
        }
        .app-header p{
            color: var(--text-muted);
            margin:.35rem 0 0;
            font-size:.92rem;
        }
        .app-header .badge{
            display:inline-block;
            margin-top:.55rem;
            padding:.18rem .65rem;
            border-radius:999px;
            background: var(--accent-soft);
            border:1px solid var(--accent-border);
            color: var(--accent);
            font-size:.72rem;
            font-weight:600;
            letter-spacing:.04em;
        }

        /* ---------- Section titles ---------- */
        .section-title{
            font-family:'Sora', sans-serif;
            font-weight:700;
            font-size:1.05rem;
            color: var(--text-main);
            margin: 1.1rem 0 .55rem;
        }
        .section-caption{
            color: var(--text-muted);
            font-size:.82rem;
            margin-top:-.4rem;
            margin-bottom:.8rem;
        }

        /* ---------- Tabs ---------- */
        button[data-baseweb="tab"]{
            font-family:'Sora', sans-serif;
            font-weight:600;
            border-radius:999px !important;
            padding:.5rem 1.15rem !important;
            color: var(--text-muted) !important;
            margin-right:.3rem !important;
        }
        button[data-baseweb="tab"][aria-selected="true"]{
            background: var(--accent-soft) !important;
            color: var(--accent) !important;
            box-shadow: 0 0 0 1px var(--accent-border) inset;
        }
        div[data-baseweb="tab-highlight"]{ background-color: var(--accent) !important; }
        div[data-baseweb="tab-border"]{ background-color: rgba(255,255,255,0.04) !important; }

        /* ---------- KPI cards ---------- */
        .kpi-card{
            background: linear-gradient(160deg, var(--surface), var(--surface-2));
            border: 1px solid var(--accent-border);
            border-radius: var(--radius-lg);
            padding: 1.05rem 1.25rem;
            box-shadow: 0 0 26px var(--accent-glow);
            height: 100%;
        }
        .kpi-label{
            font-family:'Inter', sans-serif;
            text-transform:uppercase;
            letter-spacing:.08em;
            font-size:.70rem;
            color: var(--text-muted);
            font-weight:600;
        }
        .kpi-value{
            font-family:'Sora', sans-serif;
            font-size:1.85rem;
            font-weight:700;
            color: var(--accent);
            margin-top:.22rem;
            line-height:1.15;
        }
        .kpi-help{
            font-size:.74rem;
            color: var(--text-muted);
            margin-top:.18rem;
        }

        /* ---------- Dataframe / containers ---------- */
        [data-testid="stDataFrame"]{
            border-radius: var(--radius-md);
            overflow:hidden;
            border: 1px solid var(--accent-border);
        }

        /* ---------- Tabela HTML customizada (substitui st.dataframe) ---------- */
        .polo-table-wrap{
            overflow:auto;
            border-radius: var(--radius-md);
            border: 1px solid var(--accent-border);
            box-shadow: 0 0 22px rgba(0,0,0,0.20);
            margin-bottom: .4rem;
        }
        table.polo-table{
            width:100%;
            border-collapse:separate;
            border-spacing:0;
            font-family:'Inter', sans-serif;
            font-size:.86rem;
        }
        table.polo-table thead th{
            position:sticky;
            top:0;
            z-index:1;
            background: linear-gradient(135deg, #132E2C, #101B26);
            color: var(--accent);
            text-align:center;
            padding:.7rem .85rem;
            font-weight:700;
            font-size:.70rem;
            text-transform:uppercase;
            letter-spacing:.05em;
            border-bottom:1px solid var(--accent-border);
            white-space:nowrap;
        }
        table.polo-table tbody td{
            text-align:center;
            padding:.55rem .85rem;
            color: var(--text-main);
            border-bottom:1px solid rgba(255,255,255,0.05);
            white-space:nowrap;
        }
        table.polo-table tbody tr:nth-child(even){
            background: rgba(46,230,192,0.04);
        }
        table.polo-table tbody tr:hover td{
            background: var(--accent-soft);
        }
        table.polo-table tbody tr:last-child td{
            border-bottom:none;
        }
        .polo-table-empty{
            color: var(--text-muted);
            font-size:.85rem;
            padding:.6rem 0;
        }
        div[data-testid="stExpander"]{
            border-radius: var(--radius-md) !important;
            border: 1px solid rgba(46,230,192,0.18) !important;
            background: var(--surface);
        }

        /* ---------- Buttons & inputs ---------- */
        .stButton>button, .stDownloadButton>button{
            border-radius: var(--radius-sm) !important;
            border: 1px solid var(--accent-border) !important;
            background: var(--accent-soft) !important;
            color: var(--accent) !important;
            font-weight:600 !important;
            transition: all .15s ease;
        }
        .stButton>button:hover, .stDownloadButton>button:hover{
            background: var(--accent) !important;
            color:#06151A !important;
            border-color: var(--accent) !important;
        }
        div[data-baseweb="select"]>div, .stDateInput input, .stTextInput input{
            border-radius: var(--radius-sm) !important;
            border-color: rgba(46,230,192,0.22) !important;
        }
        div[data-baseweb="popover"]{ border-radius: var(--radius-md) !important; }

        /* ---------- Misc ---------- */
        hr{ border-color: rgba(46,230,192,0.12) !important; }
        ::-webkit-scrollbar{ width:8px; height:8px; }
        ::-webkit-scrollbar-thumb{ background: rgba(46,230,192,0.30); border-radius:8px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <style>
        /* ── Design direction enhancements ──────────────────────────────── */

        .section-title{
            border-left: 3px solid var(--accent);
            padding-left: .65rem;
            margin-top: 1.5rem;
        }
        .section-caption{ padding-left: .65rem; }

        .kpi-card{
            border-bottom: 2px solid var(--accent) !important;
            transition: transform .14s ease, box-shadow .14s ease;
            cursor: default;
        }
        .kpi-card:hover{
            transform: translateY(-3px);
            box-shadow: 0 6px 36px var(--accent-glow);
        }

        .polo-divider{
            display: flex;
            align-items: center;
            gap: .75rem;
            margin: 1.6rem 0 1.1rem;
            font-family: 'Sora', sans-serif;
            color: var(--text-muted);
            font-size: .68rem;
            font-weight: 700;
            letter-spacing: .12em;
            text-transform: uppercase;
        }
        .polo-divider::before, .polo-divider::after{
            content: '';
            flex: 1;
            height: 1px;
            background: rgba(46,230,192,0.14);
        }

        section[data-testid="stSidebar"] h3{
            font-family: 'Sora', sans-serif;
            font-size: .82rem;
            color: var(--accent);
            letter-spacing: .06em;
            margin-bottom: .4rem;
        }
        section[data-testid="stSidebar"] [data-testid="stFileUploader"]{
            border: 1px dashed rgba(46,230,192,0.22);
            border-radius: var(--radius-sm);
            padding: .35rem .5rem;
            margin-top: .3rem;
        }
        section[data-testid="stSidebar"] [data-testid="stCaption"]{
            color: var(--text-muted);
            font-size: .76rem;
            line-height: 1.5;
        }

        div[data-testid="stTabsContent"]{ padding-top: .5rem; }
        .app-header p{ line-height: 1.45; }
        .stPlotlyChart{ border-radius: var(--radius-md); overflow: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Componentes de página
# --------------------------------------------------------------------------- #
def app_header(title: str, subtitle: Optional[str]="", badge: Optional[str] = None) -> None:
    badge_html = f'<span class="badge">{badge}</span>' if badge else ""
    st.markdown(
        f"""
        <div class="app-header">
            <h1>{title}</h1>
            <p>{subtitle}</p>
            {badge_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(title: str, caption: Optional[str] = None) -> None:
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    if caption:
        st.markdown(f'<div class="section-caption">{caption}</div>', unsafe_allow_html=True)


def section_divider(label: str = "") -> None:
    """Divisor horizontal estilizado com label opcional entre seções."""
    st.markdown(f'<div class="polo-divider">{label}</div>', unsafe_allow_html=True)


def kpi_card(label: str, value: str, help_text: Optional[str] = None) -> None:
    help_html = f'<div class="kpi-help">{help_text}</div>' if help_text else ""
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {help_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Tabela HTML customizada (substitui st.dataframe)
# --------------------------------------------------------------------------- #
def render_html_table(
    df: pd.DataFrame,
    date_cols: Optional[Iterable[str]] = None,
    int_cols: Optional[Iterable[str]] = None,
    float_cols: Optional[Iterable[str]] = None,
    max_height: str = "460px",
) -> None:
    """
    Renderiza um DataFrame como tabela HTML estilizada com o tema do app.

    Motivo de não usar st.dataframe: o componente nativo não permite controlar
    alinhamento de células nem formatação brasileira de forma consistente.

    - date_cols: colunas formatadas como DD/MM/AAAA.
    - int_cols: colunas formatadas como inteiro com separador de milhar (.).
    - float_cols: colunas formatadas como decimal pt-br (1.234,56).
    - Demais colunas: texto com escape HTML por segurança.
    """
    if df.empty:
        st.markdown('<div class="polo-table-empty">Nenhum registro para exibir.</div>', unsafe_allow_html=True)
        return

    date_cols = set(date_cols or [])
    int_cols = set(int_cols or [])
    float_cols = set(float_cols or [])

    headers_html = "".join(f"<th>{html_lib.escape(str(c))}</th>" for c in df.columns)

    formatted_df = df.copy()

    for col in formatted_df.columns:
        if col in date_cols:
            formatted_df[col] = formatted_df[col].apply(format_date_br)
        elif col in int_cols:
            formatted_df[col] = formatted_df[col].apply(lambda val: "—" if pd.isna(val) else format_int_br(val))
        elif col in float_cols:
            formatted_df[col] = formatted_df[col].apply(lambda val: "—" if pd.isna(val) else format_float_br(val))
        else:
            formatted_df[col] = formatted_df[col].apply(lambda val: "—" if pd.isna(val) else html_lib.escape(str(val)))

    # Envolve cada célula com as tags <td> de forma vetorizada
    for col in formatted_df.columns:
        formatted_df[col] = "<td>" + formatted_df[col].astype(str) + "</td>"

    # Junta todas as colunas de cada linha em uma string
    row_strings = formatted_df.sum(axis=1)
    
    # Envolve cada linha com as tags <tr> e junta todas em uma única string HTML
    body_rows = "<tr>" + row_strings + "</tr>"
    body_html = "".join(body_rows)

    table_html = (
        f'<div class="polo-table-wrap" style="max-height:{max_height};">'
        f'<table class="polo-table"><thead><tr>{headers_html}</tr></thead>'
        f'<tbody>{body_html}</tbody></table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Resolução da fonte de dados (arquivo local ou upload)
# --------------------------------------------------------------------------- #
def resolve_data_source(default_path: Path, label: str, uploader_key: str):
    """
    Retorna um caminho/buffer válido para leitura: usa o arquivo padrão do
    dataset se existir; caso contrário, oferece um uploader na sidebar.
    """
    if default_path.exists():
        return default_path

    st.sidebar.warning(f"Arquivo não encontrado: {default_path.name}")
    uploaded = st.sidebar.file_uploader(label, type=["xlsx"], key=uploader_key)
    return uploaded
