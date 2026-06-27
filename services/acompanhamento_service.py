"""
services/acompanhamento_service.py
ABA 1 — "A Receber": pedidos de MP = POLO ainda pendentes de recebimento,
com base na planilha ACOMPANHAMENTO.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import pandas as pd
import streamlit as st

from core import utils
from core.constants import MINUTOS_COL, OFICINA_COL, ORDEM_COL

SHEET_NAME = "ACOMPANHAMENTO"
DATE_COL = "ENVIO"
SECONDARY_DATE_COL = "DEAD LINE"
QTD_COL = "QTD"


@st.cache_data(show_spinner="Carregando ACOMPANHAMENTO...")
def load_polo_data(source: Union[Path, "st.runtime.uploaded_file_manager.UploadedFile"]) -> pd.DataFrame:
    """Lê a planilha ACOMPANHAMENTO e filtra apenas MP = POLO."""
    df = pd.read_excel(source, sheet_name=SHEET_NAME)
    df[OFICINA_COL] = utils.clean_text_series(df[OFICINA_COL])
    df = utils.filter_mp_polo(df, mp_col="MP")
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    df[SECONDARY_DATE_COL] = pd.to_datetime(df[SECONDARY_DATE_COL], errors="coerce")
    return df


def render(df: Optional[pd.DataFrame]) -> None:
    utils.section_title(
        "📦 A Receber — Pedidos POLO em andamento",
        "Origem: planilha ACOMPANHAMENTO · filtrado para MP = POLO. Filtro de período aplicado sobre a Data de Envio.",
    )

    if df is None:
        st.info("Carregue o arquivo **ACOMPANHAMENTO.xlsx** na barra lateral para visualizar esta aba.")
        return
    if df.empty:
        st.warning("Nenhum registro com MP = POLO encontrado em ACOMPANHAMENTO.")
        return

    filtered = utils.apply_filters(
        df,
        date_col=DATE_COL,
        oficina_col=OFICINA_COL,
        key_prefix="acomp",
        date_label="Data de Envio",
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
        utils.kpi_card("Total de Peças", utils.format_int_br(total_pecas))
    with c2:
        utils.kpi_card(
            "Total de Minutos",
            utils.format_int_br(total_minutos),
            help_text=f"≈ {total_minutos / 60:,.1f} horas".replace(",", "."),
        )
    with c3:
        utils.kpi_card("Ordens a Receber", str(total_ordens))

    pecas_por_oficina = (
        filtered.groupby(OFICINA_COL, as_index=True)[QTD_COL]
        .sum()
        .sort_values(ascending=False)
    )
    utils.plot_bar(pecas_por_oficina, title="Peças por Oficina")

    ordens_por_oficina = (
        filtered.groupby(OFICINA_COL)[ORDEM_COL]
        .nunique()
        .sort_values(ascending=False)
        .rename("Ordens")
    )
    utils.plot_bar(ordens_por_oficina, title="Ordens por Oficina", color="#1FB8A6")

    filtered_dated = filtered.dropna(subset=[DATE_COL])
    if not filtered_dated.empty:
        pecas_por_data = (
            filtered_dated.groupby(DATE_COL)[QTD_COL]
            .sum()
            .sort_index()
        )
        utils.plot_line(pecas_por_data, title="Peças ao Longo do Tempo (Data de Envio)")

    utils.section_divider("Detalhamento dos Pedidos")
    show_cols = [ORDEM_COL, OFICINA_COL, DATE_COL, SECONDARY_DATE_COL, QTD_COL, MINUTOS_COL]
    table = filtered[show_cols].sort_values(DATE_COL, na_position="last").rename(
        columns={
            ORDEM_COL: "Ordem Mestre",
            OFICINA_COL: "Oficina",
            DATE_COL: "Envio",
            SECONDARY_DATE_COL: "Dead Line",
            QTD_COL: "Peças",
            MINUTOS_COL: "Minutos",
        }
    )
    utils.render_html_table(
        table,
        date_cols=["Envio", "Dead Line"],
        int_cols=["Peças"],
        float_cols=["Minutos"],
    )

    utils.download_button(
        table,
        "acompanhamento_polo.xlsx",
        date_col="Envio",
        oficina_col="Oficina",
        int_cols=["Peças"],
        float_cols=["Minutos"],
        key="dl_acomp",
    )
