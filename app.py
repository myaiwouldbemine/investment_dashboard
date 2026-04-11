from pathlib import Path
import os

import httpx
import pandas as pd
import streamlit as st

from config.settings import APP_NAME, PROCESSED_DIR
from src.utils.dashboard_access import enforce_dashboard_access


def load_frame(relative_path: str) -> pd.DataFrame:
    path = PROCESSED_DIR / relative_path
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def _get_secret(name: str) -> str:
    value = os.getenv(name, '').strip()
    if value:
        return value
    try:
        secret_value = st.secrets.get(name, '')
    except Exception:
        secret_value = ''
    return str(secret_value).strip()


def get_api_base_url() -> str:
    return (
        _get_secret('INVESTMENT_API_BASE_URL')
        or _get_secret('INVESTMENT_DASHBOARD_API_BASE_URL')
    ).rstrip('/')


def fetch_api_section(base_url: str, endpoint: str) -> dict[str, object] | None:
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


def section_has_data(section: dict[str, object] | None) -> bool:
    if not section:
        return False
    lines = section.get('lines') or []
    if not isinstance(lines, list) or not lines:
        return False
    return '尚未載入資料' not in ' '.join(str(line) for line in lines)


def line_value(lines: list[str], prefixes: tuple[str, ...]) -> str | None:
    for line in lines:
        if not isinstance(line, str):
            continue
        normalized = line.replace('：', ':')
        for prefix in prefixes:
            if normalized.startswith(prefix.replace('：', ':')):
                return normalized.split(':', 1)[1].strip()
    return None


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


def metric_card(title: str, value: str, tone: str = 'neutral') -> str:
    tones = {
        'neutral': '#1f2630',
        'warn': '#2f2a1e',
        'safe': '#1e2c27',
    }
    bg = tones.get(tone, tones['neutral'])
    return f"<div class='metric-card' style='background:{bg};'><div class='metric-title'>{title}</div><div class='metric-value'>{value}</div></div>"


def module_block(title: str, cards: list[str]) -> str:
    return f"<div class='module-block'><div class='module-title'>{title}</div><div class='module-grid compact-grid'>{''.join(cards)}</div></div>"


def entry_card(title: str, subtitle: str, desc: str, accent: str, summary: str) -> str:
    return f"""
    <div class='entry-card' style='border-top: 6px solid {accent};'>
        <div class='entry-kicker'>{subtitle}</div>
        <div class='entry-title'>{title}</div>
        <div class='entry-desc'>{desc}</div>
        <div class='entry-summary'>{summary}</div>
    </div>
    """


def safe_page_link(page: str, label: str, fallback: str) -> None:
    """Render page link when available; degrade gracefully when route metadata is missing."""
    try:
        st.page_link(page, label=label)
    except KeyError:
        st.caption(fallback)


def main() -> None:
    st.set_page_config(page_title=APP_NAME, layout='wide')
    enforce_dashboard_access()
    st.markdown("""
    <style>
    .main {background: linear-gradient(180deg, #0f1319 0%, #171d26 100%);} 
    h1, h2, h3 {color: #f3f5f7;} 
    p, div, span {color: inherit;}
    .stCaptionContainer, .stMarkdown p {color: #b8c0ca !important;}
    .stDataFrame {background: rgba(255,255,255,0.06); border-radius: 16px;} 
    .module-block {
        background: #2b313c;
        border: 1px solid #414957;
        border-radius: 20px;
        padding: 18px;
        box-shadow: 0 6px 24px rgba(0,0,0,0.18);
        margin-bottom: 16px;
    }
    .module-title {
        font-size: 20px;
        font-weight: 800;
        color: #f3f5f7;
        margin-bottom: 14px;
    }
    .module-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
    }
    .compact-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .metric-card {
        padding: 16px;
        border-radius: 14px;
        border: 1px solid #4a5362;
        min-height: 96px;
    }
    .metric-title {
        font-size: 12px;
        color: #aeb7c2;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 30px;
        font-weight: 800;
        color: #ffffff;
        line-height: 1.15;
    }
    .entry-card {
        background: #252c36;
        border-left: 1px solid #414957;
        border-right: 1px solid #414957;
        border-bottom: 1px solid #414957;
        border-radius: 22px;
        padding: 22px;
        box-shadow: 0 10px 28px rgba(0,0,0,0.18);
        height: 420px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .entry-kicker {
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #9eabb8;
        margin-bottom: 10px;
    }
    .entry-title {
        font-size: 42px;
        font-weight: 800;
        color: #ffffff;
        line-height: 1.05;
        margin-bottom: 14px;
        min-height: 52px;
        display: flex;
        align-items: flex-start;
    }
    .entry-desc {
        font-size: 15px;
        color: #c6cdd6;
        line-height: 1.7;
        min-height: 96px;
    }
    .entry-summary {
        margin-top: 18px;
        font-size: 16px;
        font-weight: 800;
        color: #8eb6df;
        line-height: 1.7;
        white-space: pre-line;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title('投資管理儀表板')
    st.caption('同站整合 Bonds、Stocks 與 FCN，請由左側分頁切換。')

    api_base_url = get_api_base_url()
    bond_api = fetch_api_section(api_base_url, '/api/v1/investments/bonds')
    stock_api = fetch_api_section(api_base_url, '/api/v1/investments/stocks')
    fcn_api = fetch_api_section(api_base_url, '/api/v1/investments/fcn')
    api_sections = [bond_api, stock_api, fcn_api]
    api_reachable = any(section is not None for section in api_sections)
    api_has_data = any(section_has_data(section) for section in api_sections)

    bond_df = pd.DataFrame()
    stock_df = pd.DataFrame()
    fcn_summary_df = pd.DataFrame()

    if not section_has_data(bond_api):
        bond_df = load_frame('mart_bond_dashboard_position/latest.parquet')
    if not section_has_data(stock_api):
        stock_df = load_frame('mart_japan_stock_dashboard/latest.parquet')
    if not section_has_data(fcn_api):
        fcn_summary_df = load_frame('mart_fcn_summary/latest.parquet')

    bond_summary = '目前無債券資料，請稍後再試。'
    if section_has_data(bond_api):
        bond_summary = '\n'.join(str(line) for line in (bond_api.get('lines') or [])[:2])
    elif not bond_df.empty:
        bond_summary = f"總投資額 {fmt_amount(bond_df['face_amount'].sum())}\n平均收益率 {fmt_pct(bond_df['ytm'].mean())}"

    stock_summary = '目前無股票資料，請稍後再試。'
    if section_has_data(stock_api):
        stock_summary = '\n'.join(str(line) for line in (stock_api.get('lines') or [])[:2])
    elif not stock_df.empty:
        total_cost = stock_df['total_cost_jpy'].sum()
        total_return = stock_df['unrealized_pnl_jpy'].sum() / total_cost if total_cost else None
        stock_summary = f"投資金額 {fmt_amount(total_cost)}\n整體報酬率 {fmt_pct(total_return)}"

    fcn_summary_text = '目前無 FCN 資料，請稍後再試。'
    outstanding_coupon = None
    if section_has_data(fcn_api):
        fcn_summary_text = '\n'.join(str(line) for line in (fcn_api.get('lines') or [])[:3])
    elif not fcn_summary_df.empty:
        row = fcn_summary_df.iloc[0]
        outstanding_df = load_frame('stg_fcn_position/latest.parquet')
        if not outstanding_df.empty:
            outstanding_coupon = outstanding_df.loc[outstanding_df['status_group'] == '未到期', 'coupon_income_jpy'].sum()
        fcn_summary_text = f"總投資額 {fmt_amount(row['total_investment_jpy'])}\n總利息 {fmt_amount(row['total_coupon_jpy'])}\n未到期金額 {fmt_amount(row['outstanding_jpy'])}\n未到期利息 {fmt_amount(outstanding_coupon)}"

    st.subheader('快速入口')
    q1, q2, q3 = st.columns(3)
    with q1:
        st.markdown(entry_card('Bonds', 'Fixed Income', '查看債券部位、交易對象、類型與到期年分析。', '#355c7d', bond_summary), unsafe_allow_html=True)
        safe_page_link('pages/3_Bond_Portfolio.py', '前往債券分析', '請由左側分頁進入「3_Bond_Portfolio」。')
    with q2:
        st.markdown(entry_card('Stocks', 'Equity', '查看日本股票持股、個股損益、報酬率與市值。', '#4f6d4a', stock_summary), unsafe_allow_html=True)
        safe_page_link('pages/4_Stock_Portfolio.py', '前往股票分析', '請由左側分頁進入「4_Stock_Portfolio」。')
    with q3:
        st.markdown(entry_card('FCN', 'Structured Product', '查看 FCN 投資金額、利息分析、占比與未到期明細。', '#8a5a44', fcn_summary_text), unsafe_allow_html=True)
        safe_page_link('pages/6_FCN_Portfolio.py', '前往 FCN 分析', '請由左側分頁進入「6_FCN_Portfolio」。')

    st.subheader('摘要總覽')

    if section_has_data(bond_api):
        bond_lines = bond_api.get('lines') or []
        bond_cards = [
            metric_card('總投資額', line_value(bond_lines, ('投資金額：', '投資金額:')) or 'N/A', 'neutral'),
            metric_card('平均收益率', line_value(bond_lines, ('平均收益率：', '平均收益率:')) or 'N/A', 'safe'),
        ]
        st.markdown(module_block('債券摘要', bond_cards), unsafe_allow_html=True)
    elif not bond_df.empty:
        bond_cards = [
            metric_card('總投資額', fmt_amount(bond_df['face_amount'].sum()), 'neutral'),
            metric_card('平均收益率', fmt_pct(bond_df['ytm'].mean()), 'safe'),
        ]
        st.markdown(module_block('債券摘要', bond_cards), unsafe_allow_html=True)
    else:
        st.info('目前尚無債券資料。可稍後重試，或確認 API 已同步最新數據。')

    if section_has_data(stock_api):
        stock_lines = stock_api.get('lines') or []
        stock_cards = [
            metric_card('投資金額', line_value(stock_lines, ('投資金額：', '投資金額:')) or 'N/A', 'neutral'),
            metric_card('整體報酬率', line_value(stock_lines, ('整體報酬率：', '整體報酬率:')) or 'N/A', 'warn'),
        ]
        st.markdown(module_block('股票摘要', stock_cards), unsafe_allow_html=True)
    elif not stock_df.empty:
        total_cost = stock_df['total_cost_jpy'].sum()
        total_return = stock_df['unrealized_pnl_jpy'].sum() / total_cost if total_cost else None
        stock_cards = [
            metric_card('投資金額', fmt_amount(total_cost), 'neutral'),
            metric_card('整體報酬率', fmt_pct(total_return), 'warn'),
        ]
        st.markdown(module_block('股票摘要', stock_cards), unsafe_allow_html=True)
    else:
        st.info('目前尚無股票資料。可稍後重試，或確認 API 已同步最新數據。')

    if section_has_data(fcn_api):
        fcn_lines = fcn_api.get('lines') or []
        fcn_cards = [
            metric_card('總投資額', line_value(fcn_lines, ('總投資額：', '總投資額:')) or 'N/A', 'neutral'),
            metric_card('總利息', line_value(fcn_lines, ('總利息：', '總利息:')) or 'N/A', 'warn'),
            metric_card('未到期金額', line_value(fcn_lines, ('未到期金額：', '未到期金額:')) or 'N/A', 'safe'),
            metric_card('未到期利息', line_value(fcn_lines, ('未到期利息：', '未到期利息:')) or 'N/A', 'warn'),
        ]
        st.markdown(module_block('FCN 摘要', fcn_cards), unsafe_allow_html=True)
    elif not fcn_summary_df.empty:
        row = fcn_summary_df.iloc[0]
        fcn_cards = [
            metric_card('總投資額', fmt_amount(row['total_investment_jpy']), 'neutral'),
            metric_card('總利息', fmt_amount(row['total_coupon_jpy']), 'warn'),
            metric_card('未到期金額', fmt_amount(row['outstanding_jpy']), 'safe'),
            metric_card('未到期利息', fmt_amount(outstanding_coupon), 'warn'),
        ]
        st.markdown(module_block('FCN 摘要', fcn_cards), unsafe_allow_html=True)
    else:
        st.info('目前尚無 FCN 資料。可稍後重試，或確認 API 已同步最新數據。')

    local_has_data = any([not bond_df.empty, not stock_df.empty, not fcn_summary_df.empty])
    if not api_base_url:
        st.warning('尚未設定投資 API 位址（INVESTMENT_API_BASE_URL），目前使用本機資料模式。')
    elif not api_reachable:
        if local_has_data:
            st.warning('已設定投資 API 位址，但目前無法連線；畫面已改用本機備援資料。')
        else:
            st.error('已設定投資 API 位址，但目前無法連線，且本機也沒有可用資料。')
    elif not api_has_data:
        if local_has_data:
            st.warning('投資 API 可連線但目前回傳無資料；畫面已改用本機備援資料。')
        else:
            st.info('投資 API 可連線，但目前尚無資料。請先在 API 端同步後再重整。')

    st.info(f"專案路徑：{Path(__file__).resolve().parent}")


if __name__ == '__main__':
    main()
