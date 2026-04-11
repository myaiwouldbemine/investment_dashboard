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
    return _get_secret('INVESTMENT_API_BASE_URL').rstrip('/')


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
    """
    Availability detection algorithm for summary sections.

    We treat a section as 'no data' when:
    1) payload missing,
    2) lines empty, or
    3) lines include known sentinel text (Chinese/English).
    """
    if not section:
        return False
    lines = section.get('lines') or []
    if not isinstance(lines, list) or not lines:
        return False
    joined = ' '.join(str(line) for line in lines)
    return ('\u5c1a\u672a\u8f09\u5165\u8cc7\u6599' not in joined) and ('No data loaded' not in joined)

def line_value(lines: list[str], prefixes: tuple[str, ...]) -> str | None:
    """Extract a metric value from mixed-language summary lines via prefix matching."""
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

    st.title('Investment Management Dashboard')
    st.caption('Unified view of Bonds, Stocks, and FCN. Use the left sidebar to switch pages.')

    # Data source selection algorithm:
    # 1) Try API summary endpoints first (cloud-safe mode).
    # 2) If one section has no data, fallback to local parquet for that section only.
    # This avoids all-or-nothing failure and keeps partial results visible.
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

    bond_summary = 'No bond data available right now. Please try again later.'
    if section_has_data(bond_api):
        bond_summary = '\n'.join(str(line) for line in (bond_api.get('lines') or [])[:2])
    elif not bond_df.empty:
        bond_summary = f"Total investment {fmt_amount(bond_df['face_amount'].sum())}\nAverage yield {fmt_pct(bond_df['ytm'].mean())}"

    stock_summary = 'No stock data available right now. Please try again later.'
    if section_has_data(stock_api):
        stock_summary = '\n'.join(str(line) for line in (stock_api.get('lines') or [])[:2])
    elif not stock_df.empty:
        total_cost = stock_df['total_cost_jpy'].sum()
        total_return = stock_df['unrealized_pnl_jpy'].sum() / total_cost if total_cost else None
        stock_summary = f"Investment amount {fmt_amount(total_cost)}\nTotal return {fmt_pct(total_return)}"

    fcn_summary_text = 'No FCN data available right now. Please try again later.'
    outstanding_coupon = None
    if section_has_data(fcn_api):
        fcn_summary_text = '\n'.join(str(line) for line in (fcn_api.get('lines') or [])[:3])
    elif not fcn_summary_df.empty:
        row = fcn_summary_df.iloc[0]
        outstanding_df = load_frame('stg_fcn_position/latest.parquet')
        if not outstanding_df.empty:
            outstanding_coupon = outstanding_df.loc[outstanding_df['status_group'] == '未到期', 'coupon_income_jpy'].sum()
        fcn_summary_text = f"Total investment {fmt_amount(row['total_investment_jpy'])}\nTotal coupon {fmt_amount(row['total_coupon_jpy'])}\nOutstanding amount {fmt_amount(row['outstanding_jpy'])}\nOutstanding coupon {fmt_amount(outstanding_coupon)}"

    st.subheader('Quick Access')
    q1, q2, q3 = st.columns(3)
    with q1:
        st.markdown(entry_card('Bonds', 'Fixed Income', 'Review bond positions, counterparties, types, and maturity-year analysis.', '#355c7d', bond_summary), unsafe_allow_html=True)
        safe_page_link('pages/3_Bond_Portfolio.py', 'Open Bond Analysis', 'Use the left sidebar and open "3_Bond_Portfolio".')
    with q2:
        st.markdown(entry_card('Stocks', 'Equity', 'Review Japan stock holdings, position PnL, returns, and market value.', '#4f6d4a', stock_summary), unsafe_allow_html=True)
        safe_page_link('pages/4_Stock_Portfolio.py', 'Open Stock Analysis', 'Use the left sidebar and open "4_Stock_Portfolio".')
    with q3:
        st.markdown(entry_card('FCN', 'Structured Product', 'Review FCN investment amount, coupon analysis, allocation, and outstanding details.', '#8a5a44', fcn_summary_text), unsafe_allow_html=True)
        safe_page_link('pages/6_FCN_Portfolio.py', 'Open FCN Analysis', 'Use the left sidebar and open "6_FCN_Portfolio".')

    st.subheader('Summary Overview')

    if section_has_data(bond_api):
        bond_lines = bond_api.get('lines') or []
        bond_cards = [
            metric_card('Total Investment', line_value(bond_lines, ('\u6295\u8cc7\u91d1\u984d\uff1a', '\u6295\u8cc7\u91d1\u984d:', 'Investment amount:', 'Investment amount?')) or 'N/A', 'neutral'),
            metric_card('Average Yield', line_value(bond_lines, ('\u5e73\u5747\u6536\u76ca\u7387\uff1a', '\u5e73\u5747\u6536\u76ca\u7387:', 'Average yield:', 'Average yield?')) or 'N/A', 'safe'),
        ]
        st.markdown(module_block('Bond Summary', bond_cards), unsafe_allow_html=True)
    elif not bond_df.empty:
        bond_cards = [
            metric_card('Total Investment', fmt_amount(bond_df['face_amount'].sum()), 'neutral'),
            metric_card('Average Yield', fmt_pct(bond_df['ytm'].mean()), 'safe'),
        ]
        st.markdown(module_block('Bond Summary', bond_cards), unsafe_allow_html=True)
    else:
        st.info('No bond data is available yet. Try again later or confirm the API has synced the latest data.')

    if section_has_data(stock_api):
        stock_lines = stock_api.get('lines') or []
        stock_cards = [
            metric_card('Investment Amount', line_value(stock_lines, ('\u6295\u8cc7\u91d1\u984d\uff1a', '\u6295\u8cc7\u91d1\u984d:', 'Investment amount:', 'Investment amount?')) or 'N/A', 'neutral'),
            metric_card('Total Return', line_value(stock_lines, ('\u6574\u9ad4\u5831\u916c\u7387\uff1a', '\u6574\u9ad4\u5831\u916c\u7387:', 'Total return:', 'Total return?')) or 'N/A', 'warn'),
        ]
        st.markdown(module_block('Stock Summary', stock_cards), unsafe_allow_html=True)
    elif not stock_df.empty:
        total_cost = stock_df['total_cost_jpy'].sum()
        total_return = stock_df['unrealized_pnl_jpy'].sum() / total_cost if total_cost else None
        stock_cards = [
            metric_card('Investment Amount', fmt_amount(total_cost), 'neutral'),
            metric_card('Total Return', fmt_pct(total_return), 'warn'),
        ]
        st.markdown(module_block('Stock Summary', stock_cards), unsafe_allow_html=True)
    else:
        st.info('No stock data is available yet. Try again later or confirm the API has synced the latest data.')

    if section_has_data(fcn_api):
        fcn_lines = fcn_api.get('lines') or []
        fcn_cards = [
            metric_card('Total Investment', line_value(fcn_lines, ('\u7e3d\u6295\u8cc7\u984d\uff1a', '\u7e3d\u6295\u8cc7\u984d:', 'Total investment:', 'Total investment?')) or 'N/A', 'neutral'),
            metric_card('Total Coupon', line_value(fcn_lines, ('\u7e3d\u5229\u606f\uff1a', '\u7e3d\u5229\u606f:', 'Total coupon:', 'Total coupon?')) or 'N/A', 'warn'),
            metric_card('Outstanding Amount', line_value(fcn_lines, ('\u672a\u5230\u671f\u91d1\u984d\uff1a', '\u672a\u5230\u671f\u91d1\u984d:', 'Outstanding amount:', 'Outstanding amount?')) or 'N/A', 'safe'),
            metric_card('Outstanding Coupon', line_value(fcn_lines, ('\u672a\u5230\u671f\u5229\u606f\uff1a', '\u672a\u5230\u671f\u5229\u606f:', 'Outstanding coupon:', 'Outstanding coupon?')) or 'N/A', 'warn'),
        ]
        st.markdown(module_block('FCN Summary', fcn_cards), unsafe_allow_html=True)
    elif not fcn_summary_df.empty:
        row = fcn_summary_df.iloc[0]
        fcn_cards = [
            metric_card('Total Investment', fmt_amount(row['total_investment_jpy']), 'neutral'),
            metric_card('Total Coupon', fmt_amount(row['total_coupon_jpy']), 'warn'),
            metric_card('Outstanding Amount', fmt_amount(row['outstanding_jpy']), 'safe'),
            metric_card('Outstanding Coupon', fmt_amount(outstanding_coupon), 'warn'),
        ]
        st.markdown(module_block('FCN Summary', fcn_cards), unsafe_allow_html=True)
    else:
        st.info('No FCN data is available yet. Try again later or confirm the API has synced the latest data.')

    local_has_data = any([not bond_df.empty, not stock_df.empty, not fcn_summary_df.empty])
    if not api_base_url:
        st.warning('Investment API base URL is not configured (INVESTMENT_API_BASE_URL). Local data mode is active.')
    elif not api_reachable:
        if local_has_data:
            st.warning('Investment API is configured but unreachable. The dashboard is using local fallback data.')
        else:
            st.error('Investment API is configured but unreachable, and no local fallback data is available.')
    elif not api_has_data:
        if local_has_data:
            st.warning('Investment API is reachable but currently returns no data. The dashboard is using local fallback data.')
        else:
            st.info('Investment API is reachable, but no data is currently available. Sync data on the API side, then refresh.')

    st.info(f"Project path: {Path(__file__).resolve().parent}")


if __name__ == '__main__':
    main()
