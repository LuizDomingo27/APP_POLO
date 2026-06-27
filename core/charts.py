"""
core/charts.py
Gráficos interativos via Apache ECharts 5 (CDN), renderizados como HTML
inline no Streamlit através de st.components.v1.html.

Por que ECharts e não Plotly/Altair:
- Tooltip totalmente customizável em JavaScript (incluindo formatação pt-BR).
- Controle pixel-perfect do tema sem conflito com o CSS global do app.
- Biblioteca leve (~1 MB minificado) entregue por CDN.

Estrutura de cada função de gráfico:
1. Prepara os dados em Python (serializa para JSON).
2. Constrói a string `var option = {...}` em JavaScript.
3. Chama _echarts_wrap() que envolve tudo numa página HTML mínima.
4. Renderiza com st.components.v1.html (iframe isolado do app principal).
"""
from __future__ import annotations

import json as _json

import pandas as pd
import streamlit.components.v1 as _cv1


# --------------------------------------------------------------------------- #
# Constantes de tema — manter sincronizadas com as CSS vars de core/ui.py
# --------------------------------------------------------------------------- #

# URL do ECharts via jsDelivr; versão fixada para builds determinísticos
_ECHART_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"

# Estilo do título do gráfico (cor = --text-main, Inter 14 semi-bold)
_EC_TITLE_STYLE = '{"color":"#E7F1F0","fontFamily":"Inter, sans-serif","fontSize":14,"fontWeight":"600"}'

# Propriedades comuns do tooltip (background e bordas no tema dark do app)
_EC_TOOLTIP_COMMON = (
    '"backgroundColor":"#0B131C","borderColor":"#2EE6C0","borderWidth":1,'
    '"padding":[10,14],'
    '"textStyle":{"color":"#E7F1F0","fontSize":13,"fontFamily":"Inter, sans-serif"}'
)

# Formatador JavaScript pt-BR: inteiro com ponto de milhar (ex.: 1.234)
# raw string: preserva \B e \d que sao regex JavaScript, nao escapes Python
_FMT_BR_JS = r"""
function fmtBR(v) {
    return v.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}
"""

# Formatter de tooltip para series simples (barras): nome em muted + valor grande
_TOOLTIP_FMT_JS = (
    "function(p) {"
    " var it=Array.isArray(p)?p[0]:p;"           # eixo 'axis' retorna array
    " return '<span style=\"font-size:12px;color:#7C95A0\">'+it.name+'</span><br/>'"
    "+'<span style=\"font-size:17px;font-weight:700;color:#2EE6C0\">'+fmtBR(it.value)+'</span>';"
    "}"
)


# --------------------------------------------------------------------------- #
# Helper: monta o HTML completo que envolve o grafico
# --------------------------------------------------------------------------- #
def _echarts_wrap(body_js: str, height: int = 300) -> str:
    """
    Retorna uma pagina HTML minima contendo o ECharts e o `var option` passado.
    O div#c recebe width:100% para se adaptar ao container do Streamlit.
    O evento 'resize' reconstroi o grafico quando o usuario redimensiona a janela.
    """
    return (
        f'<!doctype html><html><head>'
        f'<script src="{_ECHART_CDN}"></script>'
        f'<style>*{{margin:0;padding:0;box-sizing:border-box}}'
        f'body{{background:transparent;overflow:hidden}}</style>'
        f'</head><body>'
        f'<div id="c" style="width:100%;height:{height}px"></div>'
        f'<script>'
        f'{_FMT_BR_JS}'
        f'var chart=echarts.init(document.getElementById("c"),null,{{renderer:"canvas"}});'
        f'{body_js}'
        f'chart.setOption(option);'
        f'window.addEventListener("resize",function(){{chart.resize()}});'
        f'</script></body></html>'
    )


# --------------------------------------------------------------------------- #
# Grafico de barras
# --------------------------------------------------------------------------- #
def plot_bar(series: pd.Series, title: str = "", color: str = "#2EE6C0") -> None:
    """
    Renderiza um grafico de barras vertical com rotulos de valor no topo.

    Opcoes notaveis:
    - barMaxWidth:64 -- evita barras largas demais quando ha poucas categorias.
    - borderRadius:[5,5,0,0] -- cantos arredondados apenas no topo da barra.
    - label.position:'top' -- valor formatado em pt-BR acima de cada barra.
    - yAxis.show:false -- sem eixo Y; os rotulos no topo dispensam escala.
    - grid.containLabel:true -- rotulos do eixo X nao sao cortados pelo container.
    """
    cats = _json.dumps([str(x) for x in series.index])
    vals = _json.dumps([float(v) for v in series.values])
    color_js = _json.dumps(color)
    title_js = _json.dumps(title)
    # rotaciona labels do eixo X quando ha muitas categorias (evita sobreposicao)
    rotate = 30 if len(series) > 4 else 0

    body = (
        f"var option={{"
        f"backgroundColor:'transparent',"
        f"title:{{text:{title_js},textStyle:{_EC_TITLE_STYLE}}},"
        f"tooltip:{{trigger:'axis',axisPointer:{{type:'shadow'}},{_EC_TOOLTIP_COMMON},formatter:{_TOOLTIP_FMT_JS}}},"
        f"grid:{{left:0,right:0,top:56,bottom:0,containLabel:true}},"
        f"xAxis:{{type:'category',data:{cats},"
        f"axisLabel:{{color:'#7C95A0',fontSize:11,rotate:{rotate},overflow:'truncate',width:80}},"
        f"axisLine:{{lineStyle:{{color:'rgba(124,149,160,0.25)'}}}},"
        f"axisTick:{{show:false}},splitLine:{{show:false}}}},"
        f"yAxis:{{type:'value',show:false,splitLine:{{show:false}}}},"
        f"series:[{{type:'bar',data:{vals},"
        f"itemStyle:{{color:{color_js},borderRadius:[5,5,0,0]}},"
        f"label:{{show:true,position:'top',"
        f"formatter:function(p){{return fmtBR(p.value);}},"
        f"color:'#E7F1F0',fontSize:11,fontWeight:'600',fontFamily:'Inter, sans-serif'}},"
        f"emphasis:{{itemStyle:{{color:'#5FECCC',shadowBlur:8,shadowColor:'rgba(46,230,192,0.4)'}}}},"
        f"barMaxWidth:64}}]"
        f"}};"
    )
    _cv1.html(_echarts_wrap(body), height=318, scrolling=False)


# --------------------------------------------------------------------------- #
# Grafico de linha com media movel
# --------------------------------------------------------------------------- #
def plot_line(series: pd.Series, title: str = "", color: str = "#2EE6C0", ma_window: int = 3) -> None:
    """
    Renderiza um grafico de linha com area preenchida + linha de media movel.

    Parametros:
    - ma_window: janela da media movel em periodos (padrao 3).
      min_periods=1 garante que nao ha pontos nulos no inicio da serie.

    Series:
    - 'Valor': linha principal com area sob a curva (gradiente vertical).
    - 'Media Movel (Np)': linha tracejada laranja sem marcadores de ponto.

    Tooltip customizado: mostra ambas as series com marcador colorido e
    valor formatado em pt-BR quando o usuario passa o mouse sobre o grafico.

    Opcoes notaveis:
    - smooth:true -- curva suavizada (spline) em vez de segmentos retos.
    - boundaryGap:false -- linha comeca na borda do eixo X.
    - areaStyle com gradiente linear: opacidade 22% no topo -> 1% na base.
    """
    x_vals = series.index
    y_vals = series.values

    # formata datas para DD/MM/AAAA se o indice for datetime
    is_date = pd.api.types.is_datetime64_any_dtype(x_vals)
    if is_date:
        cats = _json.dumps([pd.Timestamp(x).strftime("%d/%m/%Y") for x in x_vals])
    else:
        cats = _json.dumps([str(x) for x in x_vals])

    vals = _json.dumps([float(v) for v in y_vals])
    color_js = _json.dumps(color)
    title_js = _json.dumps(title)
    rotate = 30 if len(series) > 6 else 0

    # calcula a MA em Python; min_periods=1 evita NaN nos primeiros pontos
    ma_vals = _json.dumps([
        round(float(v), 1)
        for v in series.rolling(window=ma_window, min_periods=1).mean().values
    ])
    ma_label = f"Media Movel ({ma_window}p)"
    ma_label_js = _json.dumps(ma_label)

    # gradiente vertical para a area sob a linha principal
    area_color = (
        '{"type":"linear","x":0,"y":0,"x2":0,"y2":1,'
        '"colorStops":['
        '{"offset":0,"color":"rgba(46,230,192,0.22)"},'
        '{"offset":1,"color":"rgba(46,230,192,0.01)"}'
        ']}'
    )

    # tooltip multi-serie: marcador colorido + nome + valor para cada serie
    tooltip_fmt = (
        "function(params){"
        "var name=params[0].name;"
        "var html='<span style=\"font-size:12px;color:#7C95A0\">'+name+'</span><br/>';"
        "params.forEach(function(p){"
        "html+='<span style=\"display:inline-block;width:8px;height:8px;"
        "border-radius:50%;background:'+p.color+';margin-right:5px\"></span>'"
        "+'<span style=\"font-size:12px;color:#7C95A0\">'+p.seriesName+'</span>'"
        "+'<span style=\"font-size:15px;font-weight:700;color:'+p.color+';margin-left:8px\">'+"
        "fmtBR(p.value)+'</span><br/>';"
        "});"
        "return html;}"
    )

    body = (
        f"var option={{"
        f"backgroundColor:'transparent',"
        f"title:{{text:{title_js},left:0,top:0,textStyle:{_EC_TITLE_STYLE}}},"
        # legenda discreta no canto superior direito
        f"legend:{{show:true,right:0,top:2,"
        f"textStyle:{{color:'#7C95A0',fontSize:11,fontFamily:'Inter, sans-serif'}},"
        f"itemWidth:14,itemHeight:3}},"
        f"tooltip:{{trigger:'axis',{_EC_TOOLTIP_COMMON},formatter:{tooltip_fmt}}},"
        f"grid:{{left:0,right:0,top:52,bottom:0,containLabel:true}},"
        f"xAxis:{{type:'category',data:{cats},boundaryGap:false,"
        f"axisLabel:{{color:'#7C95A0',fontSize:11,rotate:{rotate}}},"
        f"axisLine:{{lineStyle:{{color:'rgba(124,149,160,0.25)'}}}},"
        f"axisTick:{{show:false}},splitLine:{{show:false}}}},"
        f"yAxis:{{type:'value',show:false,splitLine:{{show:false}}}},"
        f"series:["
        # serie principal: linha com area
        f"{{type:'line',name:'Valor',data:{vals},smooth:true,"
        f"symbol:'circle',symbolSize:8,"
        f"lineStyle:{{color:{color_js},width:2.5}},"
        f"itemStyle:{{color:{color_js},borderColor:'#0B131C',borderWidth:2}},"
        f"emphasis:{{itemStyle:{{color:'#5FECCC',borderColor:'#0B131C',borderWidth:2,"
        f"shadowBlur:8,shadowColor:'rgba(46,230,192,0.5)'}}}},"
        f"areaStyle:{{color:{area_color}}}}},"
        # serie de media movel: tracejada laranja, sem marcadores de ponto
        f"{{type:'line',name:{ma_label_js},data:{ma_vals},smooth:true,"
        f"symbol:'none',"
        f"lineStyle:{{color:'#F4A261',width:2,type:'dashed'}},"
        f"itemStyle:{{color:'#F4A261'}},"
        f"emphasis:{{disabled:true}}"
        f"}}"
        f"]"
        f"}};"
    )
    _cv1.html(_echarts_wrap(body), height=318, scrolling=False)
