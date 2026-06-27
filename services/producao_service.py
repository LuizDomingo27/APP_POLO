"""
services/producao_service.py
ABA 3 — "Produção Diária": volume diário informado pelas oficinas de POLO,
com base na planilha "Produção Diária - POLO". Esta planilha já é exclusiva
de POLO (não possui coluna MP), então não há filtro de matéria-prima aqui.
Conforme solicitado, não exibimos total de minutos nesta aba — apenas
ordens (registros de produção) e peças.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import pandas as pd
import streamlit as st

from core import utils
from core.constants import OFICINA_COL

SHEET_NAME = "BD"
DATE_COL = "DATA"
QTD_COL = "QUANTIDADE DE PEÇAS PRODUZIDA"
WK_COL = "WK"


@st.cache_data(show_spinner="Carregando Produção Diária...")
def load_data(source: Union[Path, "st.runtime.uploaded_file_manager.UploadedFile"]) -> pd.DataFrame:
    """Lê a planilha de Produção Diária - POLO (aba BD)."""
    df = pd.read_excel(source, sheet_name=SHEET_NAME)
    df.columns = [str(c).replace("\xa0", " ").strip() for c in df.columns]
    df[OFICINA_COL] = utils.clean_text_series(df[OFICINA_COL])
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    return df


def render(df: Optional[pd.DataFrame]) -> None:
    utils.section_title(
        "🏭 Produção Diária — Oficinas POLO",
        "Origem: planilha 'Produção Diária - POLO'. Dados já exclusivos de MP = POLO. "
        "Esta aba não exibe total de minutos, apenas ordens (registros) e peças.",
    )

    if df is None:
        st.info("Carregue o arquivo **Produção Diária - POLO.xlsx** na barra lateral para visualizar esta aba.")
        return
    if df.empty:
        st.warning("Nenhum dado de produção diária encontrado.")
        return

    filtered = utils.apply_filters(
        df,
        date_col=DATE_COL,
        oficina_col=OFICINA_COL,
        key_prefix="prod",
        date_label="Data de Produção",
        oficina_label="Oficina(s)",
        extra_filter_col=WK_COL,
        extra_filter_label="Semana (WK)",
    )

    if filtered.empty:
        st.warning("Nenhum registro para os filtros selecionados.")
        return

    total_pecas = filtered[QTD_COL].sum()
    total_ordens = len(filtered)

    c1, c2 = st.columns(2)
    with c1:
        utils.kpi_card("Total de Peças Produzidas", utils.format_int_br(total_pecas))
    with c2:
        utils.kpi_card(
            "Ordens (Registros de Produção)",
            str(total_ordens),
            help_text="Cada registro = 1 lançamento diário de produção por oficina",
        )

    pecas_por_oficina = (
        filtered.groupby(OFICINA_COL, as_index=True)[QTD_COL]
        .sum()
        .sort_values(ascending=False)
    )
    utils.plot_bar(pecas_por_oficina, title="Peças Produzidas por Oficina")

    filtered_dated = filtered.dropna(subset=[DATE_COL])
    if not filtered_dated.empty:
        daily = (
            filtered_dated.groupby(DATE_COL, as_index=True)[QTD_COL]
            .sum()
            .sort_index()
        )
        utils.plot_line(daily, title="Produção Diária (Total)")

    utils.section_divider("Detalhamento da Produção")
    show_cols = [OFICINA_COL, DATE_COL, QTD_COL, WK_COL]
    table = filtered[show_cols].sort_values(DATE_COL, na_position="last").rename(
        columns={
            OFICINA_COL: "Oficina",
            DATE_COL: "Data",
            QTD_COL: "Peças Produzidas",
            WK_COL: "Semana",
        }
    )
    utils.render_html_table(
        table,
        date_cols=["Data"],
        int_cols=["Peças Produzidas"],
    )

    utils.download_button(
        table,
        "producao_diaria_polo.xlsx",
        date_col="Data",
        oficina_col="Oficina",
        int_cols=["Peças Produzidas"],
        key="dl_prod",
    )
