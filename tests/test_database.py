"""
tests/test_database.py
Testes unitários e de integração para as operações de banco de dados em core/database.py.
"""
from __future__ import annotations

import os
import sqlite3
import pandas as pd
import pytest
from pathlib import Path

import core.database as db

@pytest.fixture
def temp_db(tmp_path):
    """Fixture que cria um banco de dados temporário para os testes."""
    original_db_file = db.DB_FILE
    # Apontar o DB_FILE do módulo para a pasta temporária do pytest
    db.DB_FILE = tmp_path / "test_polo.db"
    
    # Inicializar o banco de dados
    db.init_db()
    
    yield db.DB_FILE
    
    # Restaurar a configuração original
    db.DB_FILE = original_db_file

class TestDatabaseOperations:
    
    def test_init_db_creates_tables(self, temp_db):
        """Verifica se a inicialização cria as tabelas corretas."""
        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cursor.fetchall()]
            
            assert db.TABLE_ACOMP in tables
            assert db.TABLE_RECEB in tables
            assert db.TABLE_PROD in tables

    def test_save_df_to_db_replace(self, temp_db):
        """Verifica se o modo 'replace' limpa a tabela e insere os novos dados."""
        # 1. Inserir dados iniciais
        df1 = pd.DataFrame({
            "ORDEM MESTRE": ["1001", "1002"],
            "OFICINA": ["Oficina A", "Oficina B"],
            "ENVIO": ["2026-06-01", "2026-06-02"],
            "QTD": [100, 200],
            "MINUTOS": [10.0, 20.0],
            "DEAD LINE": ["2026-06-10", "2026-06-12"],
            "MP": ["POLO", "POLO"]
        })
        db.save_df_to_db(db.TABLE_ACOMP, df1, mode="replace")
        
        # Verificar inserção
        loaded_df = db.load_table(db.TABLE_ACOMP)
        assert len(loaded_df) == 2
        assert list(loaded_df["ORDEM MESTRE"]) == ["1001", "1002"]
        
        # 2. Executar replace com novos dados (deve apagar os antigos)
        df2 = pd.DataFrame({
            "ORDEM MESTRE": ["1003"],
            "OFICINA": ["Oficina C"],
            "ENVIO": ["2026-06-03"],
            "QTD": [300],
            "MINUTOS": [30.0],
            "DEAD LINE": ["2026-06-15"],
            "MP": ["POLO"]
        })
        db.save_df_to_db(db.TABLE_ACOMP, df2, mode="replace")
        
        loaded_df2 = db.load_table(db.TABLE_ACOMP)
        assert len(loaded_df2) == 1
        assert loaded_df2["ORDEM MESTRE"].iloc[0] == "1003"
        assert loaded_df2["OFICINA"].iloc[0] == "Oficina C"

    def test_save_df_to_db_upsert_acomp(self, temp_db):
        """Verifica o comportamento de UPSERT (REPLACE do SQLite) para acompanhamento (chave: ORDEM MESTRE)."""
        df1 = pd.DataFrame({
            "ORDEM MESTRE": ["1001", "1002"],
            "OFICINA": ["Oficina A", "Oficina B"],
            "ENVIO": ["2026-06-01", "2026-06-02"],
            "QTD": [100, 200],
            "MINUTOS": [10.0, 20.0],
            "DEAD LINE": ["2026-06-10", "2026-06-12"],
            "MP": ["POLO", "POLO"]
        })
        db.save_df_to_db(db.TABLE_ACOMP, df1, mode="replace")
        
        # DataFrame de atualização contendo um ID novo e um existente com dados mudados
        df_update = pd.DataFrame({
            "ORDEM MESTRE": ["1001", "1003"],
            "OFICINA": ["Oficina A Modificada", "Oficina C"],
            "ENVIO": ["2026-06-01", "2026-06-03"],
            "QTD": [150, 300],
            "MINUTOS": [15.0, 30.0],
            "DEAD LINE": ["2026-06-10", "2026-06-15"],
            "MP": ["POLO", "POLO"]
        })
        
        db.save_df_to_db(db.TABLE_ACOMP, df_update, mode="upsert")
        
        loaded = db.load_table(db.TABLE_ACOMP)
        assert len(loaded) == 3
        
        # Verificar se 1001 foi atualizada
        row_1001 = loaded[loaded["ORDEM MESTRE"] == "1001"].iloc[0]
        assert row_1001["OFICINA"] == "Oficina A Modificada"
        assert row_1001["QTD"] == 150
        
        # Verificar se 1002 permaneceu intacta
        row_1002 = loaded[loaded["ORDEM MESTRE"] == "1002"].iloc[0]
        assert row_1002["OFICINA"] == "Oficina B"
        
        # Verificar se 1003 foi inserida
        row_1003 = loaded[loaded["ORDEM MESTRE"] == "1003"].iloc[0]
        assert row_1003["OFICINA"] == "Oficina C"

    def test_save_df_to_db_upsert_receb(self, temp_db):
        """Verifica o comportamento de UPSERT para recebimento (chave: ORDEM MESTRE, DIA, OFICINA)."""
        df1 = pd.DataFrame({
            "ORDEM MESTRE": ["1001", "1001"],
            "OFICINA": ["Oficina A", "Oficina A"],
            "DIA": ["2026-06-01", "2026-06-02"],
            "MP": ["POLO", "POLO"],
            "REAL CORTADO": [50, 60],
            "MINUTOS": [5.0, 6.0]
        })
        db.save_df_to_db(db.TABLE_RECEB, df1, mode="replace")
        
        # Update: Altera a quantidade do dia 2026-06-02 e adiciona um dia 2026-06-03
        df_update = pd.DataFrame({
            "ORDEM MESTRE": ["1001", "1001"],
            "OFICINA": ["Oficina A", "Oficina A"],
            "DIA": ["2026-06-02", "2026-06-03"],
            "MP": ["POLO", "POLO"],
            "REAL CORTADO": [99, 70],
            "MINUTOS": [9.9, 7.0]
        })
        
        db.save_df_to_db(db.TABLE_RECEB, df_update, mode="upsert")
        
        loaded = db.load_table(db.TABLE_RECEB)
        assert len(loaded) == 3
        
        # Verificar se dia 02 foi atualizado
        row_dia2 = loaded[(loaded["ORDEM MESTRE"] == "1001") & (loaded["DIA"] == "2026-06-02")].iloc[0]
        assert row_dia2["REAL CORTADO"] == 99
        
        # Verificar se dia 01 permaneceu inalterado
        row_dia1 = loaded[(loaded["ORDEM MESTRE"] == "1001") & (loaded["DIA"] == "2026-06-01")].iloc[0]
        assert row_dia1["REAL CORTADO"] == 50
