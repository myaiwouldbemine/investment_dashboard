import os

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.settings import PROCESSED_DIR
from src.utils.dashboard_access import enforce_dashboard_access

STATUS_OUTSTANDING = '\u672a\u5230\u671f'
STATUS_MATURED = '\u5df2\u5230\u671f'


def fmt_amount(value):
    if value is None or pd.isna(value):
        return '-'
    value = pd.to_numeric(value, errors='coerce')
    if pd.isna(value):
        return '-'
    return f"JPY {value:,.0f}"


def fmt_pct(value):
    if value is None or pd.isna(value):
        return '-'
    value = pd.to_numeric(value, errors='coerce')
    if pd.isna(value):
        return '-'
    return f"{value:.2%}"


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


def panel_layout(fig, title: str):
    fig.update_layout(
        title=title,
        paper_bgcolor='#1a2028',
        plot_bgcolor='#1a2028',
        font=dict(color='#cfd7e3', size=15),
        title_font=dict(size=18, color='#cfd7e3'),
        margin=dict(l=30, r=20, t=60, b=30),
        xaxis=dict(gridcolor='#2a313b', zeroline=False),
        yaxis=dict(gridcolor='#2a313b', zeroline=False),
        legend=dict(title=None, orientation='h', y=1.08, x=0.25),
    )
    return fig


def style_page():
    st.markdown(
        """
        <style>
        .main {background: linear-gradient(180deg, #0f141b 0%, #141a22 100%);}
        h1, h2, h3 {color: #eef2f8;}
        .stMetric {background: #1b212a; border: 1px solid #2b3440; border-radius: 18px; padding: 12px;}
        .block {background: #1a2028; border: 1px solid #2b3440; border-radius: 18px; padding: 12px 12px 4px 12px; margin-bottom: 16px;}
        .table-title {font-size: 18px; font-weight: 800; color: #e7edf5; margin: 6px 0 12px 0;}
        .summary-table {width: 100%; border-collapse: separate; border-spacing: 0; overflow: hidden; border: 1px solid #2b3440; border-radius: 16px;}
        .summary-table th {background: #1d2735; color: #9fb0c5; padding: 12px 14px; font-size: 14px; text-align: center; border-bottom: 1px solid #2b3440;}
        .summary-table td {padding: 12px 14px; border-bottom: 1px solid #2b3440; color: #eef2f8; font-size: 15px;}
        .summary-table tr:last-child td {border-bottom: none;}
        .summary-table td.label-cell {background: #1d2735; color: #9fb0c5; font-weight: 700;}
        .summary-table td.group-cell {background: #1d2735; color: #9fb0c5; font-weight: 700; vertical-align: top;}
        .summary-table td.total-cell {font-weight: 800;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def build_analysis1_detail(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    df['trade_year'] = df['trade_date'].dt.year
    df['bucket'] = 'Other'
    df.loc[df['trade_year'] == 2025, 'bucket'] = '2025 | Matured'
    df.loc[(df['trade_year'] == 2026) & (df['status_group'] == STATUS_MATURED), 'bucket'] = '2026 | Matured'
    df.loc[(df['trade_year'] == 2026) & (df['status_group'] == STATUS_OUTSTANDING), 'bucket'] = '2026 | Outstanding'
    piv = df.pivot_table(index=['company_code', 'underlying'], columns='bucket', values='coupon_income_jpy', aggfunc='sum', fill_value=0).reset_index()
    for col in ['2025 | Matured', '2026 | Matured', '2026 | Outstanding']:
        if col not in piv.columns:
            piv[col] = 0
    piv['Total'] = piv['2025 | Matured'] + piv['2026 | Matured'] + piv['2026 | Outstanding']
    return piv[['company_code', 'underlying', '2025 | Matured', '2026 | Matured', '2026 | Outstanding', 'Total']].sort_values(['company_code', 'Total'], ascending=[True, False])


def build_analysis2_detail(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    piv = df.pivot_table(index=['company_code', 'underlying'], columns='status_group', values='investment_amount_jpy', aggfunc='sum', fill_value=0).reset_index()
    if STATUS_MATURED not in piv.columns:
        piv[STATUS_MATURED] = 0
    if STATUS_OUTSTANDING not in piv.columns:
        piv[STATUS_OUTSTANDING] = 0
    piv['Total'] = piv[STATUS_MATURED] + piv[STATUS_OUTSTANDING]
    return piv[['company_code', 'underlying', STATUS_MATURED, STATUS_OUTSTANDING, 'Total']].sort_values(['company_code', 'Total'], ascending=[True, False])


def render_group_table(df: pd.DataFrame, title: str, group_col: str, item_col: str, value_cols: list[str]):
    if df.empty:
        st.warning(f'{title}: no data')
        return
    rows = []
    for company, part in df.groupby(group_col, sort=False):
        first = True
        for _, row in part.iterrows():
            cells = []
            if first:
                cells.append(f"<td class='group-cell'>{company}</td>")
                first = False
            else:
                cells.append("<td class='group-cell'></td>")
            cells.append(f"<td class='label-cell'>{row[item_col]}</td>")
            for col in value_cols:
                cells.append(f"<td>{fmt_amount(row[col]) if row[col] != 0 else '-'}</td>")
            rows.append(f"<tr>{''.join(cells)}</tr>")
    total_vals = {col: df[col].sum() for col in value_cols}
    total_cells = ["<td class='group-cell total-cell'>Total</td>", "<td class='label-cell'></td>"]
    for col in value_cols:
        total_cells.append(f"<td class='total-cell'>{fmt_amount(total_vals[col])}</td>")
    head = ''.join([f"<th>{col}</th>" for col in value_cols])
    html = f"""
    <div class='block'>
      <div class='table-title'>{title}</div>
      <table class='summary-table'>
        <thead><tr><th>Company</th><th>Underlying</th>{head}</tr></thead>
        <tbody>{''.join(rows)}<tr>{''.join(total_cells)}</tr></tbody>
      </table>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


st.set_page_config(layout='wide')
enforce_dashboard_access()
style_page()

st.title('FCN Portfolio Analysis')
st.caption('Source: FCNs_20260409.xlsx')

position_path = PROCESSED_DIR / 'stg_fcn_position' / 'latest.parquet'
fcn_api = _fetch_api_json('/api/v1/investments/fcn')
fcn_chart_api = _fetch_api_json('/api/v1/investments/charts/fcn')

if not position_path.exists():
    has_chart_data = bool(fcn_chart_api and fcn_chart_api.get('available'))
    if has_chart_data:
        metrics = fcn_chart_api.get('metrics') or {}
        charts = fcn_chart_api.get('charts') or {}
        tables = fcn_chart_api.get('tables') or {}

        sum_invest = pd.to_numeric(metrics.get('sum_invest'), errors='coerce')
        sum_coupon = pd.to_numeric(metrics.get('sum_coupon'), errors='coerce')
        outstanding = pd.to_numeric(metrics.get('outstanding'), errors='coerce')
        due_180 = pd.to_numeric(metrics.get('due_180'), errors='coerce')

        sum_invest = 0.0 if pd.isna(sum_invest) else sum_invest
        sum_coupon = 0.0 if pd.isna(sum_coupon) else sum_coupon
        outstanding = 0.0 if pd.isna(outstanding) else outstanding
        due_180 = 0.0 if pd.isna(due_180) else due_180

        st.info('API mode enabled. Charts are rendered from aggregated API data.')
        k1, k2, k3, k4 = st.columns(4)
        k1.metric('Total Investment', f"JPY {sum_invest/1_000_000_000:.2f}B")
        k2.metric('Total Coupon', f"JPY {sum_coupon/1_000_000:.0f}M")
        k3.metric('Outstanding', f"JPY {outstanding/1_000_000_000:.2f}B")
        k4.metric('Due in 180d', f"JPY {due_180/1_000_000_000:.2f}B")

        company_status = pd.DataFrame(charts.get('company_status') or [])
        company_total = pd.DataFrame(charts.get('company_total') or [])
        if not company_status.empty and {'company_code', 'status_group', 'investment_amount_jpy'}.issubset(company_status.columns):
            fig = px.bar(company_status, x='company_code', y='investment_amount_jpy', color='status_group', barmode='group')
            fig.update_layout(xaxis_title='Company', yaxis_title='Amount')
            left, right = st.columns([1.7, 1.1])
            with left:
                st.plotly_chart(panel_layout(fig, 'Amount by Company and Status'), use_container_width=True, config={'displayModeBar': False})
            with right:
                if not company_total.empty and {'company_code', 'investment_amount_jpy'}.issubset(company_total.columns):
                    company_total = company_total.sort_values('investment_amount_jpy', ascending=False)
                    donut = go.Figure(go.Pie(labels=company_total['company_code'], values=company_total['investment_amount_jpy'], hole=0.5, textinfo='none'))
                    donut.update_layout(title='Company Allocation', paper_bgcolor='#1a2028', plot_bgcolor='#1a2028', font=dict(color='#cfd7e3', size=15), margin=dict(l=10, r=10, t=82, b=10))
                    st.plotly_chart(donut, use_container_width=True, config={'displayModeBar': False})

        analysis1 = pd.DataFrame(tables.get('analysis1') or [])
        analysis2 = pd.DataFrame(tables.get('analysis2') or [])
        render_group_table(analysis1, 'FCN Analysis 1: Coupon Pivot', 'company_code', 'underlying', ['2025 | Matured', '2026 | Matured', '2026 | Outstanding', 'Total'])
        render_group_table(analysis2, 'FCN Analysis 2: Investment Pivot', 'company_code', 'underlying', [STATUS_MATURED, STATUS_OUTSTANDING, 'Total'])
        st.stop()

    if _summary_has_data(fcn_api):
        st.info('API summary mode enabled.')
        st.json(fcn_api)
        st.stop()

    if _api_base_url():
        st.error('API base URL is configured but FCN data is unavailable.')
    else:
        st.warning('No local FCN parquet and no API base URL configured.')
    st.stop()

position_df = pd.read_parquet(position_path)

with st.sidebar:
    st.header('Filters')
    companies = sorted([x for x in position_df['company_code'].dropna().unique().tolist()])
    underlyings = sorted([x for x in position_df['underlying'].dropna().unique().tolist()])
    selected_company = st.multiselect('Company', companies, default=companies)
    selected_underlying = st.multiselect('Underlying', underlyings, default=underlyings)

filtered = position_df[position_df['company_code'].isin(selected_company) & position_df['underlying'].isin(selected_underlying)].copy()

sum_invest = filtered['investment_amount_jpy'].sum()
sum_coupon = filtered['coupon_income_jpy'].sum()
outstanding = filtered.loc[filtered['status_group'] == STATUS_OUTSTANDING, 'investment_amount_jpy'].sum()
due_180 = filtered.loc[filtered['days_to_maturity'].between(0, 180, inclusive='both'), 'investment_amount_jpy'].sum()

k1, k2, k3, k4 = st.columns(4)
k1.metric('Total Investment', f"JPY {sum_invest/1_000_000_000:.2f}B")
k2.metric('Total Coupon', f"JPY {sum_coupon/1_000_000:.0f}M")
k3.metric('Outstanding', f"JPY {outstanding/1_000_000_000:.2f}B")
k4.metric('Due in 180d', f"JPY {due_180/1_000_000_000:.2f}B")

company_status = filtered.groupby(['company_code', 'status_group'], dropna=False)[['investment_amount_jpy']].sum().reset_index()
fig = px.bar(company_status, x='company_code', y='investment_amount_jpy', color='status_group', barmode='group')
fig.update_layout(xaxis_title='Company', yaxis_title='Amount')
left, right = st.columns([1.7, 1.1])
with left:
    st.plotly_chart(panel_layout(fig, 'Amount by Company and Status'), use_container_width=True, config={'displayModeBar': False})
with right:
    company_total = filtered.groupby('company_code', dropna=False)[['investment_amount_jpy']].sum().reset_index().sort_values('investment_amount_jpy', ascending=False)
    donut = go.Figure(go.Pie(labels=company_total['company_code'], values=company_total['investment_amount_jpy'], hole=0.5, textinfo='none'))
    donut.update_layout(title='Company Allocation', paper_bgcolor='#1a2028', plot_bgcolor='#1a2028', font=dict(color='#cfd7e3', size=15), margin=dict(l=10, r=10, t=82, b=10))
    st.plotly_chart(donut, use_container_width=True, config={'displayModeBar': False})

analysis1 = build_analysis1_detail(filtered)
analysis2 = build_analysis2_detail(filtered)
render_group_table(analysis1, 'FCN Analysis 1: Coupon Pivot', 'company_code', 'underlying', ['2025 | Matured', '2026 | Matured', '2026 | Outstanding', 'Total'])
render_group_table(analysis2, 'FCN Analysis 2: Investment Pivot', 'company_code', 'underlying', [STATUS_MATURED, STATUS_OUTSTANDING, 'Total'])

st.subheader('Outstanding FCN Detail')
detail = filtered.loc[filtered['status_group'] == STATUS_OUTSTANDING].rename(columns={'company_code': 'Company', 'underlying': 'Underlying', 'tenor_months': 'Tenor(M)', 'coupon_rate': 'Coupon', 'put_strike_pct': 'Put Strike', 'spot_price': 'Spot Price', 'strike_price': 'Strike Price', 'trade_date': 'Trade Date', 'maturity_date': 'Maturity Date', 'investment_amount_jpy': 'Investment', 'coupon_income_jpy': 'Coupon Income'}).copy()
for col in ['Trade Date', 'Maturity Date']:
    detail[col] = pd.to_datetime(detail[col], errors='coerce').dt.strftime('%Y-%m-%d').fillna('')
for col in ['Investment', 'Coupon Income', 'Spot Price', 'Strike Price']:
    detail[col] = detail[col].map(fmt_amount)
detail['Coupon'] = detail['Coupon'].map(fmt_pct)
detail['Put Strike'] = detail['Put Strike'].map(fmt_pct)
st.dataframe(detail[['Company', 'Underlying', 'Tenor(M)', 'Coupon', 'Put Strike', 'Spot Price', 'Strike Price', 'Trade Date', 'Maturity Date', 'Investment', 'Coupon Income']], use_container_width=True, hide_index=True)
