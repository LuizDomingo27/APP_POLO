"""
core/database.py
Gerenciamento do banco de dados SQLite (Dataset/polo.db) e sincronização com GitHub.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path
import pandas as pd
import requests
import base64

# Configurações do arquivo de banco de dados
BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "Dataset" / "polo.db"

# Nomes de tabelas e mapeamentos
TABLE_ACOMP = "acompanhamento"
TABLE_RECEB = "recebimento"
TABLE_PROD = "producao_diaria"

def get_connection() -> sqlite3.Connection:
    """Retorna uma conexão ativa com o banco SQLite."""
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(DB_FILE))

def init_db() -> None:
    """Inicializa as tabelas do banco de dados SQLite com chaves primárias e índices."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Tabela acompanhamento (A Receber)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS "{TABLE_ACOMP}" (
                "ORDEM MESTRE" TEXT PRIMARY KEY,
                "OFICINA" TEXT,
                "ENVIO" TEXT,
                "QTD" INTEGER,
                "MINUTOS" REAL,
                "DEAD LINE" TEXT,
                "MP" TEXT
            )
        """)
        
        # 2. Tabela recebimento (Recebido)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS "{TABLE_RECEB}" (
                "ORDEM MESTRE" TEXT,
                "OFICINA" TEXT,
                "DIA" TEXT,
                "MP" TEXT,
                "REAL CORTADO" INTEGER,
                "MINUTOS" REAL,
                PRIMARY KEY ("ORDEM MESTRE", "DIA", "OFICINA")
            )
        """)
        
        # 3. Tabela producao_diaria (Produção Diária)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS "{TABLE_PROD}" (
                "OFICINA" TEXT,
                "DATA" TEXT,
                "QUANTIDADE DE PEÇAS PRODUZIDA" INTEGER,
                "WK" TEXT,
                PRIMARY KEY ("OFICINA", "DATA")
            )
        """)
        
        # 4. Criar índices secundários para melhorar performance de consultas/filtros
        cursor.execute(f'CREATE INDEX IF NOT EXISTS "idx_{TABLE_ACOMP}_mp_oficina" ON "{TABLE_ACOMP}" ("MP", "OFICINA")')
        cursor.execute(f'CREATE INDEX IF NOT EXISTS "idx_{TABLE_ACOMP}_envio" ON "{TABLE_ACOMP}" ("ENVIO")')
        
        cursor.execute(f'CREATE INDEX IF NOT EXISTS "idx_{TABLE_RECEB}_mp_oficina" ON "{TABLE_RECEB}" ("MP", "OFICINA")')
        cursor.execute(f'CREATE INDEX IF NOT EXISTS "idx_{TABLE_RECEB}_dia" ON "{TABLE_RECEB}" ("DIA")')
        
        cursor.execute(f'CREATE INDEX IF NOT EXISTS "idx_{TABLE_PROD}_oficina_data" ON "{TABLE_PROD}" ("OFICINA", "DATA")')
        
        conn.commit()

def load_table(table_name: str, filter_query: Optional[str] = None) -> pd.DataFrame:
    """Lê uma tabela do SQLite (opcionalmente filtrada) e retorna como DataFrame."""
    init_db()
    with get_connection() as conn:
        if filter_query:
            return pd.read_sql(f'SELECT * FROM "{table_name}" WHERE {filter_query}', conn)
        return pd.read_sql(f'SELECT * FROM "{table_name}"', conn)

def save_df_to_db(table_name: str, df: pd.DataFrame, mode: str = "replace") -> None:
    """
    Salva o DataFrame no banco SQLite.
    
    Parâmetros:
    - table_name: Nome da tabela.
    - df: DataFrame a ser salvo.
    - mode: 'replace' para substituir tudo, 'upsert' para atualizar/inserir (usando REPLACE do SQLite).
    """
    init_db()
    
    # Normalizar nomes de colunas substituindo \xa0 por espaços normais
    df = df.copy()
    df.columns = [str(c).replace("\xa0", " ").strip() for c in df.columns]
    
    # Limpar espaços em branco em colunas do tipo string
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()
            
    # Tratar valores vazios e datas (converter para string ISO)
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S").where(df[col].notna(), None)
            
    # Garantir valores nativos do Python que o sqlite3 entende
    df = df.replace({pd.NaT: None, float("nan"): None})
    records = df.to_numpy().tolist()
    records = [[None if pd.isna(x) else x for x in r] for r in records]
    
    cols = list(df.columns)
    col_names = ", ".join([f'"{c}"' for c in cols])
    placeholders = ", ".join(["?"] * len(cols))
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if mode == "replace":
            # Apagar dados atuais da tabela antes de inserir
            cursor.execute(f'DELETE FROM "{table_name}"')
            # Usar INSERT OR REPLACE para tolerar linhas duplicadas dentro do
            # próprio arquivo enviado (mesma chave primária aparecendo mais de
            # uma vez). Sem isso, a segunda duplicata viola a PRIMARY KEY.
            query = f'INSERT OR REPLACE INTO "{table_name}" ({col_names}) VALUES ({placeholders})'
        elif mode == "upsert":
            # Usar INSERT OR REPLACE do sqlite para chaves únicas / KEYS
            query = f'INSERT OR REPLACE INTO "{table_name}" ({col_names}) VALUES ({placeholders})'
        else:
            raise ValueError("Modo inválido. Use 'replace' ou 'upsert'.")
            
        cursor.executemany(query, records)
        conn.commit()

def sync_database_to_github() -> tuple[bool, str]:
    """
    Sincroniza o arquivo Dataset/polo.db com o repositório GitHub.
    Tenta usar comandos git locais primeiro. Se falhar ou estiver em Streamlit Cloud,
    tenta usar a API REST do GitHub se st.secrets["GITHUB_TOKEN"] estiver presente.
    """
    if not DB_FILE.exists():
        return False, "Arquivo de banco de dados não encontrado para sincronização."

    # 1. Tentar push via Git local (subprocesso)
    try:
        # Verificar se está em um repositório git
        git_dir = BASE_DIR / ".git"
        if git_dir.exists():
            # Configurar usuário temporário se não houver
            subprocess.run(["git", "config", "user.name", "Polo DB Sync"], cwd=str(BASE_DIR), capture_output=True)
            subprocess.run(["git", "config", "user.email", "polo-db-sync@example.com"], cwd=str(BASE_DIR), capture_output=True)
            
            # Adicionar e commitar
            subprocess.run(["git", "add", "Dataset/polo.db"], cwd=str(BASE_DIR), check=True, capture_output=True)
            commit_res = subprocess.run(
                ["git", "commit", "-m", "database: auto-update from Streamlit upload"],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True
            )
            
            if "nothing to commit" in commit_res.stdout or "nada para comitar" in commit_res.stdout:
                return True, "O banco de dados já está sincronizado com a versão local (sem alterações)."
                
            # Dar push
            subprocess.run(["git", "push"], cwd=str(BASE_DIR), check=True, capture_output=True)
            return True, "Banco de dados sincronizado com sucesso via Git local (Push)."
    except Exception as e:
        # Se falhar o push local (por exemplo, falta de chave SSH na nuvem), avança para a API do GitHub
        pass

    # 2. Tentar push via API REST do GitHub (caso haja segredos do Streamlit configurados)
    try:
        import streamlit as st
        # Verificar se os segredos necessários existem
        if "GITHUB_TOKEN" in st.secrets:
            token = st.secrets["GITHUB_TOKEN"]
            # Tentar obter nome do repositório a partir do git remoto
            repo = None
            try:
                remote_url = subprocess.check_output(
                    ["git", "config", "--get", "remote.origin.url"],
                    cwd=str(BASE_DIR),
                    text=True
                ).strip()
                if "github.com" in remote_url:
                    # Exemplo: https://github.com/LuizDomingo27/APP_POLO.git ou git@github.com:LuizDomingo27/APP_POLO.git
                    parts = remote_url.split("github.com")[-1].lstrip(":/").replace(".git", "").split("/")
                    if len(parts) >= 2:
                        repo = f"{parts[0]}/{parts[1]}"
            except Exception:
                pass
                
            if not repo:
                # Fallback para o repositório padrão do projeto
                repo = "LuizDomingo27/APP_POLO"
                
            path_in_repo = "Dataset/polo.db"
            
            # Ler conteúdo do banco de dados
            with open(DB_FILE, "rb") as f:
                content_bytes = f.read()
            encoded_content = base64.b64encode(content_bytes).decode("utf-8")
            
            # Consultar arquivo existente para obter o SHA atual (necessário para update na API)
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            api_url = f"https://api.github.com/repos/{repo}/contents/{path_in_repo}"
            
            sha = None
            get_res = requests.get(api_url, headers=headers)
            if get_res.status_code == 200:
                sha = get_res.json().get("sha")
                
            # Fazer a requisição PUT para atualizar o arquivo
            payload = {
                "message": "database: auto-update via GitHub API (Streamlit)",
                "content": encoded_content,
                "branch": "main"  # ou master
            }
            if sha:
                payload["sha"] = sha
                
            put_res = requests.put(api_url, headers=headers, json=payload)
            if put_res.status_code in [200, 201]:
                return True, f"Banco de dados sincronizado com sucesso via API do GitHub no repositório {repo}."
            else:
                return False, f"Falha na API do GitHub ({put_res.status_code}): {put_res.text}"
        else:
            return False, "Sincronização com o GitHub ignorada: GITHUB_TOKEN não configurado no Streamlit secrets."
    except Exception as e:
        return False, f"Erro inesperado durante sincronização com GitHub: {str(e)}"
