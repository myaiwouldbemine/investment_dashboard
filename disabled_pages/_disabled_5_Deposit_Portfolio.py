import pandas as pd
import plotly.express as px
import streamlit as st

from config.settings import PROCESSED_DIR


def fmt_amount(value):
    if value is None or pd.isna(value):
        return 'N/A'
    return f"{value:,.0f}"


def fmt_pct(value):
    if value is None or pd.isna(value):
        return 'N/A'
    return f"{value:.2%}"


def fmt_rate(value):
    if value is None or pd.isna(value):
        return ''
    return f"{value:.2%}"


def fmt_date(value):
    if value is None or pd.isna(value):
        return ''
    ts = pd.to_datetime(value, errors='coerce')
    return '' if pd.isna(ts) else ts.strftime('%Y-%m-%d')


def amount_bar(frame: pd.DataFrame, x: str, y: str, title: str, color_scale: str):
    chart = px.bar(frame, x=x, y=y, title=title, color=y, color_continuous_scale=color_scale, text=y)
    chart.update_traces(
        texttemplate='%{text:,.0f}',
        textposition='outside',
        hovertemplate=f'{x}: %{{x}}<br>金額: %{{y:,.0f}}<extra></extra>',
    )
    chart.update_layout(coloraxis_showscale=False, xaxis_title=x, yaxis_title='金額', yaxis_tickformat=',.0f')
    return chart


def weight_bar(frame: pd.DataFrame, x: str, y: str, title: str, color_scale: str):
    chart = px.bar(frame, x=x, y=y, title=title, color=y, color_continuous_scale=color_scale, text=y)
    chart.update_traces(
        texttemplate='%{text:.2%}',
        textposition='outside',
        hovertemplate=f'{x}: %{{x}}<br>比重: %{{y:.2%}}<extra></extra>',
    )
    chart.update_layout(coloraxis_showscale=False, xaxis_title=x, yaxis_title='比重', yaxis_tickformat='.0%')
    return chart


def sort_and_weight(frame: pd.DataFrame, group_col: str, top_n: int | None = None) -> pd.DataFrame:
    grouped = frame.groupby(group_col, dropna=False)[['amount_rmb_equiv']].sum().reset_index()
    grouped = grouped.sort_values('amount_rmb_equiv', ascending=False)
    if top_n is not None:
        grouped = grouped.head(top_n)
    total = grouped['amount_rmb_equiv'].sum()
    grouped['weight'] = grouped['amount_rmb_equiv'] / total if total else 0
    return grouped.reset_index(drop=True)


st.set_page_config(layout='wide')
st.markdown("""
<style>
.main {background: linear-gradient(180deg, #f7f2eb 0%, #fcfaf7 100%);} 
h1, h2, h3 {color: #241c15;} 
.stMetric {background: #23262d; border: 1px solid #4a4f59; padding: 10px; border-radius: 16px; box-shadow: 0 4px 14px rgba(0,0,0,0.28);} 
.stMetric label, .stMetric [data-testid="stMetricLabel"], .stMetric [data-testid="stMetricValue"] {color: #f7f7f7 !important;} 
.stDataFrame {background: rgba(255,255,255,0.72); border-radius: 16px;} 
</style>
""", unsafe_allow_html=True)
st.title('存款部位分析')
st.caption('資料來源：PSA大陸子公司人民幣與美元淨部位彙總_202602.xlsx')

stg_path = PROCESSED_DIR / 'stg_deposit_position' / 'latest.parquet'
if not stg_path.exists():
    st.warning('尚未找到已處理的存款資料，請先執行 `python run_pipeline.py`。')
    st.stop()

position_df = pd.read_parquet(stg_path)

with st.sidebar:
    st.header('篩選條件')
    companies = sorted([x for x in position_df['company_group'].dropna().unique().tolist()])
    banks = sorted([x for x in position_df['bank_name'].dropna().unique().tolist()])
    currencies = sorted([x for x in position_df['currency'].dropna().unique().tolist()])
    deposit_types = sorted([x for x in position_df['deposit_type'].dropna().unique().tolist()])
    bank_categories = sorted([x for x in position_df['bank_category'].dropna().unique().tolist()])
    selected_company = st.multiselect('公司別', companies, default=companies)
    selected_bank = st.multiselect('銀行', banks, default=banks)
    selected_currency = st.multiselect('幣別', currencies, default=currencies)
    selected_type = st.multiselect('類型', deposit_types, default=deposit_types)
    selected_bank_category = st.multiselect('銀行分類', bank_categories, default=bank_categories)
    maturity_max = int(max(position_df['days_to_maturity'].dropna().max(), 30)) if position_df['days_to_maturity'].notna().any() else 365
    selected_days = st.slider('到期天數', min_value=-3650, max_value=maturity_max, value=(-3650, maturity_max))

filtered = position_df[
    position_df['company_group'].isin(selected_company)
    & position_df['bank_name'].isin(selected_bank)
    & position_df['currency'].isin(selected_currency)
    & position_df['deposit_type'].isin(selected_type)
].copy()
if selected_bank_category:
    filtered = filtered.loc[filtered['bank_category'].fillna('').isin(selected_bank_category)]
filtered = filtered.loc[filtered['days_to_maturity'].fillna(999999).between(selected_days[0], selected_days[1])]

st.subheader('整體概況')
total = filtered['amount_rmb_equiv'].sum()
rmb_amount = filtered.loc[filtered['currency'] == 'RMB', 'amount'].sum()
usd_rmb = filtered.loc[filtered['currency'] == 'USD', 'amount_rmb_equiv'].sum()
due_180 = filtered.loc[filtered['days_to_maturity'].between(0, 180, inclusive='both'), 'amount_rmb_equiv'].sum()
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric('總存款額', fmt_amount(total))
c2.metric('人民幣金額', fmt_amount(rmb_amount))
c3.metric('美元折人民幣', fmt_amount(usd_rmb))
c4.metric('往來銀行數', int(filtered['bank_name'].dropna().nunique()))
c5.metric('部位筆數', int(len(filtered)))
c6.metric('近180天到期額', fmt_amount(due_180))

company_df = sort_and_weight(filtered, 'company_group')
bank_df = sort_and_weight(filtered, 'bank_name', top_n=15)
currency_df = sort_and_weight(filtered, 'currency')
type_df = sort_and_weight(filtered, 'deposit_type')

st.subheader('結構分析')
r1c1, r1c2 = st.columns(2)
with r1c1:
    chart = amount_bar(company_df, 'company_group', 'amount_rmb_equiv', '公司別金額分析', 'Teal')
    chart.update_layout(xaxis_title='公司別')
    st.plotly_chart(chart, use_container_width=True)
with r1c2:
    chart = weight_bar(company_df, 'company_group', 'weight', '公司別比重分析', 'Greens')
    chart.update_layout(xaxis_title='公司別')
    st.plotly_chart(chart, use_container_width=True)

r2c1, r2c2 = st.columns(2)
with r2c1:
    chart = amount_bar(bank_df, 'bank_name', 'amount_rmb_equiv', '銀行別金額分析', 'Sunset')
    chart.update_layout(xaxis_title='銀行')
    st.plotly_chart(chart, use_container_width=True)
with r2c2:
    chart = weight_bar(bank_df, 'bank_name', 'weight', '銀行別比重分析', 'Sunset')
    chart.update_layout(xaxis_title='銀行')
    st.plotly_chart(chart, use_container_width=True)

r3c1, r3c2 = st.columns(2)
with r3c1:
    chart = amount_bar(currency_df, 'currency', 'amount_rmb_equiv', '幣別金額分析', 'Blues')
    chart.update_layout(xaxis_title='幣別')
    st.plotly_chart(chart, use_container_width=True)
with r3c2:
    chart = weight_bar(currency_df, 'currency', 'weight', '幣別比重分析', 'Blues')
    chart.update_layout(xaxis_title='幣別')
    st.plotly_chart(chart, use_container_width=True)

r4c1, r4c2 = st.columns(2)
with r4c1:
    chart = amount_bar(type_df, 'deposit_type', 'amount_rmb_equiv', '類型金額分析', 'Purples')
    chart.update_layout(xaxis_title='類型')
    st.plotly_chart(chart, use_container_width=True)
with r4c2:
    chart = weight_bar(type_df, 'deposit_type', 'weight', '類型比重分析', 'Purples')
    chart.update_layout(xaxis_title='類型')
    st.plotly_chart(chart, use_container_width=True)

st.subheader('到期分析')
maturity_df = filtered.loc[filtered['maturity_date'].notna()].copy()
if not maturity_df.empty:
    maturity_df['maturity_month'] = pd.to_datetime(maturity_df['maturity_date'], errors='coerce').dt.strftime('%Y-%m')
    maturity_chart_df = maturity_df.groupby('maturity_month', dropna=False)[['amount_rmb_equiv']].sum().reset_index().sort_values('maturity_month')
    chart = amount_bar(maturity_chart_df, 'maturity_month', 'amount_rmb_equiv', '到期月份分析', 'Oranges')
    chart.update_layout(xaxis_title='到期月份')
    st.plotly_chart(chart, use_container_width=True)

    d1, d2, d3 = st.columns(3)
    d1.metric('近30天到期額', fmt_amount(filtered.loc[filtered['days_to_maturity'].between(0, 30, inclusive='both'), 'amount_rmb_equiv'].sum()))
    d2.metric('近90天到期額', fmt_amount(filtered.loc[filtered['days_to_maturity'].between(0, 90, inclusive='both'), 'amount_rmb_equiv'].sum()))
    d3.metric('近180天到期額', fmt_amount(filtered.loc[filtered['days_to_maturity'].between(0, 180, inclusive='both'), 'amount_rmb_equiv'].sum()))

    st.markdown('**近期到期明細**')
    due_list = maturity_df.sort_values(['days_to_maturity', 'amount_rmb_equiv'], ascending=[True, False]).copy()
    due_list = due_list.rename(columns={
        'company_group': '公司別',
        'company_name': '公司名稱',
        'bank_name': '銀行',
        'branch_name': '分行',
        'currency': '幣別',
        'deposit_type': '類型',
        'amount': '金額',
        'amount_rmb_equiv': '折人民幣金額',
        'deposit_rate': '利率',
        'maturity_date': '到期日',
        'days_to_maturity': '剩餘天數',
    })
    for col in ['金額', '折人民幣金額']:
        due_list[col] = due_list[col].map(fmt_amount)
    due_list['利率'] = due_list['利率'].map(fmt_rate)
    due_list['到期日'] = due_list['到期日'].map(fmt_date)
    st.dataframe(
        due_list[['公司別', '公司名稱', '銀行', '幣別', '類型', '金額', '折人民幣金額', '利率', '到期日', '剩餘天數']].head(20),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info('目前篩選條件下沒有到期資料。')

st.subheader('存款明細查詢')
detail = filtered.rename(columns={
    'company_group': '公司別',
    'company_name': '公司名稱',
    'bank_name': '銀行',
    'branch_name': '分行',
    'currency': '幣別',
    'deposit_type': '類型',
    'amount': '金額',
    'amount_rmb_equiv': '折人民幣金額',
    'deposit_rate': '利率',
    'start_date': '起存日',
    'maturity_date': '到期日',
    'days_to_maturity': '剩餘天數',
    'bank_category': '銀行分類',
    'note': '備註',
}).copy()
for col in ['金額', '折人民幣金額']:
    detail[col] = detail[col].map(fmt_amount)
detail['利率'] = detail['利率'].map(fmt_rate)
detail['起存日'] = detail['起存日'].map(fmt_date)
detail['到期日'] = detail['到期日'].map(fmt_date)
detail = detail.sort_values(['公司別', '銀行', '幣別', '類型', '折人民幣金額'], ascending=[True, True, True, True, False])
st.dataframe(
    detail[['公司別', '公司名稱', '銀行', '分行', '幣別', '類型', '金額', '折人民幣金額', '利率', '起存日', '到期日', '剩餘天數', '銀行分類', '備註']],
    use_container_width=True,
    hide_index=True,
)
