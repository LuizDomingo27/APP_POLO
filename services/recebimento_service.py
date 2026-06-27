"""
services/recebimento_service.py
ABA 2 — "Recebido": pedidos de MP = POLO já recebidos,
com base na planilha RECEBIMENTO.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import pandas as pd
import streamlit as st

from core import utils
from core.constants import MINUTOS_COL, OFICINA_COL, ORDEM_COL

SHEET_NAME = "RECEBIMENTO"
DATE_COL = "DIA"
QTD_COL = "REAL CORTADO"


@st.cache_data(show_spinner="Carregando RECEBIMENTO...")
def load_polo_data(source: Union[Path, "st.runtime.uploaded_file_manager.UploadedFile"]) -> pd.DataFrame:
    """Lê a planilha RECEBIMENTO e filtra apenas MP = POLO."""
    df = pd.read_excel(source, sheet_name=SHEET_NAME)
    df[OFICINA_COL] = utils.clean_text_series(df[OFICINA_COL])
    df[ORDEM_COL] = df[ORDEM_COL].astype(str).str.strip()
    df = utils.filter_mp_polo(df, mp_col="MP")
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    return df


def render(df: Optional[pd.DataFrame]) -> None:
    utils.section_title(
        "✅ Recebido — Pedidos POLO já recebidos",
        "Origem: planilha RECEBIMENTO · filtrado para MP = POLO. Filtro de período aplicado sobre a Data de Recebimento (DIA).",
    )

    if df is None:
        st.info("Carregue o arquivo **RECEBIMENTO.xlsx** na barra lateral para visualizar esta aba.")
        return
    if df.empty:
        st.warning("Nenhum registro com MP = POLO encontrado em RECEBIMENTO.")
        return

    filtered = utils.apply_filters(
        df,
        date_col=DATE_COL,
        oficina_col=OFICINA_COL,
        key_prefix="receb",
        date_label="Data de Recebimento",
        oficina_label="Oficina(s)",
    )

    if filtered.empty:
        st.warning("Nenhum registro para os filtros selecionados.")
        return

    total_pecas = filtered[QTD_COL].sum()
    total_minutos = filtered[MINUTOS_COL].sum()
    total_ordens = filtered[ORDEM_COL].nunique()

    c1, c2, c3 = st.columns(3)
    with c1:
        utils.kpi_card("Total de Peças Recebidas", utils.format_int_br(total_pecas))
    with c2:
        utils.kpi_card(
            "Total de Minutos",
            utils.format_int_br(total_minutos),
            help_text=f"≈ {total_minutos / 60:,.1f} horas".replace(",", "."),
        )
    with c3:
        utils.kpi_card(
            "Ordens Recebidas",
            str(total_ordens),
            help_text="Ordens distintas (pode haver recebimento parcial em mais de uma data)",
        )

    pecas_por_oficina = (
        filtered.groupby(OFICINA_COL, as_index=True)[QTD_COL]
        .sum()
        .sort_values(ascending=False)
    )
    utils.plot_bar(pecas_por_oficina, title="Peças Recebidas por Oficina")

    filtered_dated = filtered.dropna(subset=[DATE_COL])
    if not filtered_dated.empty:
        daily = (
            filtered_dated.groupby(DATE_COL, as_index=True)[QTD_COL]
            .sum()
            .sort_index()
        )
        utils.plot_line(daily, title="Recebimento por Dia")

    utils.section_divider("Detalhamento dos Recebimentos")
    show_cols = [ORDEM_COL, OFICINA_COL, DATE_COL, QTD_COL, MINUTOS_COL]
    table = filtered[show_cols].sort_values(DATE_COL, na_position="last").rename(
        columns={
            ORDEM_COL: "Ordem Mestre",
            OFICINA_COL: "Oficina",
            DATE_COL: "Dia",
            QTD_COL: "Peças (Real Cortado)",
            MINUTOS_COL: "Minutos",
        }
    )
    utils.render_html_table(
        table,
        date_cols=["Dia"],
        int_cols=["Peças (Real Cortado)"],
        float_cols=["Minutos"],
    )

    utils.download_button(
        table,
        "recebimento_polo.xlsx",
        date_col="Dia",
        oficina_col="Oficina",
        int_cols=["Peças (Real Cortado)"],
        float_cols=["Minutos"],
        key="dl_receb",
    )
