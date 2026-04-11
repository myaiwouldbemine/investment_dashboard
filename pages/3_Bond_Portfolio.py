import os

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

from config.settings import PROCESSED_DIR
from src.utils.dashboard_access import enforce_dashboard_access

CASHFLOW_TYPE_LABELS = {
    'coupon': '配息',
    'coupon_principal': '本利回收',
}

DETAIL_RENAME_MAP = {
    'isin': 'ISIN',
    'company_code': '公司別',
    'issuer_name': '發行機構',
    'counterparty': '交易對象',
    'currency': '幣別',
    'rating_bucket': '信評',
    'bond_type': '類型',
    'face_amount': '面額',
    'settlement_amount': '交割金額',
    'ytm': '殖利率',
    'duration_years': '存續',
    'maturity_date': '到期日',
    'maturity_year': '到期年',
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

def amount_bar(frame: pd.DataFrame, x: str, y: str, title: str, color_scale: str):
    chart = px.bar(frame, x=x, y=y, title=title, color=y, color_continuous_scale=color_scale, text=y)
    chart.update_traces(texttemplate='%{text:,.0f}', textposition='outside', hovertemplate=f'{x}: %{{x}}<br>金額: %{{y:,.0f}}<extra></extra>')
    chart.update_layout(coloraxis_showscale=False, xaxis_title=x, yaxis_title='金額', yaxis_tickformat=',.0f')
    return chart


def weight_bar(frame: pd.DataFrame, x: str, y: str, title: str, color_scale: str):
    chart = px.bar(frame, x=x, y=y, title=title, color=y, color_continuous_scale=color_scale, text=y)
    chart.update_traces(texttemplate='%{text:.2%}', textposition='outside', hovertemplate=f'{x}: %{{x}}<br>比重: %{{y:.2%}}<extra></extra>')
    chart.update_layout(coloraxis_showscale=False, xaxis_title=x, yaxis_title='比重', yaxis_tickformat='.0%')
    return chart


st.set_page_config(layout='wide')
enforce_dashboard_access()
st.markdown("""
<style>
.main {background: linear-gradient(180deg, #f7f2eb 0%, #fcfaf7 100%);}
h1, h2, h3 {color: #241c15;}
.stMetric {background: #23262d; border: 1px solid #4a4f59; padding: 10px; border-radius: 16px; box-shadow: 0 4px 14px rgba(0,0,0,0.28);} .stMetric label, .stMetric [data-testid="stMetricLabel"], .stMetric [data-testid="stMetricValue"] {color: #f7f7f7 !important;}
.stDataFrame {background: rgba(255,255,255,0.72); border-radius: 16px;}
section[data-testid="stSidebar"] [data-baseweb="tag"] {background: #4b5058 !important; border: 1px solid #666c75 !important;}
section[data-testid="stSidebar"] [data-baseweb="tag"] span {color: #f5f7fa !important;}
section[data-testid="stSidebar"] .stSlider [data-baseweb="slider"] > div > div {background: #a8afb8 !important;}
section[data-testid="stSidebar"] .stSlider [role="slider"] {background: #6f7782 !important; border-color: #6f7782 !important;}
</style>
""", unsafe_allow_html=True)
st.title('債券投資部位分析')
st.caption('資料來源：Bonds Analysis.xlsx')

position_path = PROCESSED_DIR / 'mart_bond_dashboard_position' / 'latest.parquet'
cashflow_path = PROCESSED_DIR / 'mart_bond_dashboard_cashflow' / 'latest.parquet'

bond_api = _fetch_api_summary('/api/v1/investments/bonds')

if not position_path.exists():
    if _summary_has_data(bond_api):
        lines = bond_api.get('lines') or []
        st.info('目前為 API 摘要模式（雲端無本機 parquet）。明細圖表需本機資料。')
        c1, c2, c3 = st.columns(3)
        c1.metric('投資金額', _line_value(lines, ('投資金額：', '投資金額:')) or 'N/A')
        c2.metric('平均收益率', _line_value(lines, ('平均收益率：', '平均收益率:')) or 'N/A')
        c3.metric('平均存續年數', _line_value(lines, ('平均存續年數：', '平均存續年數:')) or 'N/A')
        st.stop()
    if _api_base_url():
        st.error('已設定投資 API 位址，但目前無法取得債券資料。')
    else:
        st.warning('尚未找到已處理的債券資料，且未設定投資 API 位址（INVESTMENT_API_BASE_URL）。')
    st.stop()

position_df = pd.read_parquet(position_path)
cashflow_df = pd.read_parquet(cashflow_path) if cashflow_path.exists() else pd.DataFrame()

if not cashflow_df.empty:
    cashflow_df['現金流類型'] = cashflow_df['cashflow_type'].map(CASHFLOW_TYPE_LABELS).fillna(cashflow_df['cashflow_type'])

with st.sidebar:
    st.header('篩選條件')
    currencies = sorted([x for x in position_df['currency'].dropna().unique().tolist()])
    ratings = sorted([str(x) for x in position_df['rating_bucket'].dropna().unique().tolist()])
    counterparties = sorted([str(x) for x in position_df['counterparty'].dropna().unique().tolist()])
    bond_types = sorted([str(x) for x in position_df['bond_type'].dropna().unique().tolist()])

    selected_currency = st.multiselect('幣別', currencies, default=currencies)
    selected_rating = st.multiselect('信評', ratings, default=ratings)
    selected_counterparty = st.multiselect('交易對象', counterparties, default=counterparties)
    selected_bond_type = st.multiselect('類型', bond_types, default=bond_types)
    min_year, max_year = int(position_df['maturity_year'].min()), int(position_df['maturity_year'].max())
    maturity_range = st.slider('到期年', min_year, max_year, (min_year, max_year))

filtered = position_df[
    position_df['currency'].isin(selected_currency)
    & position_df['rating_bucket'].astype(str).isin(selected_rating)
    & position_df['counterparty'].astype(str).isin(selected_counterparty)
    & position_df['bond_type'].astype(str).isin(selected_bond_type)
    & position_df['maturity_year'].between(maturity_range[0], maturity_range[1])
].copy()

st.subheader('整體概況')
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric('投資金額', fmt_amount(filtered['face_amount'].sum()))
c2.metric('平均收益率', fmt_pct(filtered['ytm'].mean()) if not filtered['ytm'].dropna().empty else 'N/A')
c3.metric('平均存續年數', fmt_num(filtered['duration_years'].mean()) if not filtered['duration_years'].dropna().empty else 'N/A')
c4.metric('發行機構數', int(filtered['issuer_name'].nunique()))
c5.metric('部位筆數', int(len(filtered)))

row1_left, row1_right = st.columns(2)
with row1_left:
    chart = px.pie(filtered, names='currency', values='face_amount', title='幣別分析')
    chart.update_traces(textposition='inside', texttemplate='%{label}<br>%{percent}', hovertemplate='幣別: %{label}<br>金額: %{value:,.0f}<br>比重: %{percent}<extra></extra>')
    st.plotly_chart(chart, use_container_width=True)
with row1_right:
    rating_df = filtered.groupby('rating_bucket', dropna=False)['face_amount'].sum().reset_index().sort_values('face_amount', ascending=False)
    chart = amount_bar(rating_df, 'rating_bucket', 'face_amount', '信評金額', 'Blues')
    chart.update_layout(xaxis_title='信評')
    st.plotly_chart(chart, use_container_width=True)

st.subheader('交易對象分析')
counterparty_df = filtered.groupby('counterparty', dropna=False)['face_amount'].sum().reset_index().sort_values('face_amount', ascending=False)
counterparty_df['weight'] = counterparty_df['face_amount'] / counterparty_df['face_amount'].sum() if counterparty_df['face_amount'].sum() else 0
counterparty_left, counterparty_right = st.columns(2)
with counterparty_left:
    chart = amount_bar(counterparty_df, 'counterparty', 'face_amount', '交易對象金額分析', 'Sunset')
    chart.update_layout(xaxis_title='交易對象')
    st.plotly_chart(chart, use_container_width=True)
with counterparty_right:
    chart = weight_bar(counterparty_df, 'counterparty', 'weight', '交易對象比重分析', 'Sunset')
    chart.update_layout(xaxis_title='交易對象')
    st.plotly_chart(chart, use_container_width=True)

st.subheader('類型分析')
bond_type_df = filtered.groupby('bond_type', dropna=False)['face_amount'].sum().reset_index().sort_values('face_amount', ascending=False)
bond_type_df['weight'] = bond_type_df['face_amount'] / bond_type_df['face_amount'].sum() if bond_type_df['face_amount'].sum() else 0
type_left, type_right = st.columns(2)
with type_left:
    chart = amount_bar(bond_type_df, 'bond_type', 'face_amount', '類型金額分析', 'Purples')
    chart.update_layout(xaxis_title='類型')
    st.plotly_chart(chart, use_container_width=True)
with type_right:
    chart = weight_bar(bond_type_df, 'bond_type', 'weight', '類型比重分析', 'Purples')
    chart.update_layout(xaxis_title='類型')
    st.plotly_chart(chart, use_container_width=True)

row3_left, row3_right = st.columns(2)
with row3_left:
    maturity_df = filtered.groupby('maturity_year', dropna=False)['face_amount'].sum().reset_index().sort_values('maturity_year')
    chart = amount_bar(maturity_df, 'maturity_year', 'face_amount', '到期年分析', 'Oranges')
    chart.update_layout(xaxis_title='到期年')
    st.plotly_chart(chart, use_container_width=True)
with row3_right:
    if not cashflow_df.empty:
        flow_df = cashflow_df.sort_values(['cashflow_year', 'cashflow_month'])
        chart = px.bar(flow_df, x='cashflow_year', y='total_payback', color='現金流類型', barmode='group', title='本利回收分析', text='total_payback')
        chart.update_traces(texttemplate='%{text:,.0f}', textposition='outside', hovertemplate='年度: %{x}<br>金額: %{y:,.0f}<br>類型: %{fullData.name}<extra></extra>')
        chart.update_layout(xaxis_title='年度', yaxis_title='金額', yaxis_tickformat=',.0f', legend_title='現金流類型')
        st.plotly_chart(chart, use_container_width=True)

st.subheader('公司別投資分析')
company_df = filtered.groupby('company_code', dropna=False)['face_amount'].sum().reset_index()
company_df['weight'] = company_df['face_amount'] / company_df['face_amount'].sum() if company_df['face_amount'].sum() else 0
company_df = company_df.sort_values('face_amount', ascending=False)

company_left, company_right = st.columns(2)
with company_left:
    amount_chart = amount_bar(company_df, 'company_code', 'face_amount', '公司別金額', 'Teal')
    amount_chart.update_layout(xaxis_title='公司別')
    st.plotly_chart(amount_chart, use_container_width=True)
with company_right:
    weight_chart = weight_bar(company_df, 'company_code', 'weight', '公司別比重', 'Greens')
    weight_chart.update_layout(xaxis_title='公司別')
    st.plotly_chart(weight_chart, use_container_width=True)

st.subheader('債券明細查詢')

detail = filtered.rename(columns=DETAIL_RENAME_MAP).copy()
detail['面額'] = detail['面額'].map(fmt_amount)
detail['交割金額'] = detail['交割金額'].map(fmt_amount)
detail['殖利率'] = detail['殖利率'].map(fmt_pct)
detail['存續'] = detail['存續'].map(fmt_num)
detail['到期日'] = pd.to_datetime(detail['到期日'], errors='coerce').dt.strftime('%Y-%m-%d').fillna('')

st.dataframe(detail, use_container_width=True, hide_index=True)
