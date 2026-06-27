"""
tests/test_data_prep.py
Testes unitarios das funcoes puras de core/data_prep.py.

Cobertura:
- format_int_br: separador de milhar pt-BR
- format_float_br: decimal pt-BR com troca . <-> ,
- format_date_br: DD/MM/AAAA, None e NaT retornam "---"
- clean_text_series: strip e remocao de \xa0
- filter_mp_polo: case-insensitive, com/sem espacos, preserva outros

Funcoes que dependem de contexto Streamlit (apply_filters, dropdown_filter)
nao sao testadas aqui -- requerem mock da sessao Streamlit.
"""
import pandas as pd
import pytest

from core.data_prep import (
    clean_text_series,
    filter_mp_polo,
    format_date_br,
    format_float_br,
    format_int_br,
)


# --------------------------------------------------------------------------- #
# format_int_br
# --------------------------------------------------------------------------- #
class TestFormatIntBr:
    def test_milhar(self):
        assert format_int_br(1000) == "1.000"

    def test_milhao(self):
        assert format_int_br(1_234_567) == "1.234.567"

    def test_zero(self):
        assert format_int_br(0) == "0"

    def test_float_arredonda(self):
        assert format_int_br(1234.9) == "1.235"

    def test_none_retorna_zero(self):
        assert format_int_br(None) == "0"

    def test_nan_retorna_zero(self):
        assert format_int_br(float("nan")) == "0"

    def test_pequeno(self):
        assert format_int_br(42) == "42"


# --------------------------------------------------------------------------- #
# format_float_br
# --------------------------------------------------------------------------- #
class TestFormatFloatBr:
    def test_decimal(self):
        assert format_float_br(1234.56) == "1.234,56"

    def test_zero(self):
        assert format_float_br(0) == "0,00"

    def test_negativo(self):
        assert format_float_br(-100.5) == "-100,50"

    def test_sem_milhar(self):
        assert format_float_br(9.99) == "9,99"

    def test_custom_decimals(self):
        assert format_float_br(1.5, decimals=1) == "1,5"

    def test_none_retorna_zero(self):
        assert format_float_br(None) == "0"


# --------------------------------------------------------------------------- #
# format_date_br
# --------------------------------------------------------------------------- #
class TestFormatDateBr:
    def test_timestamp(self):
        assert format_date_br(pd.Timestamp("2024-03-15")) == "15/03/2024"

    def test_string_date(self):
        assert format_date_br("2024-01-01") == "01/01/2024"

    def test_none(self):
        assert format_date_br(None) == "—"

    def test_nat(self):
        assert format_date_br(pd.NaT) == "—"

    def test_formato_dd_mm_aaaa(self):
        result = format_date_br(pd.Timestamp("2024-12-31"))
        assert result == "31/12/2024"
        assert len(result) == 10


# --------------------------------------------------------------------------- #
# clean_text_series
# --------------------------------------------------------------------------- #
class TestCleanTextSeries:
    def test_strip_espacos(self):
        s = pd.Series(["  ABC  ", "  XYZ"])
        result = clean_text_series(s)
        assert result[0] == "ABC"
        assert result[1] == "XYZ"

    def test_remove_nbsp(self):
        s = pd.Series(["\xa0TESTE\xa0"])
        result = clean_text_series(s)
        assert result[0] == "TESTE"

    def test_nbsp_interno(self):
        s = pd.Series(["A\xa0B"])
        result = clean_text_series(s)
        assert result[0] == "A B"

    def test_converte_none_para_string(self):
        s = pd.Series([None, "OK"])
        result = clean_text_series(s)
        assert result[1] == "OK"

    def test_serie_vazia(self):
        s = pd.Series([], dtype=str)
        result = clean_text_series(s)
        assert result.empty


# --------------------------------------------------------------------------- #
# filter_mp_polo
# --------------------------------------------------------------------------- #
class TestFilterMpPolo:
    def _df(self, mp_values, vals=None):
        if vals is None:
            vals = list(range(len(mp_values)))
        return pd.DataFrame({"MP": mp_values, "val": vals})

    def test_filtra_polo_exato(self):
        df = self._df(["POLO", "OUTROS", "JEANS"])
        result = filter_mp_polo(df)
        assert len(result) == 1
        assert result["val"].iloc[0] == 0

    def test_case_insensitive(self):
        df = self._df(["polo", "Polo", "POLO"])
        result = filter_mp_polo(df)
        assert len(result) == 3

    def test_strip_espacos(self):
        df = self._df([" POLO ", "  polo  "])
        result = filter_mp_polo(df)
        assert len(result) == 2

    def test_exclui_nao_polo(self):
        df = self._df(["OUTROS", "JEANS", "NYLON"])
        result = filter_mp_polo(df)
        assert result.empty

    def test_df_vazio(self):
        df = pd.DataFrame({"MP": pd.Series([], dtype=str), "val": []})
        result = filter_mp_polo(df)
        assert result.empty

    def test_reset_index(self):
        df = self._df(["OUTROS", "POLO", "OUTROS"])
        result = filter_mp_polo(df)
        assert list(result.index) == [0]

    def test_coluna_customizada(self):
        df = pd.DataFrame({"MATERIA": ["polo", "outros"], "x": [1, 2]})
        result = filter_mp_polo(df, mp_col="MATERIA")
        assert len(result) == 1
        assert result["x"].iloc[0] == 1
