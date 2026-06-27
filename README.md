# Painel POLO

Aplicação em **Python + Streamlit** para acompanhamento da matéria-prima **POLO**, consolidando três fontes de dados em um único painel com tema dark moderno (verde-cyano/água).

## Estrutura do projeto

```
APP_POLO/
├── app.py                          # Ponto de entrada do Streamlit (orquestra as 3 abas)
├── requirements.txt
├── .streamlit/
│   └── config.toml                 # Tema dark + verde-cyano
├── core/
│   └── utils.py                    # CSS, filtros, KPI cards, exportação Excel
├── services/
│   ├── acompanhamento_service.py   # ABA 1 — A Receber
│   ├── recebimento_service.py      # ABA 2 — Recebido
│   └── producao_service.py         # ABA 3 — Produção Diária
└── Dataset/
    ├── ACOMPANHAMENTO.xlsx
    ├── RECEBIMENTO.xlsx
    └── Produção Diária - POLO.xlsx
```

## Como executar

```bash
pip install -r requirements.txt
streamlit run app.py
```

O app carrega os arquivos automaticamente da pasta `Dataset/` (mesmo nível de `app.py`). Se algum arquivo não for encontrado, a barra lateral oferece um upload manual.

## O que cada aba mostra

| Aba | Fonte | Filtro MP | Métricas |
|---|---|---|---|
| 📦 A Receber | `ACOMPANHAMENTO.xlsx` | MP = POLO | Total de peças (QTD), total de minutos, ordens distintas |
| ✅ Recebido | `RECEBIMENTO.xlsx` | MP = POLO | Total de peças (REAL CORTADO), total de minutos, ordens distintas |
| 🏭 Produção Diária | `Produção Diária - POLO.xlsx` | já exclusivo de POLO | Total de peças produzidas e nº de registros (ordens) — **sem minutos**, conforme solicitado |

Todas as abas têm filtro de **período (data)** e **oficina(s)**; a aba de Produção Diária tem ainda um filtro extra por **semana (WK)**.

## Observações de implementação

- **Normalização de texto**: nomes de oficina e o valor de `MP` vêm com inconsistências na planilha original (ex.: `Malha`/`MALHA`, espaços invisíveis `\xa0`). O filtro de `MP = POLO` e os filtros de oficina ignoram caixa e espaços extras.
- **Datas ausentes**: 1 registro em ACOMPANHAMENTO está sem `ENVIO`/`DEAD LINE` preenchido — ele é mantido na listagem independentemente do período escolhido (aviso exibido na tela), para não esconder dados silenciosamente.
- **Recebimento parcial**: uma mesma Ordem Mestre pode aparecer em mais de uma data em `RECEBIMENTO.xlsx` (recebimento em partes). O KPI "Ordens Recebidas" conta ordens **distintas**, enquanto peças e minutos somam todas as linhas.
- **Exportação para Excel**: o botão "Exportar Excel" de cada aba gera um `.xlsx` mantendo as colunas de data como `datetime` nativo (não como texto), aplicando apenas a formatação visual `DD/MM/YYYY` via `number_format`.

## Decisão assumida (a validar com você)

Na ABA 1, o filtro de período foi aplicado sobre a coluna **ENVIO** (data de envio do pedido para a oficina) — a coluna `DEAD LINE` também é exibida na tabela para referência, mas não é usada como filtro principal. Se preferir filtrar por `DEAD LINE` em vez de `ENVIO`, é só avisar que eu ajusto.
