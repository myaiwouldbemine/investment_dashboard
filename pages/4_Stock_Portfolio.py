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


def _fetch_api_json(endpoint: str) -> dict[str, object] | None:
    base_url = _api_base_url()
    if not base_url:
        return None
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f'{base_url}{endpoint}', headers={'ngrok-skip-browser-warning': '1'})
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
    return 'No data loaded' not in ' '.join(str(line) for line in lines)


def card_style():
    st.markdown(
        """
        <style>
        .main {background: linear-gradient(180deg, #111318 0%, #171a20 100%);}
        h1, h2, h3 {color: #f2f2ee;}
        .stCaptionContainer, .stMarkdown p {color: #b8b8b1 !important;}
        .kpi-card {background: #272824; border: 1px solid #43453f; border-radius: 20px; padding: 18px 22px; min-height: 120px;}
        .kpi-label {font-size: 16px; color: #b7b4aa; margin-bottom: 10px;}
        .kpi-value {font-size: 44px; font-weight: 800; color: #f3f3ef; line-height: 1.1;}
        .kpi-positive {color: #26b386;}
        .panel {background: #2a2b27; border: 1px solid #454741; border-radius: 24px; padding: 18px 18px 8px 18px; margin-top: 8px; margin-bottom: 16px;}
        .panel-title {font-size: 20px; font-weight: 800; color: #d8d5ca; margin-bottom: 4px;}
        .summary-row {display: grid; grid-template-columns: 120px 1fr 160px 120px; gap: 14px; align-items: center; padding: 14px 6px; border-bottom: 1px solid #3c3d38;}
        .summary-row:last-child {border-bottom: none;}
        .summary-name {font-size: 22px; font-weight: 800; color: #f2f2ef;}
        .summary-bar {height: 18px; background: #1e1f1c; border-radius: 999px; overflow: hidden;}
        .summary-fill {height: 100%; background: linear-gradient(90deg, #1fa87b 0%, #35c08f 100%); border-radius: 999px;}
        .summary-amount {font-size: 20px; font-weight: 800; color: #28b485; text-align: right;}
        .summary-rate {font-size: 18px; font-weight: 700; color: #28b485; text-align: right;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def plot_layout(chart, x_title='', y_title=''):
    chart.update_layout(
        paper_bgcolor='#2a2b27',
        plot_bgcolor='#2a2b27',
        font=dict(color='#d8d5ca', size=16),
        margin=dict(l=30, r=20, t=70, b=30),
        coloraxis_showscale=False,
        xaxis=dict(title=x_title, gridcolor='#3f413a', zeroline=False),
        yaxis=dict(title=y_title, gridcolor='#3f413a', zeroline=False),
    )
    chart.update_traces(marker_line_width=0)
    return chart


def company_summary_block(frame: pd.DataFrame) -> None:
    if frame.empty:
        return
    total = frame['total_cost_jpy'].sum()
    rows = []
    for _, row in frame.sort_values('total_cost_jpy', ascending=False).iterrows():
        width = 0 if not total else row['total_cost_jpy'] / total * 100
        rows.append(
            f"<div class='summary-row'><div class='summary-name'>{row['company_code']}</div><div class='summary-bar'><div class='summary-fill' style='width:{width:.2f}%;'></div></div><div class='summary-amount'>{fmt_amount(row['unrealized_pnl_jpy'])}</div><div class='summary-rate'>{fmt_pct(row['pnl_pct'])}</div></div>"
        )
    st.markdown(f"<div class='panel'><div class='panel-title'>Account Unrealized PnL</div>{''.join(rows)}</div>", unsafe_allow_html=True)


def company_pnl_chart(frame: pd.DataFrame):
    chart = px.bar(frame.sort_values('unrealized_pnl_jpy'), x='unrealized_pnl_jpy', y='company_code', orientation='h', color='unrealized_pnl_jpy', color_continuous_scale=['#d75d2d', '#2aa77e'])
    chart.update_traces(text=frame.sort_values('unrealized_pnl_jpy')['unrealized_pnl_jpy'], texttemplate='%{text:,.0f}', textposition='outside', customdata=frame.sort_values('unrealized_pnl_jpy')[['pnl_pct']], hovertemplate='Company: %{y}<br>PnL ratio: %{customdata[0]:.2%}<extra></extra>')
    return plot_layout(chart, 'PnL Amount', '')


def stock_pnl_chart(frame: pd.DataFrame):
    ordered = frame.sort_values('unrealized_pnl_jpy')
    colors = ['#d75d2d' if v < 0 else '#2aa77e' for v in ordered['unrealized_pnl_jpy']]
    chart = go.Figure(go.Bar(x=ordered['unrealized_pnl_jpy'], y=ordered['security_name_zh'], orientation='h', marker_color=colors, text=[fmt_amount(v) for v in ordered['unrealized_pnl_jpy']], textposition='outside', customdata=ordered[['return_pct']], hovertemplate='Stock: %{y}<br>Return: %{customdata[0]:.2%}<extra></extra>'))
    chart.update_layout(title='Stock PnL Distribution')
    return plot_layout(chart, 'PnL Amount', '')


def market_value_donut(frame: pd.DataFrame):
    chart = go.Figure(go.Pie(labels=frame['security_name_zh'], values=frame['market_value_jpy'], hole=0.42, textinfo='label+value', texttemplate='%{label}<br>%{value:,.0f}', customdata=frame[['investment_weight']], hovertemplate='Stock: %{label}<br>Weight: %{customdata[0]:.2%}<extra></extra>'))
    chart.update_layout(title='Market Value Allocation', paper_bgcolor='#2a2b27', plot_bgcolor='#2a2b27', font=dict(color='#d8d5ca', size=16), margin=dict(l=10, r=10, t=70, b=10), showlegend=False)
    return chart


def pnl_heatmap(frame: pd.DataFrame):
    pivot = frame.pivot_table(index='company_code', columns='security_name_zh', values='unrealized_pnl_jpy', aggfunc='sum')
    chart = go.Figure(data=go.Heatmap(z=pivot.values, x=pivot.columns, y=pivot.index, colorscale=[[0.0, '#8f4b34'], [0.5, '#31322e'], [1.0, '#2aa77e']], zmid=0, text=[[fmt_amount(v) if pd.notna(v) else '-' for v in row] for row in pivot.values], texttemplate='%{text}', hovertemplate='Account: %{y}<br>Stock: %{x}<br>PnL: %{z:,.0f}<extra></extra>'))
    chart.update_layout(title='Account x Stock PnL Heatmap', xaxis_title='', yaxis_title='', paper_bgcolor='#2a2b27', plot_bgcolor='#2a2b27', font=dict(color='#d8d5ca', size=16), margin=dict(l=30, r=20, t=70, b=20))
    return chart


st.set_page_config(layout='wide')
enforce_dashboard_access()
card_style()
st.title('Stock Portfolio Analysis')
st.caption('Source: Stocks.xlsx')

position_path = PROCESSED_DIR / 'mart_japan_stock_dashboard' / 'latest.parquet'
stock_api = _fetch_api_json('/api/v1/investments/stocks')
stock_chart_api = _fetch_api_json('/api/v1/investments/charts/stocks')

if not position_path.exists():
    has_chart_data = bool(stock_chart_api and stock_chart_api.get('available'))
    if has_chart_data:
        metrics = stock_chart_api.get('metrics') or {}
        charts = stock_chart_api.get('charts') or {}
        total_cost = pd.to_numeric(metrics.get('total_cost'), errors='coerce')
        total_market = pd.to_numeric(metrics.get('total_market'), errors='coerce')
        total_pnl = pd.to_numeric(metrics.get('total_pnl'), errors='coerce')
        overall_return = pd.to_numeric(metrics.get('overall_return'), errors='coerce')
        total_cost = 0.0 if pd.isna(total_cost) else total_cost
        total_market = 0.0 if pd.isna(total_market) else total_market
        total_pnl = 0.0 if pd.isna(total_pnl) else total_pnl

        st.info('API mode enabled. Charts are rendered from aggregated API data.')

        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(f"<div class='kpi-card'><div class='kpi-label'>Total Cost</div><div class='kpi-value'>JPY {total_cost/1_000_000_000:.2f}B</div></div>", unsafe_allow_html=True)
        k2.markdown(f"<div class='kpi-card'><div class='kpi-label'>Market Value</div><div class='kpi-value'>JPY {total_market/1_000_000_000:.2f}B</div></div>", unsafe_allow_html=True)
        pnl_cls = 'kpi-positive' if total_pnl >= 0 else ''
        pnl_sign = '+' if total_pnl >= 0 else ''
        k3.markdown(f"<div class='kpi-card'><div class='kpi-label'>Unrealized PnL</div><div class='kpi-value {pnl_cls}'>{pnl_sign}JPY {total_pnl/1_000_000:.0f}M</div></div>", unsafe_allow_html=True)
        ret = 0 if pd.isna(overall_return) else overall_return
        ret_cls = 'kpi-positive' if ret >= 0 else ''
        ret_sign = '+' if ret >= 0 else ''
        k4.markdown(f"<div class='kpi-card'><div class='kpi-label'>Total Return</div><div class='kpi-value {ret_cls}'>{ret_sign}{fmt_pct(overall_return)}</div></div>", unsafe_allow_html=True)

        company_df = pd.DataFrame(charts.get('company') or [])
        stock_pnl_df = pd.DataFrame(charts.get('stock_pnl') or [])
        market_df = pd.DataFrame(charts.get('market_value') or [])
        heatmap_df = pd.DataFrame(charts.get('heatmap') or [])

        if not company_df.empty and {'company_code', 'total_cost_jpy', 'unrealized_pnl_jpy', 'pnl_pct'}.issubset(company_df.columns):
            company_summary_block(company_df)

        left, right = st.columns(2)
        if not company_df.empty and {'company_code', 'unrealized_pnl_jpy', 'pnl_pct'}.issubset(company_df.columns):
            with left:
                st.plotly_chart(company_pnl_chart(company_df), use_container_width=True, config={'displayModeBar': False})
        if not stock_pnl_df.empty and {'security_name_zh', 'unrealized_pnl_jpy', 'return_pct'}.issubset(stock_pnl_df.columns):
            with right:
                st.plotly_chart(stock_pnl_chart(stock_pnl_df), use_container_width=True, config={'displayModeBar': False})

        left, right = st.columns(2)
        if not market_df.empty and {'security_name_zh', 'market_value_jpy', 'investment_weight'}.issubset(market_df.columns):
            with left:
                st.plotly_chart(market_value_donut(market_df), use_container_width=True, config={'displayModeBar': False})
        if not heatmap_df.empty and {'company_code', 'security_name_zh', 'unrealized_pnl_jpy'}.issubset(heatmap_df.columns):
            with right:
                st.plotly_chart(pnl_heatmap(heatmap_df), use_container_width=True, config={'displayModeBar': False})
        st.stop()

    if _summary_has_data(stock_api):
        st.info('API summary mode enabled.')
        st.json(stock_api)
        st.stop()

    if _api_base_url():
        st.error('API base URL is configured but stock data is unavailable.')
    else:
        st.warning('No local stock parquet and no API base URL configured.')
    st.stop()

position_df = pd.read_parquet(position_path)

with st.sidebar:
    st.header('Filters')
    companies = sorted([x for x in position_df['company_code'].dropna().unique().tolist()])
    stocks = sorted([x for x in position_df['security_name_zh'].dropna().unique().tolist()])
    selected_company = st.multiselect('Company', companies, default=companies)
    selected_stock = st.multiselect('Stock', stocks, default=stocks)

filtered = position_df[position_df['company_code'].isin(selected_company) & position_df['security_name_zh'].isin(selected_stock)].copy()

total_cost = filtered['total_cost_jpy'].sum()
total_market = filtered['market_value_jpy'].sum()
total_pnl = filtered['unrealized_pnl_jpy'].sum()
overall_return = total_pnl / total_cost if total_cost else None

k1, k2, k3, k4 = st.columns(4)
k1.markdown(f"<div class='kpi-card'><div class='kpi-label'>Total Cost</div><div class='kpi-value'>JPY {total_cost/1_000_000_000:.2f}B</div></div>", unsafe_allow_html=True)
k2.markdown(f"<div class='kpi-card'><div class='kpi-label'>Market Value</div><div class='kpi-value'>JPY {total_market/1_000_000_000:.2f}B</div></div>", unsafe_allow_html=True)
pnl_cls = 'kpi-positive' if total_pnl >= 0 else ''
pnl_sign = '+' if total_pnl >= 0 else ''
k3.markdown(f"<div class='kpi-card'><div class='kpi-label'>Unrealized PnL</div><div class='kpi-value {pnl_cls}'>{pnl_sign}JPY {total_pnl/1_000_000:.0f}M</div></div>", unsafe_allow_html=True)
ret_cls = 'kpi-positive' if (overall_return or 0) >= 0 else ''
ret_sign = '+' if (overall_return or 0) >= 0 else ''
k4.markdown(f"<div class='kpi-card'><div class='kpi-label'>Total Return</div><div class='kpi-value {ret_cls}'>{ret_sign}{fmt_pct(overall_return)}</div></div>", unsafe_allow_html=True)

company_df = filtered.groupby('company_code', dropna=False)[['total_cost_jpy', 'unrealized_pnl_jpy']].sum().reset_index()
company_df['pnl_pct'] = company_df['unrealized_pnl_jpy'] / company_df['total_cost_jpy']
company_summary_block(company_df)

left, right = st.columns(2)
with left:
    st.plotly_chart(company_pnl_chart(company_df), use_container_width=True, config={'displayModeBar': False})
with right:
    pnl_df = filtered.groupby('security_name_zh', dropna=False)[['unrealized_pnl_jpy', 'total_cost_jpy']].sum().reset_index()
    pnl_df['return_pct'] = pnl_df['unrealized_pnl_jpy'] / pnl_df['total_cost_jpy']
    st.plotly_chart(stock_pnl_chart(pnl_df), use_container_width=True, config={'displayModeBar': False})

left, right = st.columns(2)
with left:
    market_df = filtered.groupby('security_name_zh', dropna=False)[['market_value_jpy', 'total_cost_jpy']].sum().reset_index()
    market_df['investment_weight'] = market_df['total_cost_jpy'] / market_df['total_cost_jpy'].sum() if market_df['total_cost_jpy'].sum() else 0
    market_df = market_df.sort_values('market_value_jpy', ascending=False)
    st.plotly_chart(market_value_donut(market_df), use_container_width=True, config={'displayModeBar': False})
with right:
    st.plotly_chart(pnl_heatmap(filtered), use_container_width=True, config={'displayModeBar': False})

st.subheader('Stock Detail')
detail = filtered.rename(columns={'ticker': 'Ticker', 'security_name_zh': 'Stock', 'company_code': 'Company', 'shares': 'Shares', 'avg_cost_jpy': 'Avg Cost', 'last_price_jpy': 'Last Price', 'total_cost_jpy': 'Investment', 'market_value_jpy': 'Market Value', 'unrealized_pnl_jpy': 'Unrealized PnL', 'unrealized_return': 'Return'}).copy()
detail = detail.sort_values(['Company', 'Investment'], ascending=[True, False])
for col in ['Shares', 'Investment', 'Market Value', 'Unrealized PnL']:
    detail[col] = detail[col].map(fmt_amount)
detail['Avg Cost'] = detail['Avg Cost'].map(fmt_num)
detail['Last Price'] = detail['Last Price'].map(fmt_num)
detail['Return'] = detail['Return'].map(fmt_pct)
st.dataframe(detail[['Ticker', 'Stock', 'Company', 'Shares', 'Avg Cost', 'Last Price', 'Investment', 'Market Value', 'Unrealized PnL', 'Return']], use_container_width=True, hide_index=True)
