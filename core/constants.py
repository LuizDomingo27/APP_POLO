"""
core/constants.py
Constantes de colunas e valores compartilhados entre todos os serviços.

Por que centralizar aqui:
- Nomes de colunas das planilhas aparecem em múltiplos serviços; se a
  planilha mudar um cabeçalho, basta atualizar este arquivo.
- Valores de filtro (ex.: MP_VALUE = "POLO") ficam num único lugar para
  evitar strings mágicas espalhadas pelo código.

Constantes específicas de cada serviço (sheet name, colunas únicas) ficam
no próprio arquivo de serviço — não colocar aqui o que é exclusivo de uma aba.
"""

# --------------------------------------------------------------------------- #
# Matéria-prima
# --------------------------------------------------------------------------- #
MP_COL: str = "MP"
MP_VALUE: str = "POLO"  # valor esperado após normalização (upper, strip)

# --------------------------------------------------------------------------- #
# Colunas comuns a dois ou mais serviços
# --------------------------------------------------------------------------- #
OFICINA_COL: str = "OFICINA"       # presente em ACOMPANHAMENTO, RECEBIMENTO e BD
ORDEM_COL: str = "ORDEM MESTRE"    # presente em ACOMPANHAMENTO e RECEBIMENTO
MINUTOS_COL: str = "MINUTOS"       # presente em ACOMPANHAMENTO e RECEBIMENTO
