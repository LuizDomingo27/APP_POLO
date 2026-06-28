"""
core/data_prep.py
Normalização de texto, filtros de dados e formatação numérica/de datas.

Responsabilidade: lógica pura de preparação de dados (sem UI) mais os
widgets de filtro Streamlit (data + oficina + extra). Separado de ui.py
para que as funções de formatação possam ser testadas sem contexto Streamlit.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from core.constants import MP_VALUE


# --------------------------------------------------------------------------- #
# Normalização de texto
# --------------------------------------------------------------------------- #
def clean_text_series(series: pd.Series) -> pd.Series:
    """Remove espaços comuns e non-breaking spaces (\\xa0) e padroniza para string."""
    return (
        series.astype(str)
        .str.replace("\xa0", " ", regex=False)
        .str.strip()
    )


def filter_mp_polo(df: pd.DataFrame, mp_col: str = "MP") -> pd.DataFrame:
    """Retorna apenas as linhas onde a coluna MP == 'POLO' (case/espaço-insensitive)."""
    out = df.copy()
    out[mp_col] = clean_text_series(out[mp_col])
    mask = out[mp_col].str.upper() == MP_VALUE
    return out[mask].reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Formatação pt-BR
# --------------------------------------------------------------------------- #
def format_int_br(value: float) -> str:
    """Formata número inteiro no padrão brasileiro (separador de milhar com ponto)."""
    try:
        if pd.isna(value):
            return "0"
        return f"{value:,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def format_float_br(value: float, decimals: int = 2) -> str:
    """Formata número decimal no padrão brasileiro (milhar com ponto, decimal com vírgula)."""
    try:
        text = f"{value:,.{decimals}f}"
        # troca vírgula <-> ponto via marcador intermediário §
        return text.replace(",", "§").replace(".", ",").replace("§", ".")
    except (TypeError, ValueError):
        return "0"


def format_date_br(value) -> str:
    """Formata data no padrão brasileiro DD/MM/AAAA; retorna '—' se vazia/inválida."""
    if value is None or pd.isna(value):
        return "—"
    return pd.Timestamp(value).strftime("%d/%m/%Y")


# --------------------------------------------------------------------------- #
# Widgets de filtro reutilizáveis
# --------------------------------------------------------------------------- #
def dropdown_filter(
    options: list,
    key: str,
    label: str = "Opções",
    icon: str = "🏭",
) -> list:
    """
    Filtro em lista suspensa nativa (st.selectbox): a primeira opção é
    "Todas" (mantém todos os registros) e as demais permitem escolher
    exatamente uma opção. Um único widget, sem popover, sem botões extras.
    """
    state_key = f"{key}__sel"
    all_label = f"Todas ({len(options)})"
    full_options = [all_label] + list(options)

    # se a opção salva não existe mais (ex.: troca de período), volta para "Todas"
    if state_key in st.session_state and st.session_state[state_key] not in full_options:
        st.session_state[state_key] = all_label

    if state_key not in st.session_state:
        st.session_state[state_key] = all_label

    choice = st.selectbox(f"{icon} {label}", options=full_options, key=state_key)

    if choice == all_label:
        return list(options)
    return [choice]


def apply_filters(
    df: pd.DataFrame,
    date_col: str,
    oficina_col: str,
    key_prefix: str,
    date_label: str = "Período",
    oficina_label: str = "Oficina(s)",
    extra_filter_col: Optional[str] = None,
    extra_filter_label: str = "Semana",
) -> pd.DataFrame:
    """
    Renderiza filtros de data + oficina (e opcionalmente uma terceira coluna,
    ex.: semana/WK) acima do conteúdo e retorna o DataFrame já filtrado.

    Linhas sem data preenchida são sempre mantidas independentemente do período
    escolhido, para não ocultar registros silenciosamente.
    """
    work = df.copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work[oficina_col] = clean_text_series(work[oficina_col])

    valid_dates = work[date_col].dropna()
    has_dates = not valid_dates.empty

    n_cols = 3 if extra_filter_col else 2
    cols = st.columns([1.3, 1.7, 1.0][:n_cols])

    # --- filtro de data
    with cols[0]:
        if has_dates:
            min_d, max_d = valid_dates.min().date(), valid_dates.max().date()
            date_range = st.date_input(
                date_label,
                value=(min_d, max_d),
                min_value=min_d,
                max_value=max_d,
                key=f"{key_prefix}",
                format="DD/MM/YYYY",
            )
        else:
            date_range = None
            st.caption(f"{date_label}: sem datas disponíveis")

    # --- filtro de oficina
    with cols[1]:
        oficinas = sorted(
            o for o in work[oficina_col].dropna().unique() if o and o.lower() != "nan"
        )
        selected_oficinas = dropdown_filter(
            oficinas, key=f"{key_prefix}_oficina", label=oficina_label, icon="🏭"
        )

    # --- filtro extra opcional (ex.: WK)
    selected_extra: list = []
    if extra_filter_col:
        with cols[2]:
            extra_opts = sorted(work[extra_filter_col].dropna().unique())
            selected_extra = dropdown_filter(
                extra_opts, key=f"{key_prefix}_extra", label=extra_filter_label, icon="📅"
            )

    mask = pd.Series(True, index=work.index)

    if has_dates and isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end) + pd.Timedelta(hours=23, minutes=59, seconds=59)
        mask &= work[date_col].between(start_ts, end_ts) | work[date_col].isna()

    if selected_oficinas:
        mask &= work[oficina_col].isin(selected_oficinas)
    else:
        mask &= False

    if extra_filter_col:
        if selected_extra:
            mask &= work[extra_filter_col].isin(selected_extra)
        else:
            mask &= False

    filtered = work[mask].reset_index(drop=True)

    n_no_date = filtered[date_col].isna().sum() if has_dates else 0
    if n_no_date:
        st.caption(
            f"⚠️ {n_no_date} registro(s) sem data preenchida — "
            "exibidos independentemente do período selecionado."
        )

    return filtered
