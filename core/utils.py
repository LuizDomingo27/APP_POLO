"""
core/utils.py
Hub de re-exportacao para compatibilidade com o codigo existente.

Os servicos importam `from core import utils` e chamam `utils.plot_bar(...)`,
`utils.format_int_br(...)` etc. Este arquivo re-exporta tudo dos modulos
especializados sem duplicar implementacao, de modo que as importacoes
existentes continuam funcionando sem nenhuma alteracao nos servicos.

Modulos especializados (edite-os diretamente para novas funcionalidades):
- core/constants.py  — constantes de colunas e valores compartilhados
- core/data_prep.py  — normalizacao, filtros e formatacao pt-BR
- core/ui.py         — CSS, KPI cards, tabela HTML, resolve_data_source
- core/charts.py     — graficos ECharts (barras e linhas)
- core/export.py     — exportacao Excel (.xlsx)
"""
from core.charts import plot_bar, plot_line
from core.data_prep import (
    apply_filters,
    clean_text_series,
    dropdown_filter,
    filter_mp_polo,
    format_date_br,
    format_float_br,
    format_int_br,
)
from core.export import build_grouped_summary, download_button, to_excel_bytes_grouped
from core.ui import (
    app_header,
    inject_global_css,
    kpi_card,
    render_html_table,
    resolve_data_source,
    section_divider,
    section_title,
)

__all__ = [
    # data_prep
    "clean_text_series",
    "filter_mp_polo",
    "format_int_br",
    "format_float_br",
    "format_date_br",
    "dropdown_filter",
    "apply_filters",
    # ui
    "inject_global_css",
    "app_header",
    "section_title",
    "section_divider",
    "kpi_card",
    "render_html_table",
    "resolve_data_source",
    # charts
    "plot_bar",
    "plot_line",
    # export
    "build_grouped_summary",
    "to_excel_bytes_grouped",
    "download_button",
]
