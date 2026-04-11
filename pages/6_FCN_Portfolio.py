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
        return '-'
    value = pd.to_numeric(value, errors='coerce')
    if pd.isna(value):
        return '-'
    return f"¥{value:,.0f}"


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
    return (_get_secret('INVESTMENT_API_BASE_URL') or _get_secret('INVESTMENT_DASHBOARD_API_BASE_URL')).rstrip('/')


def _fetch_api_summary(endpoint: str) -> dict[str, object] | None:
    base_url = _api_base_url()
    if not base_url:
        return None
    try:
        with httpx.Client(timeout=4.0) as client:
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
        .stCaptionContainer, .stMarkdown p {color: #aeb8c4 !important;}
        .stMetric {
            background: #1b212a;
            border: 1px solid #2b3440;
            border-radius: 18px;
            padding: 12px;
        }
        .stMetric label, .stMetric [data-testid="stMetricLabel"], .stMetric [data-testid="stMetricValue"] {
            color: #eef2f8 !important;
        }
        .block {
            background: #1a2028;
            border: 1px solid #2b3440;
            border-radius: 18px;
            padding: 12px 12px 4px 12px;
            margin-bottom: 16px;
        }
        .table-title {
            font-size: 18px;
            font-weight: 800;
            color: #e7edf5;
            margin: 6px 0 12px 0;
        }
        .summary-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            overflow: hidden;
            border: 1px solid #2b3440;
            border-radius: 16px;
        }
        .summary-table th {
            background: #1d2735;
            color: #9fb0c5;
            padding: 12px 14px;
            font-size: 14px;
            text-align: center;
            border-bottom: 1px solid #2b3440;
        }
        .summary-table td {
            padding: 12px 14px;
            border-bottom: 1px solid #2b3440;
            color: #eef2f8;
            font-size: 15px;
        }
        .summary-table tr:last-child td {border-bottom: none;}
        .summary-table td.label-cell {
            background: #1d2735;
            color: #9fb0c5;
            font-weight: 700;
        }
        .summary-table td.group-cell {
            background: #1d2735;
            color: #9fb0c5;
            font-weight: 700;
            vertical-align: top;
        }
        .summary-table td.total-cell {
            font-weight: 800;
        }
        .stDataFrame {background: rgba(255,255,255,0.04); border-radius: 14px;}
        section[data-testid="stSidebar"] [data-baseweb="tag"] {background: #4b5058 !important; border: 1px solid #666c75 !important;}
        section[data-testid="stSidebar"] [data-baseweb="tag"] span {color: #f5f7fa !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def build_analysis1_detail(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    df['trade_year'] = df['trade_date'].dt.year
    df['bucket'] = '其他'
    df.loc[df['trade_year'] == 2025, 'bucket'] = '2025年 | 已到期'
    df.loc[(df['trade_year'] == 2026) & (df['status_group'] == '已到期'), 'bucket'] = '2026年 | 已到期'
    df.loc[(df['trade_year'] == 2026) & (df['status_group'] == '未到期'), 'bucket'] = '2026年 | 未到期'
    piv = df.pivot_table(index=['company_code', 'underlying'], columns='bucket', values='coupon_income_jpy', aggfunc='sum', fill_value=0).reset_index()
    for col in ['2025年 | 已到期', '2026年 | 已到期', '2026年 | 未到期']:
        if col not in piv.columns:
            piv[col] = 0
    piv['總計'] = piv['2025年 | 已到期'] + piv['2026年 | 已到期'] + piv['2026年 | 未到期']
    return piv[['company_code', 'underlying', '2025年 | 已到期', '2026年 | 已到期', '2026年 | 未到期', '總計']].sort_values(['company_code', '總計'], ascending=[True, False])


def build_analysis2_detail(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    piv = df.pivot_table(index=['company_code', 'underlying'], columns='status_group', values='investment_amount_jpy', aggfunc='sum', fill_value=0).reset_index()
    for col in ['已到期', '未到期']:
        if col not in piv.columns:
            piv[col] = 0
    piv['總計'] = piv['已到期'] + piv['未到期']
    return piv[['company_code', 'underlying', '已到期', '未到期', '總計']].sort_values(['company_code', '總計'], ascending=[True, False])


def render_group_table(df: pd.DataFrame, title: str, group_col: str, item_col: str, value_cols: list[str]):
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
    total_cells = ["<td class='group-cell total-cell'>總計</td>", "<td class='label-cell'></td>"]
    for col in value_cols:
        total_cells.append(f"<td class='total-cell'>{fmt_amount(total_vals[col])}</td>")
    head = ''.join([f"<th>{col}</th>" for col in value_cols])
    html = f"""
    <div class='block'>
      <div class='table-title'>{title}</div>
      <table class='summary-table'>
        <thead>
          <tr><th>公司</th><th>標的</th>{head}</tr>
        </thead>
        <tbody>
          {''.join(rows)}
          <tr>{''.join(total_cells)}</tr>
        </tbody>
      </table>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


st.set_page_config(layout='wide')
enforce_dashboard_access()
style_page()

st.title('FCN 部位分析')
st.caption('資料來源：FCNs_20260409.xlsx')

position_path = PROCESSED_DIR / 'stg_fcn_position' / 'latest.parquet'
fcn_api = _fetch_api_summary('/api/v1/investments/fcn')

if not position_path.exists():
    if _summary_has_data(fcn_api):
        lines = fcn_api.get('lines') or []
        st.info('目前為 API 摘要模式（雲端無本機 parquet）。明細圖表需本機資料。')
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('總投資額', _line_value(lines, ('總投資額：', '總投資額:')) or 'N/A')
        c2.metric('總利息', _line_value(lines, ('總利息：', '總利息:')) or 'N/A')
        c3.metric('未到期金額', _line_value(lines, ('未到期金額：', '未到期金額:')) or 'N/A')
        c4.metric('未到期利息', _line_value(lines, ('未到期利息：', '未到期利息:')) or 'N/A')
        st.stop()
    if _api_base_url():
        st.error('已設定投資 API 位址，但目前無法取得FCN資料。')
    else:
        st.warning('尚未找到已處理的FCN資料，且未設定投資 API 位址（INVESTMENT_API_BASE_URL）。')
    st.stop()

position_df = pd.read_parquet(position_path)

with st.sidebar:
    st.header('篩選條件')
    companies = sorted([x for x in position_df['company_code'].dropna().unique().tolist()])
    underlyings = sorted([x for x in position_df['underlying'].dropna().unique().tolist()])
    selected_company = st.multiselect('公司別', companies, default=companies)
    selected_underlying = st.multiselect('標的', underlyings, default=underlyings)

filtered = position_df[
    position_df['company_code'].isin(selected_company)
    & position_df['underlying'].isin(selected_underlying)
].copy()

sum_invest = filtered['investment_amount_jpy'].sum()
sum_coupon = filtered['coupon_income_jpy'].sum()
outstanding = filtered.loc[filtered['status_group'] == '未到期', 'investment_amount_jpy'].sum()
due_180 = filtered.loc[filtered['days_to_maturity'].between(0, 180, inclusive='both'), 'investment_amount_jpy'].sum()

k1, k2, k3, k4 = st.columns(4)
k1.metric('總投資金額', f"¥{sum_invest/1_000_000_000:.2f}B")
k2.metric('累計利息', f"¥{sum_coupon/1_000_000:.0f}M")
k3.metric('未到期金額', f"¥{outstanding/1_000_000_000:.2f}B")
k4.metric('180天內到期', f"¥{due_180/1_000_000_000:.2f}B")

company_status = filtered.groupby(['company_code', 'status_group'], dropna=False)[['investment_amount_jpy']].sum().reset_index()
fig = px.bar(company_status, x='company_code', y='investment_amount_jpy', color='status_group', barmode='group', color_discrete_map={'已到期': '#3b7bbb', '未到期': '#76b447'})
fig.update_layout(xaxis_title='公司', yaxis_title='投資金額')
fig.update_traces(hovertemplate='公司: %{x}<br>金額: %{y:,.0f}<extra></extra>')
left, right = st.columns([1.7, 1.1])
with left:
    st.plotly_chart(panel_layout(fig, '各公司投資金額（已到期 vs 未到期）'), use_container_width=True, config={'displayModeBar': False})
with right:
    company_total = filtered.groupby('company_code', dropna=False)[['investment_amount_jpy']].sum().reset_index()
    company_total['sort_key'] = company_total['investment_amount_jpy'].rank(method='first', ascending=False)
    company_total = company_total.sort_values(['sort_key', 'company_code']).drop(columns=['sort_key'])
    color_map = {
        'BOSS': '#6eaee3',
        'HSB': '#2f78c4',
        'WTC': '#8bc06a',
        'GBM': '#f0b94b',
    }
    donut = go.Figure(
        go.Pie(
            labels=company_total['company_code'],
            values=company_total['investment_amount_jpy'],
            hole=0.5,
            textinfo='none',
            marker=dict(colors=[color_map.get(label, '#9aa7b8') for label in company_total['company_code']]),
            hovertemplate='公司: %{label}<br>投資金額: ¥%{value:,.0f}<br>占比: %{percent}<extra></extra>'
        )
    )
    donut.update_layout(
        title='投資金額佔比',
        paper_bgcolor='#1a2028',
        plot_bgcolor='#1a2028',
        font=dict(color='#cfd7e3', size=15),
        title_font=dict(size=18, color='#cfd7e3'),
        margin=dict(l=10, r=10, t=82, b=10),
        legend=dict(orientation='h', y=1.12, x=0.18, font=dict(size=13))
    )
    st.plotly_chart(donut, use_container_width=True, config={'displayModeBar': False})

analysis1 = build_analysis1_detail(filtered)
analysis2 = build_analysis2_detail(filtered)
render_group_table(analysis1, 'FCN Analysis 1：利息(日元)樞紐分析表', 'company_code', 'underlying', ['2025年 | 已到期', '2026年 | 已到期', '2026年 | 未到期', '總計'])
render_group_table(analysis2, 'FCN Analysis 2：投資金額(日元)樞紐分析表', 'company_code', 'underlying', ['已到期', '未到期', '總計'])

st.subheader('未到期 FCN 明細查詢')
detail = filtered.loc[filtered['status_group'] == '未到期'].rename(columns={
    'company_code': '公司別',
        'underlying': '標的',
    'tenor_months': '月數',
    'coupon_rate': '票息',
    'put_strike_pct': 'Put Strike',
    'spot_price': 'Spot Price',
    'strike_price': 'Strike Price',
    'trade_date': '交易日',
    'maturity_date': '到期日',
    'investment_amount_jpy': '投資金額',
    'coupon_income_jpy': '利息',
}).copy()
for col in ['交易日', '到期日']:
    detail[col] = pd.to_datetime(detail[col], errors='coerce').dt.strftime('%Y-%m-%d').fillna('')
for col in ['投資金額', '利息', 'Spot Price', 'Strike Price']:
    detail[col] = detail[col].map(fmt_amount)
detail['票息'] = detail['票息'].map(fmt_pct)
detail['Put Strike'] = detail['Put Strike'].map(fmt_pct)
st.dataframe(detail[['公司別', '標的', '月數', '票息', 'Put Strike', 'Spot Price', 'Strike Price', '交易日', '到期日', '投資金額', '利息']], use_container_width=True, hide_index=True)










