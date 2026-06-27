# CLAUDE.md — APP_POLO

Guia de desenvolvimento para o painel de acompanhamento de MP = POLO.

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Os arquivos de dados sao lidos automaticamente de `Dataset/`. Se nao existirem,
o app exibe um uploader na sidebar.

## Como rodar os testes

```bash
pip install pytest
pytest tests/ -v
```

## Arquitetura

```
APP_POLO/
├── app.py                  # Orquestracao: config de pagina, sidebar, abas
├── core/
│   ├── constants.py        # Constantes de colunas compartilhadas entre servicos
│   ├── data_prep.py        # Normalizacao, filtros, formatacao pt-BR (testavel puro)
│   ├── ui.py               # CSS global, KPI cards, tabela HTML, resolve_data_source
│   ├── charts.py           # Graficos ECharts (plot_bar, plot_line)
│   ├── export.py           # Exportacao Excel (.xlsx) agrupado + detalhado
│   └── utils.py            # Hub de re-exportacao (backward compat -- nao editar)
├── services/
│   ├── acompanhamento_service.py   # ABA 1: A Receber (ACOMPANHAMENTO.xlsx)
│   ├── recebimento_service.py      # ABA 2: Recebido (RECEBIMENTO.xlsx)
│   └── producao_service.py         # ABA 3: Producao Diaria (BD aba)
├── tests/
│   ├── test_data_prep.py   # Testes unitarios de core/data_prep.py
│   └── test_export.py      # Testes de integracao de core/export.py
└── Dataset/
    ├── ACOMPANHAMENTO.xlsx
    ├── RECEBIMENTO.xlsx
    └── Producao Diaria - POLO.xlsx
```

## Como adicionar uma nova aba

1. Crie `services/novo_servico.py`:
   - Defina `SHEET_NAME`, `DATE_COL` e colunas especificas.
   - Importe constantes compartilhadas de `core.constants`.
   - Implemente `load_data(source)` com `@st.cache_data`.
   - Implemente `render(df)` chamando `utils.*`.

2. Registre em `app.py`:
   ```python
   from services import novo_servico as novo_svc
   novo_source = utils.resolve_data_source(NOVO_FILE, "Novo.xlsx", "upload_novo")
   df_novo = novo_svc.load_data(novo_source) if novo_source else None
   # dentro do st.tabs([..., "Nova Aba"]):
   with tab4:
       novo_svc.render(df_novo)
   ```

3. Adicione o arquivo `.xlsx` em `Dataset/`.

## Convencoes de colunas

| Constante (core/constants.py) | Valor            | Presente em  |
|-------------------------------|------------------|--------------|
| `OFICINA_COL`                 | `"OFICINA"`      | Todos        |
| `ORDEM_COL`                   | `"ORDEM MESTRE"` | ACOMP, RECEB |
| `MINUTOS_COL`                 | `"MINUTOS"`      | ACOMP, RECEB |
| `MP_COL`                      | `"MP"`           | ACOMP, RECEB |
| `MP_VALUE`                    | `"POLO"`         | Filtro MP    |

Constantes especificas de cada servico (DATE_COL, QTD_COL, SHEET_NAME) ficam
no proprio arquivo de servico.

## Graficos (ECharts)

Os graficos usam Apache ECharts 5 via CDN, renderizados como HTML inline.
Veja `core/charts.py` para detalhes de cada opcao.

- `plot_bar(series, title, color)`: barras com rotulos no topo.
- `plot_line(series, title, color, ma_window)`: linha + media movel tracejada.

Para customizar cores, passe `color="#HEX"`. Padrao: `#2EE6C0`.

## Exportacao Excel

`core/export.py` gera `.xlsx` com duas abas:
- **Resumo Diario**: agrupado por Data+Oficina, linha TOTAL com formula SUM.
- **Detalhado**: registro a registro.

## Tema visual

Paleta principal (CSS vars em `core/ui.py` > `inject_global_css`):
- `--accent: #2EE6C0` — verde-cyano (destaque, barras, KPI)
- `--bg-base: #0B131C` — fundo principal
- `--text-main: #E7F1F0` — texto principal
- `--text-muted: #7C95A0` — texto secundario

A paleta do Excel em `core/export.py` espelha as mesmas cores.

## O que NAO esta coberto por testes automaticos

Funcoes que dependem de contexto Streamlit ativo (widgets, session_state):
- `apply_filters`, `dropdown_filter` (usam st.selectbox, st.date_input)
- `inject_global_css`, `kpi_card`, `render_html_table` (usam st.markdown)
- `plot_bar`, `plot_line` (usam st.components.v1.html)

Para verificar: execute `streamlit run app.py` e valide visualmente cada aba.
