import os

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.settings import PROCESSED_DIR
from src.utils.dashboard_access import enforce_dashboard_access


def fmt_amount(value):
    if value is None or pd.isna(value):
        return 'N/A'
    value = pd.to_numeric(value, errors='coerce')
    if pd.isna(value):
        return 'N/A'
    return f"{value:,.0f}"


def fmt_pct(value):
    if value is None or pd.isna(value):
        return 'N/A'
    value = pd.to_numeric(value, errors='coerce')
    if pd.isna(value):
        return 'N/A'
    return f"{value:.2%}"


def fmt_num(value):
    if value is None or pd.isna(value):
        return 'N/A'
    value = pd.to_numeric(value, errors='coerce')
    if pd.isna(value):
        return 'N/A'
    return f"{value:,.2f}"



def _get_secret(name: str) -> str:
    value = os.getenv(name, '').strip()
    if value:
        return value
    try:
        value = st.secrets.get(name, '')
    except Exception:
        value = ''
    return str(value).strip()


def _api_base_url() -> str:
    return (_get_secret('INVESTMENT_API_BASE_URL') or _get_secret('INVESTMENT_DASHBOARD_API_BASE_URL')).rstrip('/')


def _fetch_api_summary(endpoint: str) -> dict[str, object] | None:
    base_url = _api_base_url()
    if not base_url:
        return None
    try:
        with httpx.Client(timeout=4.0) as client:
            response = client.get(f'{base_url}{endpoint}')
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return payload
    except Exception:
        return None
    return None


def _summary_has_data(payload: dict[str, object] | None) -> bool:
    if not payload:
        return False
    lines = payload.get('lines') or []
    if not isinstance(lines, list) or not lines:
        return False
    return '尚未載入資料' not in ' '.join(str(line) for line in lines)


def _line_value(lines: list[str], prefixes: tuple[str, ...]) -> str | None:
    for line in lines:
        if not isinstance(line, str):
            continue
        normalized = line.replace('：', ':')
        for prefix in prefixes:
            if normalized.startswith(prefix.replace('：', ':')):
                return normalized.split(':', 1)[1].strip()
    return None

def card_style():
    st.markdown(
        """
        <style>
        .main {background: linear-gradient(180deg, #111318 0%, #171a20 100%);}
        h1, h2, h3 {color: #f2f2ee;}
        .stCaptionContainer, .stMarkdown p {color: #b8b8b1 !important;}
        .kpi-card {
            background: #272824;
            border: 1px solid #43453f;
            border-radius: 20px;
            padding: 18px 22px;
            min-height: 120px;
        }
        .kpi-label {font-size: 16px; color: #b7b4aa; margin-bottom: 10px;}
        .kpi-value {font-size: 44px; font-weight: 800; color: #f3f3ef; line-height: 1.1;}
        .kpi-positive {color: #26b386;}
        .panel {
            background: #2a2b27;
            border: 1px solid #454741;
            border-radius: 24px;
            padding: 18px 18px 8px 18px;
            margin-top: 8px;
            margin-bottom: 16px;
        }
        .panel-title {
            font-size: 20px;
            font-weight: 800;
            color: #d8d5ca;
            margin-bottom: 4px;
        }
        .summary-row {
            display: grid;
            grid-template-columns: 120px 1fr 160px 120px;
            gap: 14px;
            align-items: center;
            padding: 14px 6px;
            border-bottom: 1px solid #3c3d38;
        }
        .summary-row:last-child {border-bottom: none;}
        .summary-name {font-size: 22px; font-weight: 800; color: #f2f2ef;}
        .summary-bar {height: 18px; background: #1e1f1c; border-radius: 999px; overflow: hidden;}
        .summary-fill {height: 100%; background: linear-gradient(90deg, #1fa87b 0%, #35c08f 100%); border-radius: 999px;}
        .summary-amount {font-size: 20px; font-weight: 800; color: #28b485; text-align: right;}
        .summary-rate {font-size: 18px; font-weight: 700; color: #28b485; text-align: right;}
        .stDataFrame {background: rgba(255,255,255,0.04); border-radius: 16px;}
        section[data-testid="stSidebar"] [data-baseweb="tag"] {background: #4b5058 !important; border: 1px solid #666c75 !important;}
        section[data-testid="stSidebar"] [data-baseweb="tag"] span {color: #f5f7fa !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def plot_layout(chart, x_title='', y_title=''):
    chart.update_layout(
        paper_bgcolor='#2a2b27',
        plot_bgcolor='#2a2b27',
        font=dict(color='#d8d5ca', size=16),
        title=dict(font=dict(size=22, color='#d8d5ca'), x=0.02),
        margin=dict(l=30, r=20, t=70, b=30),
        coloraxis_showscale=False,
        xaxis=dict(title=x_title, gridcolor='#3f413a', zeroline=False),
        yaxis=dict(title=y_title, gridcolor='#3f413a', zeroline=False),
    )
    chart.update_traces(marker_line_width=0)
    return chart


def company_summary_block(frame: pd.DataFrame) -> None:
    total = frame['total_cost_jpy'].sum()
    rows = []
    for _, row in frame.sort_values('total_cost_jpy', ascending=False).iterrows():
        width = 0 if not total else row['total_cost_jpy'] / total * 100
        rows.append(
            f"<div class='summary-row'><div class='summary-name'>{row['company_code']}</div><div class='summary-bar'><div class='summary-fill' style='width:{width:.2f}%;'></div></div><div class='summary-amount'>{fmt_amount(row['unrealized_pnl_jpy'])}</div><div class='summary-rate'>{fmt_pct(row['pnl_pct'])}</div></div>"
        )
    html = f"<div class='panel'><div class='panel-title'>各帳戶未實現損益</div>{''.join(rows)}</div>"
    st.markdown(html, unsafe_allow_html=True)


def company_pnl_chart(frame: pd.DataFrame):
    chart = px.bar(frame.sort_values('unrealized_pnl_jpy'), x='unrealized_pnl_jpy', y='company_code', orientation='h', color='unrealized_pnl_jpy', color_continuous_scale=['#d75d2d', '#2aa77e'])
    chart.update_traces(
        text=frame.sort_values('unrealized_pnl_jpy')['unrealized_pnl_jpy'],
        texttemplate='%{text:,.0f}',
        textposition='outside',
        customdata=frame.sort_values('unrealized_pnl_jpy')[['pnl_pct']],
        hovertemplate='公司別: %{y}<br>損益比率: %{customdata[0]:.2%}<extra></extra>',
    )
    return plot_layout(chart, '損益金額', '')


def stock_pnl_chart(frame: pd.DataFrame):
    ordered = frame.sort_values('unrealized_pnl_jpy')
    colors = ['#d75d2d' if v < 0 else '#2aa77e' for v in ordered['unrealized_pnl_jpy']]
    chart = go.Figure(
        go.Bar(
            x=ordered['unrealized_pnl_jpy'],
            y=ordered['security_name_zh'],
            orientation='h',
            marker_color=colors,
            text=[fmt_amount(v) for v in ordered['unrealized_pnl_jpy']],
            textposition='outside',
            customdata=ordered[['return_pct']],
            hovertemplate='股票: %{y}<br>報酬率: %{customdata[0]:.2%}<extra></extra>',
        )
    )
    chart.update_layout(title='各股報酬分析（損益金額）')
    return plot_layout(chart, '損益金額', '')


def market_value_donut(frame: pd.DataFrame):
    chart = go.Figure(
        go.Pie(
            labels=frame['security_name_zh'],
            values=frame['market_value_jpy'],
            hole=0.42,
            textinfo='label+value',
            texttemplate='%{label}<br>%{value:,.0f}',
            customdata=frame[['investment_weight']],
            hovertemplate='股票: %{label}<br>市值占比: %{percent}<br>投資比重: %{customdata[0]:.2%}<extra></extra>',
        )
    )
    chart.update_layout(
        title='持倉結構分析（Hover 顯示投資比重）',
        paper_bgcolor='#2a2b27',
        plot_bgcolor='#2a2b27',
        font=dict(color='#d8d5ca', size=16),
        title_font=dict(size=22, color='#d8d5ca'),
        margin=dict(l=10, r=10, t=70, b=10),
        showlegend=False,
    )
    return chart


def pnl_heatmap(frame: pd.DataFrame):
    pivot = frame.pivot_table(index='company_code', columns='security_name_zh', values='unrealized_pnl_jpy', aggfunc='sum')
    chart = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale=[
                [0.0, '#8f4b34'],
                [0.5, '#31322e'],
                [1.0, '#2aa77e'],
            ],
            zmid=0,
            text=[[fmt_amount(v) if pd.notna(v) else '—' for v in row] for row in pivot.values],
            texttemplate='%{text}',
            hovertemplate='帳戶: %{y}<br>股票: %{x}<br>未實現損益: %{z:,.0f}<extra></extra>',
        )
    )
    chart.update_layout(title='帳戶 × 股票損益 Heatmap', xaxis_title='', yaxis_title='', paper_bgcolor='#2a2b27', plot_bgcolor='#2a2b27', font=dict(color='#d8d5ca', size=16), title_font=dict(size=22, color='#d8d5ca'), margin=dict(l=30, r=20, t=70, b=20))
    return chart


st.set_page_config(layout='wide')
enforce_dashboard_access()
card_style()
st.title('股票部位分析')
st.caption('資料來源：Stocks.xlsx')

position_path = PROCESSED_DIR / 'mart_japan_stock_dashboard' / 'latest.parquet'
stock_api = _fetch_api_summary('/api/v1/investments/stocks')

if not position_path.exists():
    if _summary_has_data(stock_api):
        lines = stock_api.get('lines') or []
        st.info('目前為 API 摘要模式（雲端無本機 parquet）。明細圖表需本機資料。')
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('投資金額', _line_value(lines, ('投資金額：', '投資金額:')) or 'N/A')
        c2.metric('市值', _line_value(lines, ('市值：', '市值:')) or 'N/A')
        c3.metric('未實現損益', _line_value(lines, ('未實現損益：', '未實現損益:')) or 'N/A')
        c4.metric('整體報酬率', _line_value(lines, ('整體報酬率：', '整體報酬率:')) or 'N/A')
        st.stop()
    if _api_base_url():
        st.error('已設定投資 API 位址，但目前無法取得股票資料。')
    else:
        st.warning('尚未找到已處理的股票資料，且未設定投資 API 位址（INVESTMENT_API_BASE_URL）。')
    st.stop()

position_df = pd.read_parquet(position_path)

with st.sidebar:
    st.header('篩選條件')
    companies = sorted([x for x in position_df['company_code'].dropna().unique().tolist()])
    stocks = sorted([x for x in position_df['security_name_zh'].dropna().unique().tolist()])
    selected_company = st.multiselect('公司別', companies, default=companies)
    selected_stock = st.multiselect('股票', stocks, default=stocks)

filtered = position_df[position_df['company_code'].isin(selected_company) & position_df['security_name_zh'].isin(selected_stock)].copy()

total_cost = filtered['total_cost_jpy'].sum()
total_market = filtered['market_value_jpy'].sum()
total_pnl = filtered['unrealized_pnl_jpy'].sum()
overall_return = total_pnl / total_cost if total_cost else None

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"<div class='kpi-card'><div class='kpi-label'>總投入成本</div><div class='kpi-value'>¥{total_cost/1_000_000_000:.2f}B</div></div>", unsafe_allow_html=True)
with k2:
    st.markdown(f"<div class='kpi-card'><div class='kpi-label'>總市值估算</div><div class='kpi-value'>¥{total_market/1_000_000_000:.2f}B</div></div>", unsafe_allow_html=True)
with k3:
    pnl_cls = 'kpi-positive' if total_pnl >= 0 else ''
    pnl_sign = '+' if total_pnl >= 0 else ''
    st.markdown(f"<div class='kpi-card'><div class='kpi-label'>未實現損益</div><div class='kpi-value {pnl_cls}'>{pnl_sign}¥{total_pnl/1_000_000:.0f}M</div></div>", unsafe_allow_html=True)
with k4:
    ret_cls = 'kpi-positive' if (overall_return or 0) >= 0 else ''
    ret_sign = '+' if (overall_return or 0) >= 0 else ''
    st.markdown(f"<div class='kpi-card'><div class='kpi-label'>整體報酬率</div><div class='kpi-value {ret_cls}'>{ret_sign}{fmt_pct(overall_return)}</div></div>", unsafe_allow_html=True)

company_df = filtered.groupby('company_code', dropna=False)[['total_cost_jpy', 'unrealized_pnl_jpy']].sum().reset_index()
company_df['pnl_pct'] = company_df['unrealized_pnl_jpy'] / company_df['total_cost_jpy']
company_summary_block(company_df)

left, right = st.columns(2)
with left:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.plotly_chart(company_pnl_chart(company_df), use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)
with right:
    pnl_df = filtered.groupby('security_name_zh', dropna=False)[['unrealized_pnl_jpy', 'total_cost_jpy']].sum().reset_index()
    pnl_df['return_pct'] = pnl_df['unrealized_pnl_jpy'] / pnl_df['total_cost_jpy']
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.plotly_chart(stock_pnl_chart(pnl_df), use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

left, right = st.columns(2)
with left:
    market_df = filtered.groupby('security_name_zh', dropna=False)[['market_value_jpy', 'total_cost_jpy']].sum().reset_index()
    market_df['investment_weight'] = market_df['total_cost_jpy'] / market_df['total_cost_jpy'].sum() if market_df['total_cost_jpy'].sum() else 0
    market_df = market_df.sort_values('market_value_jpy', ascending=False)
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.plotly_chart(market_value_donut(market_df), use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)
with right:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.plotly_chart(pnl_heatmap(filtered), use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

st.subheader('股票明細查詢')
detail = filtered.rename(columns={
    'ticker': '代碼',
    'security_name_zh': '股票',
    'company_code': '公司別',
    'shares': '持股股數',
    'avg_cost_jpy': '平均成本',
    'last_price_jpy': '現價',
    'total_cost_jpy': '投資金額',
    'market_value_jpy': '市值',
    'unrealized_pnl_jpy': '未實現損益',
    'unrealized_return': '報酬率',
}).copy()
detail = detail.sort_values(['公司別', '投資金額'], ascending=[True, False])
for col in ['持股股數', '投資金額', '市值', '未實現損益']:
    detail[col] = detail[col].map(fmt_amount)
detail['平均成本'] = detail['平均成本'].map(fmt_num)
detail['現價'] = detail['現價'].map(fmt_num)
detail['報酬率'] = detail['報酬率'].map(fmt_pct)
st.dataframe(detail[['代碼', '股票', '公司別', '持股股數', '平均成本', '現價', '投資金額', '市值', '未實現損益', '報酬率']], use_container_width=True, hide_index=True)

