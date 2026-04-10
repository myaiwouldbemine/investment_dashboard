from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from config.settings import PROCESSED_DIR


@dataclass(slots=True)
class InvestmentSnapshot:
    bond_df: pd.DataFrame
    stock_df: pd.DataFrame
    fcn_df: pd.DataFrame
    fcn_summary_df: pd.DataFrame
    bond_as_of: str | None
    stock_as_of: str | None
    fcn_as_of: str | None


def _frame_path(relative_path: str) -> Path:
    return PROCESSED_DIR / relative_path


def load_frame(relative_path: str) -> pd.DataFrame:
    path = _frame_path(relative_path)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def file_as_of(relative_path: str) -> str | None:
    path = _frame_path(relative_path)
    if not path.exists():
        return None
    ts = datetime.fromtimestamp(path.stat().st_mtime)
    return ts.strftime('%Y-%m-%d %H:%M:%S')


def latest_as_of(*values: str | None) -> str | None:
    valid = [value for value in values if value]
    if not valid:
        return None
    return max(valid)


def load_snapshot() -> InvestmentSnapshot:
    bond_path = 'mart_bond_dashboard_position/latest.parquet'
    stock_path = 'mart_japan_stock_dashboard/latest.parquet'
    fcn_path = 'stg_fcn_position/latest.parquet'
    fcn_summary_path = 'mart_fcn_summary/latest.parquet'
    return InvestmentSnapshot(
        bond_df=load_frame(bond_path),
        stock_df=load_frame(stock_path),
        fcn_df=load_frame(fcn_path),
        fcn_summary_df=load_frame(fcn_summary_path),
        bond_as_of=file_as_of(bond_path),
        stock_as_of=file_as_of(stock_path),
        fcn_as_of=latest_as_of(file_as_of(fcn_path), file_as_of(fcn_summary_path)),
    )


def fmt_amount(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return 'N/A'
    return f'{value:,.0f}'


def fmt_pct(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return 'N/A'
    return f'{value:.2%}'


def fmt_count(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return 'N/A'
    return f'{int(value):,d}'


def normalize_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ''
    return str(value).strip().casefold()


def top_label(frame: pd.DataFrame, group_col: str, value_col: str, unit: str = '') -> str:
    if frame.empty or group_col not in frame.columns or value_col not in frame.columns:
        return 'N/A'
    ranked = (
        frame.groupby(group_col, dropna=False)[value_col]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    if ranked.empty:
        return 'N/A'
    row = ranked.iloc[0]
    label = str(row[group_col]) if pd.notna(row[group_col]) else '未分類'
    suffix = f' {unit}' if unit else ''
    return f'{label} ({fmt_amount(row[value_col])}{suffix})'


def best_stock_label(stock_df: pd.DataFrame) -> str:
    if stock_df.empty or 'unrealized_return' not in stock_df.columns:
        return 'N/A'
    ranked = stock_df.sort_values('unrealized_return', ascending=False).reset_index(drop=True)
    if ranked.empty:
        return 'N/A'
    row = ranked.iloc[0]
    return f"{row['security_name_zh']} ({fmt_pct(row['unrealized_return'])})"


def format_section(title: str, lines: list[str], as_of: str | None = None) -> dict[str, object]:
    clean_lines = [line for line in lines if isinstance(line, str) and line.strip()]
    return {
        'title': title,
        'lines': clean_lines,
        'as_of': as_of,
        'text': '\n'.join([title, ''] + [f'－ {line}' for line in clean_lines]),
    }


def extract_detail_term(query: str, aliases: tuple[str, ...]) -> str:
    stripped = query.strip()
    normalized = stripped.casefold()
    for alias in aliases:
        alias_norm = alias.casefold()
        if normalized == alias_norm:
            return ''
        if normalized.startswith(f'{alias_norm} '):
            return stripped[len(alias) :].strip()
    return ''


def filter_frame_by_keyword(frame: pd.DataFrame, keyword: str, candidate_columns: tuple[str, ...]) -> pd.DataFrame:
    if frame.empty:
        return frame
    normalized_keyword = normalize_text(keyword)
    if not normalized_keyword:
        return frame
    tokens = [token for token in normalized_keyword.split() if token]
    if not tokens:
        tokens = [normalized_keyword]

    searchable_columns = [column for column in candidate_columns if column in frame.columns]
    if not searchable_columns:
        return frame.iloc[0:0]

    def matches(row: pd.Series) -> bool:
        haystack = ' '.join(normalize_text(row[column]) for column in searchable_columns)
        if not haystack:
            return False
        return normalized_keyword in haystack or all(token in haystack for token in tokens)

    mask = frame.apply(matches, axis=1)
    return frame.loc[mask].copy()


def first_present_value(row: pd.Series, columns: tuple[str, ...]) -> str:
    for column in columns:
        if column in row.index and pd.notna(row[column]) and str(row[column]).strip():
            return str(row[column]).strip()
    return 'N/A'


def build_bond_summary(snapshot: InvestmentSnapshot | None = None) -> dict[str, object]:
    snapshot = snapshot or load_snapshot()
    bond_df = snapshot.bond_df
    if bond_df.empty:
        return format_section('【債券摘要】', ['尚未載入資料'], as_of=snapshot.bond_as_of)
    total_face = bond_df['face_amount'].sum()
    avg_ytm = bond_df['ytm'].mean()
    avg_duration = bond_df['duration_years'].mean()
    position_count = len(bond_df)
    return format_section('【債券摘要】', [
        f'投資金額：{fmt_amount(total_face)}',
        f'平均收益率：{fmt_pct(avg_ytm)}',
        f'平均存續年數：{avg_duration:,.2f} 年' if pd.notna(avg_duration) else '平均存續年數：N/A',
    ], as_of=snapshot.bond_as_of)


def build_bond_detail_summary(keyword: str, snapshot: InvestmentSnapshot | None = None) -> dict[str, object]:
    snapshot = snapshot or load_snapshot()
    bond_df = snapshot.bond_df
    if bond_df.empty:
        return format_section('【債券明細】', ['尚未載入資料'], as_of=snapshot.bond_as_of)

    matched = filter_frame_by_keyword(
        bond_df,
        keyword,
        ('counterparty', 'issuer_name', 'security_name', 'security_name_zh', 'security_name_en'),
    )
    if matched.empty:
        return format_section('【債券明細】', [f'查無符合「{keyword}」的債券部位'], as_of=snapshot.bond_as_of)

    total_face = matched['face_amount'].sum() if 'face_amount' in matched.columns else None
    avg_ytm = matched['ytm'].mean() if 'ytm' in matched.columns else None
    avg_duration = matched['duration_years'].mean() if 'duration_years' in matched.columns else None
    top_row = matched.sort_values('face_amount', ascending=False).iloc[0] if 'face_amount' in matched.columns else matched.iloc[0]
    lines = [
        f'查詢條件：{keyword}',
        f'命中筆數：{fmt_count(len(matched))}',
        f'投資金額：{fmt_amount(total_face)}',
        f'平均收益率：{fmt_pct(avg_ytm)}',
        f'平均存續年數：{avg_duration:,.2f} 年' if avg_duration is not None and pd.notna(avg_duration) else '平均存續年數：N/A',
        f'主要交易對象：{first_present_value(top_row, ("counterparty", "issuer_name"))}',
        f'主要幣別：{first_present_value(top_row, ("currency",))}',
    ]
    return format_section('【債券明細】', lines, as_of=snapshot.bond_as_of)


def build_stock_summary(snapshot: InvestmentSnapshot | None = None) -> dict[str, object]:
    snapshot = snapshot or load_snapshot()
    stock_df = snapshot.stock_df
    if stock_df.empty:
        return format_section('【股票摘要】', ['尚未載入資料'], as_of=snapshot.stock_as_of)
    total_cost = stock_df['total_cost_jpy'].sum()
    market_value = stock_df['market_value_jpy'].sum()
    pnl = stock_df['unrealized_pnl_jpy'].sum()
    total_return = pnl / total_cost if total_cost else None
    holding_count = len(stock_df)
    return format_section('【股票摘要】', [
        f'投資金額：{fmt_amount(total_cost)} JPY',
        f'市值：{fmt_amount(market_value)} JPY',
        f'未實現損益：{fmt_amount(pnl)} JPY',
        f'整體報酬率：{fmt_pct(total_return)}',
    ], as_of=snapshot.stock_as_of)


def build_stock_detail_summary(keyword: str, snapshot: InvestmentSnapshot | None = None) -> dict[str, object]:
    snapshot = snapshot or load_snapshot()
    stock_df = snapshot.stock_df
    if stock_df.empty:
        return format_section('【股票明細】', ['尚未載入資料'], as_of=snapshot.stock_as_of)

    matched = filter_frame_by_keyword(
        stock_df,
        keyword,
        ('security_name_zh', 'security_name_en', 'security_name', 'ticker', 'symbol'),
    )
    if matched.empty:
        return format_section('【股票明細】', [f'查無符合「{keyword}」的股票部位'], as_of=snapshot.stock_as_of)

    total_cost = matched['total_cost_jpy'].sum() if 'total_cost_jpy' in matched.columns else None
    market_value = matched['market_value_jpy'].sum() if 'market_value_jpy' in matched.columns else None
    pnl = matched['unrealized_pnl_jpy'].sum() if 'unrealized_pnl_jpy' in matched.columns else None
    total_return = (pnl / total_cost) if total_cost else None
    top_row = matched.sort_values('market_value_jpy', ascending=False).iloc[0] if 'market_value_jpy' in matched.columns else matched.iloc[0]
    stock_name = first_present_value(top_row, ('security_name_zh', 'security_name_en', 'security_name', 'ticker', 'symbol'))
    ticker = first_present_value(top_row, ('ticker', 'symbol'))
    lines = [
        f'查詢條件：{keyword}',
        f'標的：{stock_name}',
        f'命中筆數：{fmt_count(len(matched))}',
        f'總投入成本：{fmt_amount(total_cost)} JPY',
        f'總市值估算：{fmt_amount(market_value)} JPY',
        f'未實現損益：{fmt_amount(pnl)} JPY',
        f'報酬率：{fmt_pct(total_return)}',
    ]
    if ticker != 'N/A' and ticker != stock_name:
        lines.insert(2, f'代碼：{ticker}')
    return format_section('【股票明細】', lines, as_of=snapshot.stock_as_of)


def build_fcn_summary(snapshot: InvestmentSnapshot | None = None) -> dict[str, object]:
    snapshot = snapshot or load_snapshot()
    fcn_df = snapshot.fcn_df
    fcn_summary_df = snapshot.fcn_summary_df
    if fcn_df.empty or fcn_summary_df.empty:
        return format_section('【FCN 摘要】', ['尚未載入資料'], as_of=snapshot.fcn_as_of)
    row = fcn_summary_df.iloc[0]
    outstanding_df = fcn_df.loc[fcn_df['status_group'] == '未到期'].copy() if 'status_group' in fcn_df.columns else pd.DataFrame()
    outstanding_coupon = outstanding_df['coupon_income_jpy'].sum() if 'coupon_income_jpy' in outstanding_df.columns else None
    outstanding_count = len(outstanding_df)
    return format_section('【FCN 摘要】', [
        f'總投資額：{fmt_amount(row.get("total_investment_jpy"))} JPY',
        f'總利息：{fmt_amount(row.get("total_coupon_jpy"))} JPY',
        f'未到期金額：{fmt_amount(row.get("outstanding_jpy"))} JPY',
        f'未到期利息：{fmt_amount(outstanding_coupon)} JPY',
    ], as_of=snapshot.fcn_as_of)


def build_fcn_detail_summary(keyword: str, snapshot: InvestmentSnapshot | None = None) -> dict[str, object]:
    snapshot = snapshot or load_snapshot()
    fcn_df = snapshot.fcn_df
    if fcn_df.empty:
        return format_section('【FCN 明細】', ['尚未載入資料'], as_of=snapshot.fcn_as_of)

    outstanding_df = fcn_df.loc[fcn_df['status_group'] == '未到期'].copy() if 'status_group' in fcn_df.columns else fcn_df.copy()
    matched = filter_frame_by_keyword(
        outstanding_df,
        keyword,
        ('company_code', 'underlying', 'isin', 'issuer'),
    )
    if matched.empty:
        return format_section('【FCN 明細】', [f'查無符合「{keyword}」的未到期 FCN 部位'], as_of=snapshot.fcn_as_of)

    total_investment = matched['investment_amount_jpy'].sum() if 'investment_amount_jpy' in matched.columns else None
    total_coupon = matched['coupon_income_jpy'].sum() if 'coupon_income_jpy' in matched.columns else None
    avg_coupon = matched['coupon_rate'].mean() if 'coupon_rate' in matched.columns else None
    nearest = matched.sort_values('maturity_date', ascending=True).iloc[0] if 'maturity_date' in matched.columns else matched.iloc[0]
    lines = [
        f'查詢條件：{keyword}',
        f'命中筆數：{fmt_count(len(matched))}',
        f'未到期投資額：{fmt_amount(total_investment)} JPY',
        f'未到期利息：{fmt_amount(total_coupon)} JPY',
        f'平均票息：{fmt_pct(avg_coupon)}',
        f'最近到期日：{first_present_value(nearest, ("maturity_date",))}',
        f'主要標的：{first_present_value(nearest, ("underlying",))}',
    ]
    return format_section('【FCN 明細】', lines, as_of=snapshot.fcn_as_of)


def build_overview_summary(snapshot: InvestmentSnapshot | None = None) -> dict[str, object]:
    snapshot = snapshot or load_snapshot()
    sections = [build_bond_summary(snapshot), build_stock_summary(snapshot), build_fcn_summary(snapshot)]
    overview_as_of = latest_as_of(*(section.get('as_of') for section in sections))
    text_lines = ['【投資總覽】', '']
    for index, section in enumerate(sections):
        text_lines.append(section['title'])
        text_lines.append('')
        text_lines.extend([f'－ {line}' for line in section['lines']])
        if index < len(sections) - 1:
            text_lines.append('')
    text_lines.extend(['', '可直接輸入：/invest bonds、/invest stocks、/invest fcn'])
    return {'title': '【投資總覽】', 'sections': sections, 'as_of': overview_as_of, 'text': '\n'.join(text_lines)}


def query_summary(query: str) -> dict[str, object]:
    stripped = query.strip()
    normalized = stripped.casefold()
    snapshot = load_snapshot()

    overview_terms = {'', 'overview', 'summary', 'all', '總覽', '全部', '投資總覽'}
    bond_terms = ('bonds', 'bond', '債券', 'fixed income')
    stock_terms = ('stocks', 'stock', '股票', 'equities', 'equity')
    fcn_terms = ('fcn', 'fcns', '結構型商品', '結構商品')

    if normalized in overview_terms:
        return build_overview_summary(snapshot)

    bond_detail = extract_detail_term(stripped, bond_terms)
    if bond_detail:
        return build_bond_detail_summary(bond_detail, snapshot)
    if normalized in {term.casefold() for term in bond_terms}:
        return build_bond_summary(snapshot)

    stock_detail = extract_detail_term(stripped, stock_terms)
    if stock_detail:
        return build_stock_detail_summary(stock_detail, snapshot)
    if normalized in {term.casefold() for term in stock_terms}:
        return build_stock_summary(snapshot)

    fcn_detail = extract_detail_term(stripped, fcn_terms)
    if fcn_detail:
        return build_fcn_detail_summary(fcn_detail, snapshot)
    if normalized in {term.casefold() for term in fcn_terms}:
        return build_fcn_summary(snapshot)

    return {
        'title': '目前支援的投資查詢：',
        'lines': [
            '/invest overview',
            '/invest bonds',
            '/invest stocks',
            '/invest fcn',
            '/股票 日本菸草',
            '/債券 Morgan Stanley',
            '/fcn COMBO',
        ],
        'as_of': None,
        'text': '\n'.join([
            '目前支援的投資查詢：',
            '',
            '－ /invest overview',
            '－ /invest bonds',
            '－ /invest stocks',
            '－ /invest fcn',
            '－ /股票 日本菸草',
            '－ /債券 Morgan Stanley',
            '－ /fcn COMBO',
        ]),
    }
