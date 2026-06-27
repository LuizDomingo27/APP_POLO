"""
app.py — APP_POLO
Painel de acompanhamento de MP = POLO com banco de dados SQLite e sincronização com GitHub.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
from pathlib import Path

from core import utils
from core.database import (
    save_df_to_db,
    sync_database_to_github,
    TABLE_ACOMP,
    TABLE_RECEB,
    TABLE_PROD
)
from services import acompanhamento_service as acomp_svc
from services import recebimento_service as receb_svc
from services import producao_service as prod_svc

st.set_page_config(
    page_title="POLO • Painel de Acompanhamento",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded",
)

utils.inject_global_css()

# Colunas esperadas para cada tabela (garante validação e filtro)
ACOMP_COLS = ["ORDEM MESTRE", "OFICINA", "ENVIO", "QTD", "MINUTOS", "DEAD LINE", "MP"]
RECEB_COLS = ["ORDEM MESTRE", "OFICINA", "DIA", "MP", "REAL CORTADO", "MINUTOS"]
PROD_COLS = ["OFICINA", "DATA", "QUANTIDADE DE PEÇAS PRODUZIDA", "WK"]

# --------------------------------------------------------------------------- #
# Sidebar — Navegação e Informações do Banco
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown("### 🧭 Menu")
    page = st.radio(
        "Navegar para:",
        ["📊 Painel de Acompanhamento", "📤 Carregar Dados (Planilhas)"],
        index=0
    )
    
    st.markdown("---")
    st.markdown("### 💾 Banco de Dados")
    st.caption("Tecnologia: **SQLite (Dataset/polo.db)**")
    
    if st.button("🔄 Limpar Cache / Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.toast("Cache do Streamlit limpo com sucesso!")
        
    st.markdown("---")
    st.caption("💡 Os filtros de período e oficina ficam disponíveis dentro do painel.")

# --------------------------------------------------------------------------- #
# Renderização da Página Ativa
# --------------------------------------------------------------------------- #
if page == "📊 Painel de Acompanhamento":
    utils.app_header(
        "🧵 Painel POLO",
        "Acompanhamento consolidado de matéria-prima POLO — pedidos a receber, recebidos e produção diária das oficinas.",
        badge="Fonte: SQLite Database",
    )
    
    # Carregamento de dados a partir do SQLite (com cache do Streamlit)
    df_acomp = acomp_svc.load_polo_data()
    df_receb = receb_svc.load_polo_data()
    df_prod = prod_svc.load_data()
    
    tab1, tab2, tab3 = st.tabs(["📦 A Receber", "✅ Recebido", "🏭 Produção Diária"])
    
    with tab1:
        acomp_svc.render(df_acomp)
        
    with tab2:
        receb_svc.render(df_receb)
        
    with tab3:
        prod_svc.render(df_prod)

elif page == "📤 Carregar Dados (Planilhas)":
    utils.app_header(
        "📤 Carregar & Sincronizar",
        "Faça upload das planilhas Excel para atualizar as tabelas do banco SQLite e sincronizar no GitHub.",
        badge="Mapeamento com Chaves Únicas",
    )
    
    st.markdown(
        """
        <div style="background-color: var(--surface); padding: 1.2rem; border-radius: var(--radius-md); border: 1px solid rgba(46,230,192,0.1); margin-bottom: 1.5rem;">
            <h4 style="margin-top: 0; color: var(--accent); font-family: 'Sora', sans-serif;">Como funciona a atualização?</h4>
            <p style="font-size: 0.9rem; margin-bottom: 0;">
                Escolha o arquivo Excel correspondente e defina a estratégia:
                <br>• <b>Atualizar/Mesclar (Upsert)</b>: Utiliza a instrução <code>REPLACE</code> do SQLite baseando-se nas chaves únicas (como ORDEM MESTRE e DIA) para atualizar registros que mudaram e inserir novas linhas sem gerar duplicatas.
                <br>• <b>Substituir Tudo (Replace)</b>: Limpa a tabela correspondente e carrega apenas os dados presentes no arquivo enviado.
            </p>
        </div>
        """,
        unsafe_allow_html=True
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
    
    if st.button("🚀 Processar Uploads & Sincronizar com GitHub", type="primary", use_container_width=True):
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
                    
                    # Normalizar colunas do dataframe enviado
                    df.columns = [str(c).replace("\xa0", " ").strip() for c in df.columns]
                    
                    # Validar se as colunas necessárias estão presentes
                    missing = [c for c in expected_cols if c not in df.columns]
                    if missing:
                        errors.append(f"**{label}**: Colunas ausentes no arquivo: {', '.join(missing)}")
                        continue
                        
                    # Filtrar apenas as colunas mapeadas no SQLite
                    df_to_save = df[expected_cols]
                    
                    # Adicionalmente limpar a coluna Oficina
                    if "OFICINA" in df_to_save.columns:
                        df_to_save = df_to_save.copy()
                        df_to_save["OFICINA"] = df_to_save["OFICINA"].astype(str).str.replace("\xa0", " ", regex=False).str.strip()
                        
                    # Converter tipo de chave de ordem para string em acompanhamento/recebimento para evitar problemas
                    if "ORDEM MESTRE" in df_to_save.columns:
                        df_to_save = df_to_save.copy()
                        df_to_save["ORDEM MESTRE"] = df_to_save["ORDEM MESTRE"].astype(str).str.strip()
                    
                    # Executar salvamento no SQLite
                    db_mode = "upsert" if "Upsert" in mode_label else "replace"
                    save_df_to_db(table_name, df_to_save, mode=db_mode)
                    
                    successes.append(f"**{label}**: Carga executada com sucesso usando a estratégia de **{db_mode.upper()}** ({len(df_to_save)} registros).")
                except Exception as e:
                    errors.append(f"**{label}**: Erro ao processar o arquivo: {str(e)}")
                    
        if not any_uploaded:
            st.warning("Nenhum arquivo foi selecionado para upload. Selecione um arquivo .xlsx acima para continuar.")
        else:
            # Exibir sucessos e erros das cargas locais
            for success_msg in successes:
                st.success(success_msg)
            for error_msg in errors:
                st.error(error_msg)
                
            if successes and not errors:
                # Limpar o cache de dados do Streamlit para refletir imediatamente no painel
                st.cache_data.clear()
                
                # Executar sincronização com o GitHub
                st.info("🔄 Iniciando sincronização do banco de dados com o GitHub...")
                sync_ok, sync_msg = sync_database_to_github()
                
                if sync_ok:
                    st.success(f"✅ **Sincronização Concluída:** {sync_msg}")
                else:
                    st.warning(f"⚠️ **Banco de dados atualizado localmente, mas a sincronização falhou:** {sync_msg}")
