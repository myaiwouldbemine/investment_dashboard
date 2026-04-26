import os

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

from config.settings import PROCESSED_DIR
from src.utils.dashboard_access import enforce_dashboard_access

CASHFLOW_TYPE_LABELS = {
    'coupon': 'Coupon',
    'coupon_principal': 'Coupon+Principal',
}

DETAIL_RENAME_MAP = {
    'isin': 'ISIN',
    'company_code': 'Company',
    'issuer_name': 'Issuer',
    'counterparty': 'Counterparty',
    'currency': 'Currency',
    'rating_bucket': 'Rating',
    'bond_type': 'Type',
    'face_amount': 'Face Amount',
    'settlement_amount': 'Settlement Amount',
    'ytm': 'YTM',
    'duration_years': 'Duration',
    'maturity_date': 'Maturity Date',
    'maturity_year': 'Maturity Year',
}


def fmt_amount(value):
    if value is None or pd.isna(value):
        return 'N/A'
    return f"{value:,.0f}"


def fmt_pct(value):
    if value is None or pd.isna(value):
        return 'N/A'
    return f"{value:.2%}"


def fmt_num(value):
    if value is None or pd.isna(value):
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
    return _get_secret('INVESTMENT_API_BASE_URL').rstrip('/')


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


def _line_value(lines: list[str], prefixes: tuple[str, ...]) -> str | None:
    for line in lines:
        if not isinstance(line, str):
            continue
        normalized = line.replace('?', ':')
        for prefix in prefixes:
            if normalized.startswith(prefix.replace('?', ':')):
                return normalized.split(':', 1)[1].strip()
    return None


def amount_bar(frame: pd.DataFrame, x: str, y: str, title: str, color_scale: str):
    chart = px.bar(frame, x=x, y=y, title=title, color=y, color_continuous_scale=color_scale, text=y)
    chart.update_traces(texttemplate='%{text:,.0f}', textposition='outside', hovertemplate=f'{x}: %{{x}}<br>Amount: %{{y:,.0f}}<extra></extra>')
    chart.update_layout(coloraxis_showscale=False, xaxis_title=x, yaxis_title='Amount', yaxis_tickformat=',.0f')
    return chart


def weight_bar(frame: pd.DataFrame, x: str, y: str, title: str, color_scale: str):
    chart = px.bar(frame, x=x, y=y, title=title, color=y, color_continuous_scale=color_scale, text=y)
    chart.update_traces(texttemplate='%{text:.2%}', textposition='outside', hovertemplate=f'{x}: %{{x}}<br>Weight: %{{y:.2%}}<extra></extra>')
    chart.update_layout(coloraxis_showscale=False, xaxis_title=x, yaxis_title='Weight', yaxis_tickformat='.0%')
    return chart


st.set_page_config(layout='wide')
enforce_dashboard_access()
st.markdown("""
<style>
.main {background: linear-gradient(180deg, #f7f2eb 0%, #fcfaf7 100%);}
h1, h2, h3 {color: #241c15;}
.stMetric {background: #23262d; border: 1px solid #4a4f59; padding: 10px; border-radius: 16px; box-shadow: 0 4px 14px rgba(0,0,0,0.28);} .stMetric label, .stMetric [data-testid="stMetricLabel"], .stMetric [data-testid="stMetricValue"] {color: #f7f7f7 !important;}
.stDataFrame {background: rgba(255,255,255,0.72); border-radius: 16px;}
</style>
""", unsafe_allow_html=True)
st.title('Bond Portfolio Analysis')
st.caption('Source: Bonds Analysis.xlsx')

position_path = PROCESSED_DIR / 'mart_bond_dashboard_position' / 'latest.parquet'
cashflow_path = PROCESSED_DIR / 'mart_bond_dashboard_cashflow' / 'latest.parquet'

bond_api = _fetch_api_json('/api/v1/investments/bonds')
bond_chart_api = _fetch_api_json('/api/v1/investments/charts/bonds')

if not position_path.exists():
    has_chart_data = bool(bond_chart_api and bond_chart_api.get('available'))
    if has_chart_data:
        metrics = bond_chart_api.get('metrics') or {}
        charts = bond_chart_api.get('charts') or {}
        st.info('API mode enabled. Charts are rendered from aggregated API data.')
        c1, c2, c3 = st.columns(3)
        c1.metric('Investment Amount', str(metrics.get('investment_amount') or 'N/A'))
        c2.metric('Average Yield', str(metrics.get('avg_ytm') or 'N/A'))
        c3.metric('Average Duration', str(metrics.get('avg_duration') or 'N/A'))

        currency_df = pd.DataFrame(charts.get('currency') or [])
        rating_df = pd.DataFrame(charts.get('rating') or [])
        counterparty_df = pd.DataFrame(charts.get('counterparty') or [])
        bond_type_df = pd.DataFrame(charts.get('bond_type') or [])
        maturity_df = pd.DataFrame(charts.get('maturity_year') or [])
        company_df = pd.DataFrame(charts.get('company') or [])
        cashflow_df = pd.DataFrame(charts.get('cashflow') or [])

        row1_left, row1_right = st.columns(2)
        with row1_left:
            if not currency_df.empty and {'currency', 'settlement_amount'}.issubset(currency_df.columns):
                chart = px.pie(currency_df, names='currency', values='settlement_amount', title='Currency Breakdown')
                st.plotly_chart(chart, use_container_width=True)
        with row1_right:
            if not rating_df.empty and {'rating_bucket', 'settlement_amount'}.issubset(rating_df.columns):
                st.plotly_chart(amount_bar(rating_df, 'rating_bucket', 'settlement_amount', 'Amount by Rating', 'Blues'), use_container_width=True)

        cp_left, cp_right = st.columns(2)
        with cp_left:
            if not counterparty_df.empty and {'counterparty', 'settlement_amount'}.issubset(counterparty_df.columns):
                st.plotly_chart(amount_bar(counterparty_df, 'counterparty', 'settlement_amount', 'Counterparty Amount', 'Sunset'), use_container_width=True)
        with cp_right:
            if not counterparty_df.empty and {'counterparty', 'weight'}.issubset(counterparty_df.columns):
                st.plotly_chart(weight_bar(counterparty_df, 'counterparty', 'weight', 'Counterparty Weight', 'Sunset'), use_container_width=True)

        tp_left, tp_right = st.columns(2)
        with tp_left:
            if not bond_type_df.empty and {'bond_type', 'settlement_amount'}.issubset(bond_type_df.columns):
                st.plotly_chart(amount_bar(bond_type_df, 'bond_type', 'settlement_amount', 'Amount by Bond Type', 'Purples'), use_container_width=True)
        with tp_right:
            if not bond_type_df.empty and {'bond_type', 'weight'}.issubset(bond_type_df.columns):
                st.plotly_chart(weight_bar(bond_type_df, 'bond_type', 'weight', 'Weight by Bond Type', 'Purples'), use_container_width=True)

        yr_left, yr_right = st.columns(2)
        with yr_left:
            if not maturity_df.empty and {'maturity_year', 'settlement_amount'}.issubset(maturity_df.columns):
                st.plotly_chart(amount_bar(maturity_df, 'maturity_year', 'settlement_amount', 'Amount by Maturity Year', 'Oranges'), use_container_width=True)
        with yr_right:
            if not cashflow_df.empty and {'cashflow_year', 'total_payback'}.issubset(cashflow_df.columns):
                flow_df = cashflow_df.groupby('cashflow_year', dropna=False)['total_payback'].sum().reset_index().sort_values('cashflow_year')
                chart = px.bar(flow_df, x='cashflow_year', y='total_payback', title='Cashflow by Year', text='total_payback')
                chart.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                chart.update_layout(xaxis_title='Year', yaxis_title='Amount', yaxis_tickformat=',.0f')
                st.plotly_chart(chart, use_container_width=True)

        cm_left, cm_right = st.columns(2)
        with cm_left:
            if not company_df.empty and {'company_code', 'settlement_amount'}.issubset(company_df.columns):
                st.plotly_chart(amount_bar(company_df, 'company_code', 'settlement_amount', 'Amount by Company', 'Teal'), use_container_width=True)
        with cm_right:
            if not company_df.empty and {'company_code', 'weight'}.issubset(company_df.columns):
                st.plotly_chart(weight_bar(company_df, 'company_code', 'weight', 'Weight by Company', 'Greens'), use_container_width=True)
        st.stop()

    if _summary_has_data(bond_api):
        lines = bond_api.get('lines') or []
        st.info('API summary mode enabled.')
        c1, c2, c3 = st.columns(3)
        c1.metric('Investment Amount', _line_value(lines, ('Investment amount:',)) or 'N/A')
        c2.metric('Average Yield', _line_value(lines, ('Average yield:',)) or 'N/A')
        c3.metric('Average Duration', _line_value(lines, ('Average duration:',)) or 'N/A')
        st.stop()

    if _api_base_url():
        st.error('API base URL is configured but bond data is unavailable.')
    else:
        st.warning('No local bond parquet and no API base URL configured.')
    st.stop()

position_df = pd.read_parquet(position_path)
cashflow_df = pd.read_parquet(cashflow_path) if cashflow_path.exists() else pd.DataFrame()

if not cashflow_df.empty:
    cashflow_df['cashflow_label'] = cashflow_df['cashflow_type'].map(CASHFLOW_TYPE_LABELS).fillna(cashflow_df['cashflow_type'])

with st.sidebar:
    st.header('Filters')
    currencies = sorted([x for x in position_df['currency'].dropna().unique().tolist()])
    ratings = sorted([str(x) for x in position_df['rating_bucket'].dropna().unique().tolist()])
    counterparties = sorted([str(x) for x in position_df['counterparty'].dropna().unique().tolist()])
    bond_types = sorted([str(x) for x in position_df['bond_type'].dropna().unique().tolist()])

    selected_currency = st.multiselect('Currency', currencies, default=currencies)
    selected_rating = st.multiselect('Rating', ratings, default=ratings)
    selected_counterparty = st.multiselect('Counterparty', counterparties, default=counterparties)
    selected_bond_type = st.multiselect('Type', bond_types, default=bond_types)
    min_year, max_year = int(position_df['maturity_year'].min()), int(position_df['maturity_year'].max())
    maturity_range = st.slider('Maturity Year', min_year, max_year, (min_year, max_year))

filtered = position_df[
    position_df['currency'].isin(selected_currency)
    & position_df['rating_bucket'].astype(str).isin(selected_rating)
    & position_df['counterparty'].astype(str).isin(selected_counterparty)
    & position_df['bond_type'].astype(str).isin(selected_bond_type)
    & position_df['maturity_year'].between(maturity_range[0], maturity_range[1])
].copy()

st.subheader('Overview')
c1, c2, c3, c4, c5 = st.columns(5)
_settlement_sum = filtered['settlement_amount'].sum()
_cash_total_sum = filtered['cash_total'].sum() if 'cash_total' in filtered.columns else None
_w = filtered['settlement_amount'].sum() if 'settlement_amount' in filtered.columns else 0
_avg_duration = ((filtered['duration_years'] * filtered['settlement_amount']).sum() / _w) if _w else (filtered['duration_years'].mean() if not filtered['duration_years'].dropna().empty else None)
if _cash_total_sum and _cash_total_sum > 0 and _settlement_sum > 0 and _avg_duration and pd.notna(_avg_duration) and _avg_duration > 0:
    _avg_ytm = fmt_pct((_cash_total_sum - _settlement_sum) / _settlement_sum / _avg_duration)
else:
    _avg_ytm = fmt_pct(filtered['ytm'].mean()) if not filtered['ytm'].dropna().empty else 'N/A'
c1.metric('Investment Amount', fmt_amount(_settlement_sum))
c2.metric('Average Yield', _avg_ytm)
c3.metric('Average Duration', fmt_num(_avg_duration) if _avg_duration is not None else 'N/A')
c4.metric('Issuer Count', int(filtered['issuer_name'].nunique()))
c5.metric('Positions', int(len(filtered)))

row1_left, row1_right = st.columns(2)
with row1_left:
    st.plotly_chart(px.pie(filtered, names='currency', values='settlement_amount', title='Currency Breakdown'), use_container_width=True)
with row1_right:
    rating_df = filtered.groupby('rating_bucket', dropna=False)['settlement_amount'].sum().reset_index().sort_values('settlement_amount', ascending=False)
    st.plotly_chart(amount_bar(rating_df, 'rating_bucket', 'settlement_amount', 'Amount by Rating', 'Blues'), use_container_width=True)

counterparty_df = filtered.groupby('counterparty', dropna=False)['settlement_amount'].sum().reset_index().sort_values('settlement_amount', ascending=False)
counterparty_df['weight'] = counterparty_df['settlement_amount'] / counterparty_df['settlement_amount'].sum() if counterparty_df['settlement_amount'].sum() else 0
cp_left, cp_right = st.columns(2)
with cp_left:
    st.plotly_chart(amount_bar(counterparty_df, 'counterparty', 'settlement_amount', 'Counterparty Amount', 'Sunset'), use_container_width=True)
with cp_right:
    st.plotly_chart(weight_bar(counterparty_df, 'counterparty', 'weight', 'Counterparty Weight', 'Sunset'), use_container_width=True)

bond_type_df = filtered.groupby('bond_type', dropna=False)['settlement_amount'].sum().reset_index().sort_values('settlement_amount', ascending=False)
bond_type_df['weight'] = bond_type_df['settlement_amount'] / bond_type_df['settlement_amount'].sum() if bond_type_df['settlement_amount'].sum() else 0
tp_left, tp_right = st.columns(2)
with tp_left:
    st.plotly_chart(amount_bar(bond_type_df, 'bond_type', 'settlement_amount', 'Amount by Bond Type', 'Purples'), use_container_width=True)
with tp_right:
    st.plotly_chart(weight_bar(bond_type_df, 'bond_type', 'weight', 'Weight by Bond Type', 'Purples'), use_container_width=True)

yr_left, yr_right = st.columns(2)
with yr_left:
    maturity_df = filtered.groupby('maturity_year', dropna=False)['settlement_amount'].sum().reset_index().sort_values('maturity_year')
    st.plotly_chart(amount_bar(maturity_df, 'maturity_year', 'settlement_amount', 'Amount by Maturity Year', 'Oranges'), use_container_width=True)
with yr_right:
    if not cashflow_df.empty:
        flow_df = cashflow_df.groupby('cashflow_year', dropna=False)['total_payback'].sum().reset_index().sort_values('cashflow_year')
        cf_chart = px.bar(flow_df, x='cashflow_year', y='total_payback', title='Cashflow by Year', text='total_payback')
        cf_chart.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        cf_chart.update_layout(xaxis_title='Year', yaxis_title='Amount', yaxis_tickformat=',.0f')
        st.plotly_chart(cf_chart, use_container_width=True)

company_df = filtered.groupby('company_code', dropna=False)['settlement_amount'].sum().reset_index()
company_df['weight'] = company_df['settlement_amount'] / company_df['settlement_amount'].sum() if company_df['settlement_amount'].sum() else 0
company_df = company_df.sort_values('settlement_amount', ascending=False)
cm_left, cm_right = st.columns(2)
with cm_left:
    st.plotly_chart(amount_bar(company_df, 'company_code', 'settlement_amount', 'Amount by Company', 'Teal'), use_container_width=True)
with cm_right:
    st.plotly_chart(weight_bar(company_df, 'company_code', 'weight', 'Weight by Company', 'Greens'), use_container_width=True)

st.subheader('Bond Detail')
detail = filtered.rename(columns=DETAIL_RENAME_MAP).copy()
detail['Face Amount'] = detail['Face Amount'].map(fmt_amount)
detail['Settlement Amount'] = detail['Settlement Amount'].map(fmt_amount)
detail['YTM'] = detail['YTM'].map(fmt_pct)
detail['Duration'] = detail['Duration'].map(fmt_num)
detail['Maturity Date'] = pd.to_datetime(detail['Maturity Date'], errors='coerce').dt.strftime('%Y-%m-%d').fillna('')
st.dataframe(detail, use_container_width=True, hide_index=True)
