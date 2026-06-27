"""
app.py — APP_POLO
Painel de acompanhamento de MP = POLO: pedidos a receber, pedidos recebidos
e produção diária informada pelas oficinas.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from core import utils
from services import acompanhamento_service as acomp_svc
from services import producao_service as prod_svc
from services import recebimento_service as receb_svc

st.set_page_config(
    page_title="POLO • Painel de Acompanhamento",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded",
)

utils.inject_global_css()

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "Dataset"

ACOMP_FILE = DATASET_DIR / "ACOMPANHAMENTO.xlsx"
RECEB_FILE = DATASET_DIR / "RECEBIMENTO.xlsx"
PROD_FILE = DATASET_DIR / "Produção Diária - POLO.xlsx"

utils.app_header(
    "🧵 Painel POLO",
    "Acompanhamento consolidado de matéria-prima POLO — pedidos a receber, recebidos e produção diária das oficinas.",
    badge="MP = POLO",
)

# --------------------------------------------------------------------------- #
# Sidebar — fonte de dados
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown("### 📂 Fonte de Dados")
    st.caption("Os arquivos são lidos automaticamente da pasta `Dataset/`. Se algum não for encontrado, use o upload abaixo.")

    acomp_source = utils.resolve_data_source(ACOMP_FILE, "ACOMPANHAMENTO.xlsx", "upload_acomp")
    receb_source = utils.resolve_data_source(RECEB_FILE, "RECEBIMENTO.xlsx", "upload_receb")
    prod_source = utils.resolve_data_source(PROD_FILE, "Produção Diária - POLO.xlsx", "upload_prod")

    st.markdown("---")
    st.caption("💡 Os filtros de período e oficina ficam disponíveis dentro de cada aba.")

# --------------------------------------------------------------------------- #
# Carregamento dos dados (com cache)
# --------------------------------------------------------------------------- #
df_acomp = acomp_svc.load_polo_data(acomp_source) if acomp_source else None
df_receb = receb_svc.load_polo_data(receb_source) if receb_source else None
df_prod = prod_svc.load_data(prod_source) if prod_source else None

# --------------------------------------------------------------------------- #
# Abas
# --------------------------------------------------------------------------- #
tab1, tab2, tab3 = st.tabs(["📦 A Receber", "✅ Recebido", "🏭 Produção Diária"])

with tab1:
    acomp_svc.render(df_acomp)

with tab2:
    receb_svc.render(df_receb)

with tab3:
    prod_svc.render(df_prod)
