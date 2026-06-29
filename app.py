"""
app.py — APP_POLO
Painel de acompanhamento de MP = POLO com banco de dados SQLite e sincronização com GitHub.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd

from core import utils
from core.constants import OFICINA_COL, ORDEM_COL
from core.database import (
    save_df_to_db,
    sync_database_to_github,
    load_table,
    TABLE_ACOMP,
    TABLE_RECEB,
    TABLE_PROD,
)

from services import producao_service as prod_svc
from services import aderencia_service as ader_svc

st.set_page_config(
    page_title="Acompanhamento POLO",
    page_icon=":material/settings:",
    layout="wide",
    initial_sidebar_state="expanded",
)

utils.inject_global_css()

# Colunas esperadas para cada tabela (garante validação e filtro)
ACOMP_COLS = ["ORDEM MESTRE", "OFICINA", "ENVIO", "QTD", "MINUTOS", "DEAD LINE", "MP"]
RECEB_COLS = ["ORDEM MESTRE", "OFICINA", "DIA", "MP", "REAL CORTADO", "MINUTOS"]
PROD_COLS = ["OFICINA", "DATA", "QUANTIDADE DE PEÇAS PRODUZIDA", "WK"]


# --------------------------------------------------------------------------- #
# Loaders de dados (mantidos no banco para análises de aderência)
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Carregando A Receber...")
def _load_acomp() -> pd.DataFrame:
    df = load_table(TABLE_ACOMP, filter_query="UPPER(TRIM(MP)) = 'POLO'")
    df[OFICINA_COL] = utils.clean_text_series(df[OFICINA_COL])
    df = utils.filter_mp_polo(df, mp_col="MP")
    df["ENVIO"] = pd.to_datetime(df["ENVIO"], errors="coerce")
    df["DEAD LINE"] = pd.to_datetime(df["DEAD LINE"], errors="coerce")
    return df


@st.cache_data(show_spinner="Carregando Recebido...")
def _load_receb() -> pd.DataFrame:
    df = load_table(TABLE_RECEB, filter_query="UPPER(TRIM(MP)) = 'POLO'")
    df[OFICINA_COL] = utils.clean_text_series(df[OFICINA_COL])
    df[ORDEM_COL] = df[ORDEM_COL].astype(str).str.strip()
    df = utils.filter_mp_polo(df, mp_col="MP")
    df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")
    return df


# --------------------------------------------------------------------------- #
# Sidebar — Navegação e Informações do Banco
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown("### :material/menu: Navegação")
    page = st.radio(
        "Navegar para:",
        ["Painel de Acompanhamento", "📤 Carregar Dados (Planilhas)"],
        index=0
    )

    st.markdown("---")
    st.markdown("### 💾 Banco de Dados")

    if st.button("🔄 Limpar Cache / Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.toast("Cache do Streamlit limpo com sucesso!")

    st.markdown("---")
    st.caption("💡 Os filtros de período e oficina ficam disponíveis dentro do painel.")


# --------------------------------------------------------------------------- #
# Renderização da Página Ativa
# --------------------------------------------------------------------------- #
if page == "Painel de Acompanhamento":
    df_acomp = _load_acomp()
    df_receb = _load_receb()
    df_prod = prod_svc.load_data()

    tab1, tab2 = st.tabs(["🏭 Produção Diária", "🔍 Aderência das Oficinas"])

    with tab1:
        prod_svc.render(df_prod)

    with tab2:
        ader_svc.render(df_acomp, df_receb, df_prod)

elif page == "📤 Carregar Dados (Planilhas)":
    utils.app_header(
        "Carregar & Sincronizar",
        badge="Faça upload das planilhas Excel para atualizar as tabelas do banco de dados.",
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("<h4 style='font-family: Sora; color:var(--text-main);'>📦 A Receber</h4>", unsafe_allow_html=True)
        st.caption("Tabela: acompanhamento")
        acomp_file = st.file_uploader("Arquivo ACOMPANHAMENTO.xlsx", type=["xlsx"], key="up_acomp")
        acomp_mode = st.selectbox(
            "Estratégia de Carga",
            ["Atualizar/Mesclar (Upsert)", "Substituir Tudo (Replace)"],
            key="mode_acomp"
        )

    with col2:
        st.markdown("<h4 style='font-family: Sora; color:var(--text-main);'>✅ Recebido</h4>", unsafe_allow_html=True)
        st.caption("Tabela: recebimento")
        receb_file = st.file_uploader("Arquivo RECEBIMENTO.xlsx", type=["xlsx"], key="up_receb")
        receb_mode = st.selectbox(
            "Estratégia de Carga",
            ["Atualizar/Mesclar (Upsert)", "Substituir Tudo (Replace)"],
            key="mode_receb"
        )

    with col3:
        st.markdown("<h4 style='font-family: Sora; color:var(--text-main);'>🏭 Produção Diária</h4>", unsafe_allow_html=True)
        st.caption("Tabela: producao_diaria")
        prod_file = st.file_uploader("Arquivo Produção Diária - POLO.xlsx", type=["xlsx"], key="up_prod")
        prod_mode = st.selectbox(
            "Estratégia de Carga",
            ["Atualizar/Mesclar (Upsert)", "Substituir Tudo (Replace)"],
            key="mode_prod"
        )

    st.markdown("---")

    if st.button("🚀 Processar Uploads", type="primary", use_container_width=True):
        uploads = [
            ("A Receber (Acompanhamento)", acomp_file, TABLE_ACOMP, ACOMP_COLS, acomp_mode, "ACOMPANHAMENTO"),
            ("Recebido (Recebimento)", receb_file, TABLE_RECEB, RECEB_COLS, receb_mode, "RECEBIMENTO"),
            ("Produção Diária", prod_file, TABLE_PROD, PROD_COLS, prod_mode, "BD")
        ]

        any_uploaded = False
        errors = []
        successes = []

        for label, file, table_name, expected_cols, mode_label, sheet_name in uploads:
            if file is not None:
                any_uploaded = True
                try:
                    df = pd.read_excel(file, sheet_name=sheet_name)

                    df.columns = [str(c).replace("\xa0", " ").strip() for c in df.columns]

                    missing = [c for c in expected_cols if c not in df.columns]
                    if missing:
                        errors.append(f"**{label}**: Colunas ausentes no arquivo: {', '.join(missing)}")
                        continue

                    df_to_save = df[expected_cols]

                    if "OFICINA" in df_to_save.columns:
                        df_to_save = df_to_save.copy()
                        df_to_save["OFICINA"] = df_to_save["OFICINA"].astype(str).str.replace("\xa0", " ", regex=False).str.strip()

                    if "ORDEM MESTRE" in df_to_save.columns:
                        df_to_save = df_to_save.copy()
                        df_to_save["ORDEM MESTRE"] = df_to_save["ORDEM MESTRE"].astype(str).str.strip()

                    db_mode = "upsert" if "Upsert" in mode_label else "replace"
                    save_df_to_db(table_name, df_to_save, mode=db_mode)

                    successes.append(f"**{label}**: Carga executada com sucesso usando a estratégia de **{db_mode.upper()}** ({len(df_to_save)} registros).")
                except Exception as e:
                    errors.append(f"**{label}**: Erro ao processar o arquivo: {str(e)}")

        if not any_uploaded:
            st.warning("Nenhum arquivo foi selecionado para upload. Selecione um arquivo .xlsx acima para continuar.")
        else:
            for success_msg in successes:
                st.success(success_msg)
            for error_msg in errors:
                st.error(error_msg)

            if successes and not errors:
                st.cache_data.clear()

                st.info("🔄 Iniciando sincronização do banco de dados com o GitHub...")
                sync_ok, sync_msg = sync_database_to_github()

                if sync_ok:
                    st.success(f"✅ **Sincronização Concluída:** {sync_msg}")
                else:
                    st.warning(f"⚠️ **Banco de dados atualizado localmente, mas a sincronização falhou:** {sync_msg}")
