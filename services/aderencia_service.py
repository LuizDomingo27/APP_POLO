"""
services/aderencia_service.py
ABA — "Aderência das Oficinas"

Cruzamento entre as três fontes de dados para medir a confiabilidade
de cada oficina POLO:

  Fonte                | Coluna de qtd                  | Data de ref.
  ---------------------|--------------------------------|-------------
  A Receber (ACOMP)    | QTD                            | DEAD LINE
  Recebido (RECEB)     | REAL CORTADO                   | DIA
  Produção Diária      | QUANTIDADE DE PEÇAS PRODUZIDA  | DATA

Cruzamentos realizados:
  1. Por OFICINA (todas as fontes): volume Programado × Recebido × Declarado
  2. Por ORDEM MESTRE + OFICINA (ACOMP × RECEB): status ordem a ordem
"""
from __future__ import annotations

import datetime

import pandas as pd
import streamlit as st

from core import utils
from core.charts import plot_bar_grouped
from core.constants import OFICINA_COL, ORDEM_COL

_ACOMP_QTD = "QTD"
_RECEB_QTD = "REAL CORTADO"
_PROD_QTD = "QUANTIDADE DE PEÇAS PRODUZIDA"
_ACOMP_DATE = "DEAD LINE"
_RECEB_DATE = "DIA"
_PROD_DATE = "DATA"

_COLORS = ["#7C95A0", "#2EE6C0", "#F4A261"]  # Programado / Recebido / Declarado


# ---------------------------------------------------------------------------
# Preparação de dados (puras)
# ---------------------------------------------------------------------------

def _filter_by_period(
    df: pd.DataFrame,
    date_col: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    mask = df[date_col].notna() & df[date_col].between(start, end)
    return df[mask]


def build_adherence_table(
    df_acomp: pd.DataFrame,
    df_receb: pd.DataFrame,
    df_prod: pd.DataFrame,
) -> pd.DataFrame:
    """
    Tabela consolidada de aderência agrupada por OFICINA.

    Colunas: Oficina | Programado | Recebido | Declarado | Gap Prog→Receb | Gap Decl→Receb | Status
    """
    prog = df_acomp.groupby(OFICINA_COL)[_ACOMP_QTD].sum().rename("Programado")
    receb = df_receb.groupby(OFICINA_COL)[_RECEB_QTD].sum().rename("Recebido")
    decl = (
        df_prod.groupby(OFICINA_COL)[_PROD_QTD].sum().rename("Declarado")
        if not df_prod.empty
        else pd.Series(dtype=float, name="Declarado")
    )

    df = pd.concat([prog, receb, decl], axis=1).fillna(0)
    df.index.name = "Oficina"
    df = df.reset_index()

    df["Gap Prog→Receb"] = (df["Programado"] - df["Recebido"]).astype(int)
    df["Gap Decl→Receb"] = (df["Declarado"] - df["Recebido"]).astype(int)

    def _semaforo(row: pd.Series) -> str:
        if row["Programado"] == 0:
            return "⚪ S/ Prog."
        taxa = row["Recebido"] / row["Programado"] * 100
        if taxa >= 95:
            return "🟢 OK"
        if taxa >= 80:
            return "🟡 Atenção"
        return "🔴 Crítico"

    df["Status"] = df.apply(_semaforo, axis=1)
    df[["Programado", "Recebido", "Declarado"]] = df[
        ["Programado", "Recebido", "Declarado"]
    ].astype(int)

    return df.sort_values("Gap Prog→Receb", ascending=False)


def build_orders_cross(
    df_acomp: pd.DataFrame,
    df_receb: pd.DataFrame,
) -> pd.DataFrame:
    """
    Cruzamento por ORDEM MESTRE + OFICINA entre A Receber e Recebido.

    Colunas: Ordem Mestre | Oficina | Programado | Recebido | Saldo | % Recebido | Status
    """
    prog = (
        df_acomp.groupby([ORDEM_COL, OFICINA_COL])[_ACOMP_QTD]
        .sum()
        .reset_index()
        .rename(columns={_ACOMP_QTD: "Programado"})
    )
    receb = (
        df_receb.groupby([ORDEM_COL, OFICINA_COL])[_RECEB_QTD]
        .sum()
        .reset_index()
        .rename(columns={_RECEB_QTD: "Recebido"})
    )

    merged = prog.merge(receb, on=[ORDEM_COL, OFICINA_COL], how="left")
    merged["Recebido"] = merged["Recebido"].fillna(0).astype(int)
    merged["Programado"] = merged["Programado"].astype(int)
    merged["Saldo"] = merged["Programado"] - merged["Recebido"]
    merged["% Recebido"] = (
        merged["Recebido"] / merged["Programado"].replace(0, float("nan")) * 100
    ).round(1)

    def _status(row: pd.Series) -> str:
        pct = row["% Recebido"]
        if pd.isna(pct) or pct == 0:
            return "❌ Não Entregue"
        if pct >= 100:
            return "✅ Completo"
        return "⚠️ Parcial"

    merged["Status"] = merged.apply(_status, axis=1)
    merged = merged.rename(
        columns={ORDEM_COL: "Ordem Mestre", OFICINA_COL: "Oficina"}
    )
    return merged.sort_values("% Recebido", ascending=True, na_position="last")


# ---------------------------------------------------------------------------
# Helpers de semana ISO
# ---------------------------------------------------------------------------

def _week_label(year: int, week: int) -> str:
    ws = datetime.date.fromisocalendar(year, week, 1)
    we = datetime.date.fromisocalendar(year, week, 7)
    return f"Sem. {week:02d}/{year} ({ws.strftime('%d/%m')}–{we.strftime('%d/%m')})"


def _in_iso_weeks(s: pd.Series, sel_yw: set) -> pd.Series:
    return s.apply(
        lambda d: (d.isocalendar().year, d.isocalendar().week) if pd.notna(d) else None
    ).isin(sel_yw)


# ---------------------------------------------------------------------------
# Filtros de período, oficina e semana (UI)
# ---------------------------------------------------------------------------

def _period_filter(
    df_acomp: pd.DataFrame,
    df_receb: pd.DataFrame,
    df_prod: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Renderiza seletores de período, oficina e semana.
    O multiselect de semanas lista apenas as semanas ISO dentro do intervalo
    de datas escolhido — muda dinamicamente conforme o período é ajustado.
    """
    all_dates = pd.concat(
        [
            df_acomp[_ACOMP_DATE].dropna(),
            df_receb[_RECEB_DATE].dropna(),
            df_prod[_PROD_DATE].dropna()
            if not df_prod.empty
            else pd.Series(dtype="datetime64[ns]"),
        ]
    )

    if all_dates.empty:
        return df_acomp, df_receb, df_prod

    min_d = all_dates.min().date()
    max_d = all_dates.max().date()

    all_oficinas = sorted(
        set(df_acomp[OFICINA_COL].dropna().unique())
        | set(df_receb[OFICINA_COL].dropna().unique())
        | (set(df_prod[OFICINA_COL].dropna().unique()) if not df_prod.empty else set())
    )
    all_oficinas = [o for o in all_oficinas if o and o.lower() != "nan"]

    col_dt, col_of, col_wk = st.columns([1.5, 2, 2])

    with col_dt:
        date_range = st.date_input(
            "Período de análise",
            value=(min_d, max_d),
            min_value=min_d,
            max_value=max_d,
            key="ader_period",
            format="DD/MM/YYYY",
        )

    with col_of:
        selected = utils.dropdown_filter(
            all_oficinas,
            key="ader_oficina",
            label="Oficina(s)",
            icon="🏭",
        )

    if not (isinstance(date_range, tuple) and len(date_range) == 2):
        return df_acomp, df_receb, df_prod

    start = pd.Timestamp(date_range[0])
    end = pd.Timestamp(date_range[1]) + pd.Timedelta(hours=23, minutes=59, seconds=59)

    # Semanas ISO disponíveis no intervalo selecionado
    week_set = sorted(
        set(
            (d.isocalendar().year, d.isocalendar().week)
            for d in pd.date_range(start=start, end=end, freq="D")
        )
    )
    week_options = [_week_label(y, w) for y, w in week_set]
    week_map = {_week_label(y, w): (y, w) for y, w in week_set}

    with col_wk:
        sel_week_labels = st.multiselect(
            "Semana(s) — dentro do período acima",
            options=week_options,
            default=[],
            key="ader_week",
            placeholder="Todas as semanas",
        )

    # Filtro de data
    fa = _filter_by_period(df_acomp, _ACOMP_DATE, start, end)
    fr = _filter_by_period(df_receb, _RECEB_DATE, start, end)
    fp = (
        _filter_by_period(df_prod, _PROD_DATE, start, end)
        if not df_prod.empty
        else df_prod
    )

    # Filtro de oficina
    if selected:
        fa = fa[fa[OFICINA_COL].isin(selected)]
        fr = fr[fr[OFICINA_COL].isin(selected)]
        if not fp.empty:
            fp = fp[fp[OFICINA_COL].isin(selected)]

    # Filtro de semana (aplicado sobre o resultado do filtro de data+oficina)
    if sel_week_labels:
        sel_yw = {week_map[lbl] for lbl in sel_week_labels}
        fa = fa[_in_iso_weeks(fa[_ACOMP_DATE], sel_yw)]
        fr = fr[_in_iso_weeks(fr[_RECEB_DATE], sel_yw)]
        if not fp.empty:
            fp = fp[_in_iso_weeks(fp[_PROD_DATE], sel_yw)]

    return fa, fr, fp


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------

def render(
    df_acomp: pd.DataFrame | None,
    df_receb: pd.DataFrame | None,
    df_prod: pd.DataFrame | None,
) -> None:
    utils.section_title("🔍 Aderência das Oficinas — Planejado × Recebido × Declarado")
    st.divider()

    if df_acomp is None or df_receb is None:
        st.info(
            "Carregue os arquivos **ACOMPANHAMENTO.xlsx** e **RECEBIMENTO.xlsx** "
            "na barra lateral para visualizar esta aba."
        )
        return

    if df_acomp.empty and df_receb.empty:
        st.warning("Nenhum dado encontrado nas bases de Programado e Recebido.")
        return

    df_acomp = df_acomp.copy()
    df_receb = df_receb.copy()
    df_prod = df_prod.copy() if df_prod is not None else pd.DataFrame()

    df_acomp[_ACOMP_DATE] = pd.to_datetime(df_acomp[_ACOMP_DATE], errors="coerce")
    df_receb[_RECEB_DATE] = pd.to_datetime(df_receb[_RECEB_DATE], errors="coerce")
    if not df_prod.empty and _PROD_DATE in df_prod.columns:
        df_prod[_PROD_DATE] = pd.to_datetime(df_prod[_PROD_DATE], errors="coerce")

    fa, fr, fp = _period_filter(df_acomp, df_receb, df_prod)

    if fa.empty and fr.empty:
        st.warning("Nenhum registro para o período selecionado.")
        return

    # ------------------------------------------------------------------ KPIs
    total_prog = int(fa[_ACOMP_QTD].sum())
    total_receb = int(fr[_RECEB_QTD].sum())
    total_decl = int(fp[_PROD_QTD].sum()) if not fp.empty and _PROD_QTD in fp.columns else 0

    utils.section_divider("Visão Geral")
    c1, c2, c3 = st.columns(3)
    with c1:
        utils.kpi_card("Programado (A Receber)", utils.format_int_br(total_prog))
    with c2:
        utils.kpi_card(
            "Recebido",
            utils.format_int_br(total_receb),
            help_text=f"Saldo pendente: {utils.format_int_br(total_prog - total_receb)} peças",
        )
    with c3:
        utils.kpi_card(
            "Declarado (Produção)",
            utils.format_int_br(total_decl),
            help_text="Autoinformado pelas oficinas",
        )

    # ------------------------------------------------ Tabela de aderência
    st.markdown("<br>", unsafe_allow_html=True)
    utils.section_divider("Resumo de Aderência por Oficina")
    #st.caption(
    #    "**Programado** = A Receber  ·  **Recebido** = entregue fisicamente  ·  "
    #    "**Declarado** = produção autoinformada  ·  "
    #    "**Gap Prog→Receb** = saldo pendente  ·  "
    #    "**Status** = 🟢 ≥95% · 🟡 ≥80% · 🔴 <80%"
    #)
    adh = build_adherence_table(fa, fr, fp)
    utils.render_html_table(
        adh,
        int_cols=["Programado", "Recebido", "Declarado", "Gap Prog→Receb", "Gap Decl→Receb"],
        max_height="320px",
    )

    # ------------------------------------------------ Gráfico comparativo
    utils.section_divider("Comparativo por Oficina — Programado × Recebido × Declarado")

    chart_df = (
        adh.set_index("Oficina")[["Programado", "Recebido", "Declarado"]]
        .sort_values("Programado", ascending=False)
    )
    plot_bar_grouped(chart_df, colors=_COLORS, height=400)

    # ------------------------------------------------ Cruzamento por Ordem
    utils.section_divider("Cruzamento por Ordem Mestre — A Receber × Recebido")
    st.caption(
        "Cada ordem da base **A Receber** é buscada em **Recebido** pelo mesmo "
        "número de Ordem Mestre + Oficina. Ordens sem correspondência = não entregues."
    )

    orders = build_orders_cross(fa, fr)

    if orders.empty:
        st.info("Nenhuma ordem encontrada no período selecionado.")
    else:
        status_counts = orders["Status"].value_counts()
        s1, s2, s3 = st.columns(3)
        with s1:
            utils.kpi_card("✅ Ordens Completas", str(status_counts.get("✅ Completo", 0)))
        with s2:
            utils.kpi_card("⚠️ Recebimento Parcial", str(status_counts.get("⚠️ Parcial", 0)))
        with s3:
            utils.kpi_card("❌ Não Entregues", str(status_counts.get("❌ Não Entregue", 0)))

        st.markdown("<br>", unsafe_allow_html=True)
        utils.render_html_table(
            orders,
            int_cols=["Programado", "Recebido", "Saldo"],
            float_cols=["% Recebido"],
            max_height="420px",
        )

        utils.download_button(
            orders,
            "aderencia_ordens.xlsx",
            oficina_col="Oficina",
            int_cols=["Programado", "Recebido", "Saldo"],
            float_cols=["% Recebido"],
            key="dl_ader",
        )
