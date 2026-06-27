"""
scripts/migrate_to_sqlite.py
Carga inicial das planilhas Excel (Dataset/*.xlsx) para o banco SQLite (Dataset/polo.db).
"""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

# Adicionar a pasta raiz ao sys.path para conseguir importar de core
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from core.database import save_df_to_db, init_db, TABLE_ACOMP, TABLE_RECEB, TABLE_PROD

def migrate():
    dataset_dir = BASE_DIR / "Dataset"
    
    # Arquivos padrão
    acomp_file = dataset_dir / "ACOMPANHAMENTO.xlsx"
    receb_file = dataset_dir / "RECEBIMENTO.xlsx"
    prod_file = dataset_dir / "Produção Diária - POLO.xlsx"
    
    print("Inicializando banco de dados SQLite...")
    init_db()
    
    # 1. Migrar Acompanhamento
    if acomp_file.exists():
        print(f"Lendo {acomp_file.name}...")
        df_acomp = pd.read_excel(acomp_file, sheet_name="ACOMPANHAMENTO")
        print(f"Salvando {len(df_acomp)} registros na tabela '{TABLE_ACOMP}'...")
        save_df_to_db(TABLE_ACOMP, df_acomp, mode="replace")
        print("Acompanhamento migrado com sucesso.")
    else:
        print(f"Aviso: Arquivo {acomp_file.name} não encontrado. Pulando.")
        
    # 2. Migrar Recebimento
    if receb_file.exists():
        print(f"Lendo {receb_file.name}...")
        df_receb = pd.read_excel(receb_file, sheet_name="RECEBIMENTO")
        # Remover duplicados exatos para evitar falha de chave primária na primeira carga
        dup_keys = ["ORDEM MESTRE", "DIA", "OFICINA"]
        df_receb.columns = [str(c).replace("\xa0", " ").strip() for c in df_receb.columns]
        df_receb["ORDEM MESTRE"] = df_receb["ORDEM MESTRE"].astype(str).str.strip()
        df_receb["OFICINA"] = df_receb["OFICINA"].astype(str).str.strip()
        
        # Deduplicar
        initial_len = len(df_receb)
        df_receb = df_receb.drop_duplicates(subset=dup_keys, keep="first")
        dedup_len = len(df_receb)
        if initial_len != dedup_len:
            print(f"Deduplicados {initial_len - dedup_len} registros idênticos em recebimento.")
            
        print(f"Salvando {len(df_receb)} registros na tabela '{TABLE_RECEB}'...")
        save_df_to_db(TABLE_RECEB, df_receb, mode="replace")
        print("Recebimento migrado com sucesso.")
    else:
        print(f"Aviso: Arquivo {receb_file.name} não encontrado. Pulando.")
        
    # 3. Migrar Produção Diária
    if prod_file.exists():
        print(f"Lendo {prod_file.name}...")
        df_prod = pd.read_excel(prod_file, sheet_name="BD")
        print(f"Salvando {len(df_prod)} registros na tabela '{TABLE_PROD}'...")
        save_df_to_db(TABLE_PROD, df_prod, mode="replace")
        print("Produção Diária migrada com sucesso.")
    else:
        print(f"Aviso: Arquivo {prod_file.name} não encontrado. Pulando.")
        
    print("\nMigração concluída com sucesso!")

if __name__ == "__main__":
    migrate()
