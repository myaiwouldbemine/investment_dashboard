from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from config.settings import PROCESSED_DIR

CJK_BOND = '\u50b5\u5238'
CJK_STOCK = '\u80a1\u7968'
CJK_OVERVIEW = '\u7e3d\u89bd'
CJK_ALL = '\u5168\u90e8'
CJK_FCN = '\u7d50\u69cb\u578b\u5546\u54c1'
STATUS_OUTSTANDING = '\u672a\u5230\u671f'
STATUS_MATURED = '\u5df2\u5230\u671f'


@dataclass(slots=True)
class InvestmentSnapshot:
    bond_df: pd.DataFrame
    bond_cashflow_df: pd.DataFrame
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
    return max(valid) if valid else None


def load_snapshot() -> InvestmentSnapshot:
    """
    Snapshot loading algorithm:
    - Read all required parquet tables once per request cycle.
    - Attach per-domain as_of timestamps from file mtime.
    - Return a single bundle used by summary/detail/chart builders.
    """
    bond_path = 'mart_bond_dashboard_position/latest.parquet'
    bond_cashflow_path = 'mart_bond_dashboard_cashflow/latest.parquet'
    stock_path = 'mart_japan_stock_dashboard/latest.parquet'
    fcn_path = 'stg_fcn_position/latest.parquet'
    fcn_summary_path = 'mart_fcn_summary/latest.parquet'
    return InvestmentSnapshot(
        bond_df=load_frame(bond_path),
        bond_cashflow_df=load_frame(bond_cashflow_path),
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


def format_section(title: str, lines: list[str], as_of: str | None = None) -> dict[str, object]:
    clean_lines = [line for line in lines if isinstance(line, str) and line.strip()]
    return {
        'title': title,
        'lines': clean_lines,
        'as_of': as_of,
        'text': '\n'.join([title, ''] + [f'- {line}' for line in clean_lines]),
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

    searchable_columns = [column for column in candidate_columns if column in frame.columns]
    if not searchable_columns:
        return frame.iloc[0:0]

    def matches(row: pd.Series) -> bool:
        haystack = ' '.join(normalize_text(row[column]) for column in searchable_columns)
        return bool(haystack) and normalized_keyword in haystack

    return frame.loc[frame.apply(matches, axis=1)].copy()


def first_present_value(row: pd.Series, columns: tuple[str, ...]) -> str:
    for column in columns:
        if column in row.index and pd.notna(row[column]) and str(row[column]).strip():
            return str(row[column]).strip()
    return 'N/A'


def build_bond_summary(snapshot: InvestmentSnapshot | None = None) -> dict[str, object]:
    snapshot = snapshot or load_snapshot()
    bond_df = snapshot.bond_df
    if bond_df.empty:
        return format_section('[Bond Summary]', ['No data loaded'], as_of=snapshot.bond_as_of)
    total_face = bond_df['face_amount'].sum()
    avg_ytm = bond_df['ytm'].mean()
    avg_duration = bond_df['duration_years'].mean()
    return format_section('[Bond Summary]', [
        f'Investment amount: {fmt_amount(total_face)}',
        f'Average yield: {fmt_pct(avg_ytm)}',
        f'Average duration: {avg_duration:,.2f} years' if pd.notna(avg_duration) else 'Average duration: N/A',
    ], as_of=snapshot.bond_as_of)


def build_bond_detail_summary(keyword: str, snapshot: InvestmentSnapshot | None = None) -> dict[str, object]:
    snapshot = snapshot or load_snapshot()
    bond_df = snapshot.bond_df
    if bond_df.empty:
        return format_section('[Bond Detail]', ['No data loaded'], as_of=snapshot.bond_as_of)

    matched = filter_frame_by_keyword(
        bond_df,
        keyword,
        ('counterparty', 'issuer_name', 'security_name', 'security_name_zh', 'security_name_en'),
    )
    if matched.empty:
        return format_section('[Bond Detail]', [f'No match for: {keyword}'], as_of=snapshot.bond_as_of)

    total_face = matched['face_amount'].sum() if 'face_amount' in matched.columns else None
    avg_ytm = matched['ytm'].mean() if 'ytm' in matched.columns else None
    avg_duration = matched['duration_years'].mean() if 'duration_years' in matched.columns else None
    top_row = matched.sort_values('face_amount', ascending=False).iloc[0] if 'face_amount' in matched.columns else matched.iloc[0]
    lines = [
        f'Keyword: {keyword}',
        f'Matched rows: {fmt_count(len(matched))}',
        f'Investment amount: {fmt_amount(total_face)}',
        f'Average yield: {fmt_pct(avg_ytm)}',
        f'Average duration: {avg_duration:,.2f} years' if avg_duration is not None and pd.notna(avg_duration) else 'Average duration: N/A',
        f'Top counterparty: {first_present_value(top_row, ("counterparty", "issuer_name"))}',
        f'Top currency: {first_present_value(top_row, ("currency",))}',
    ]
    return format_section('[Bond Detail]', lines, as_of=snapshot.bond_as_of)


def build_stock_summary(snapshot: InvestmentSnapshot | None = None) -> dict[str, object]:
    snapshot = snapshot or load_snapshot()
    stock_df = snapshot.stock_df
    if stock_df.empty:
        return format_section('[Stock Summary]', ['No data loaded'], as_of=snapshot.stock_as_of)
    total_cost = stock_df['total_cost_jpy'].sum()
    market_value = stock_df['market_value_jpy'].sum()
    pnl = stock_df['unrealized_pnl_jpy'].sum()
    total_return = pnl / total_cost if total_cost else None
    return format_section('[Stock Summary]', [
        f'Investment amount: {fmt_amount(total_cost)} JPY',
        f'Market value: {fmt_amount(market_value)} JPY',
        f'Unrealized PnL: {fmt_amount(pnl)} JPY',
        f'Total return: {fmt_pct(total_return)}',
    ], as_of=snapshot.stock_as_of)


def build_stock_detail_summary(keyword: str, snapshot: InvestmentSnapshot | None = None) -> dict[str, object]:
    snapshot = snapshot or load_snapshot()
    stock_df = snapshot.stock_df
    if stock_df.empty:
        return format_section('[Stock Detail]', ['No data loaded'], as_of=snapshot.stock_as_of)

    matched = filter_frame_by_keyword(
        stock_df,
        keyword,
        ('security_name_zh', 'security_name_en', 'security_name', 'ticker', 'symbol'),
    )
    if matched.empty:
        return format_section('[Stock Detail]', [f'No match for: {keyword}'], as_of=snapshot.stock_as_of)

    total_cost = matched['total_cost_jpy'].sum() if 'total_cost_jpy' in matched.columns else None
    market_value = matched['market_value_jpy'].sum() if 'market_value_jpy' in matched.columns else None
    pnl = matched['unrealized_pnl_jpy'].sum() if 'unrealized_pnl_jpy' in matched.columns else None
    total_return = (pnl / total_cost) if total_cost else None
    top_row = matched.sort_values('market_value_jpy', ascending=False).iloc[0] if 'market_value_jpy' in matched.columns else matched.iloc[0]
    stock_name = first_present_value(top_row, ('security_name_zh', 'security_name_en', 'security_name', 'ticker', 'symbol'))
    lines = [
        f'Keyword: {keyword}',
        f'Ticker/name: {stock_name}',
        f'Matched rows: {fmt_count(len(matched))}',
        f'Total cost: {fmt_amount(total_cost)} JPY',
        f'Market value: {fmt_amount(market_value)} JPY',
        f'Unrealized PnL: {fmt_amount(pnl)} JPY',
        f'Return: {fmt_pct(total_return)}',
    ]
    return format_section('[Stock Detail]', lines, as_of=snapshot.stock_as_of)


def build_fcn_summary(snapshot: InvestmentSnapshot | None = None) -> dict[str, object]:
    snapshot = snapshot or load_snapshot()
    fcn_df = snapshot.fcn_df
    fcn_summary_df = snapshot.fcn_summary_df
    if fcn_df.empty or fcn_summary_df.empty:
        return format_section('[FCN Summary]', ['No data loaded'], as_of=snapshot.fcn_as_of)
    row = fcn_summary_df.iloc[0]
    outstanding_df = fcn_df.loc[fcn_df['status_group'] == STATUS_OUTSTANDING].copy() if 'status_group' in fcn_df.columns else pd.DataFrame()
    outstanding_coupon = outstanding_df['coupon_income_jpy'].sum() if 'coupon_income_jpy' in outstanding_df.columns else None
    return format_section('[FCN Summary]', [
        f'Total investment: {fmt_amount(row.get("total_investment_jpy"))} JPY',
        f'Total coupon: {fmt_amount(row.get("total_coupon_jpy"))} JPY',
        f'Outstanding amount: {fmt_amount(row.get("outstanding_jpy"))} JPY',
        f'Outstanding coupon: {fmt_amount(outstanding_coupon)} JPY',
    ], as_of=snapshot.fcn_as_of)


def build_fcn_detail_summary(keyword: str, snapshot: InvestmentSnapshot | None = None) -> dict[str, object]:
    snapshot = snapshot or load_snapshot()
    fcn_df = snapshot.fcn_df
    if fcn_df.empty:
        return format_section('[FCN Detail]', ['No data loaded'], as_of=snapshot.fcn_as_of)

    outstanding_df = fcn_df.loc[fcn_df['status_group'] == STATUS_OUTSTANDING].copy() if 'status_group' in fcn_df.columns else fcn_df.copy()
    matched = filter_frame_by_keyword(outstanding_df, keyword, ('company_code', 'underlying', 'isin', 'issuer'))
    if matched.empty:
        return format_section('[FCN Detail]', [f'No match for: {keyword}'], as_of=snapshot.fcn_as_of)

    total_investment = matched['investment_amount_jpy'].sum() if 'investment_amount_jpy' in matched.columns else None
    total_coupon = matched['coupon_income_jpy'].sum() if 'coupon_income_jpy' in matched.columns else None
    avg_coupon = matched['coupon_rate'].mean() if 'coupon_rate' in matched.columns else None
    nearest = matched.sort_values('maturity_date', ascending=True).iloc[0] if 'maturity_date' in matched.columns else matched.iloc[0]
    lines = [
        f'Keyword: {keyword}',
        f'Matched rows: {fmt_count(len(matched))}',
        f'Outstanding investment: {fmt_amount(total_investment)} JPY',
        f'Outstanding coupon: {fmt_amount(total_coupon)} JPY',
        f'Average coupon: {fmt_pct(avg_coupon)}',
        f'Nearest maturity: {first_present_value(nearest, ("maturity_date",))}',
        f'Underlying: {first_present_value(nearest, ("underlying",))}',
    ]
    return format_section('[FCN Detail]', lines, as_of=snapshot.fcn_as_of)


def build_overview_summary(snapshot: InvestmentSnapshot | None = None) -> dict[str, object]:
    snapshot = snapshot or load_snapshot()
    sections = [build_bond_summary(snapshot), build_stock_summary(snapshot), build_fcn_summary(snapshot)]
    overview_as_of = latest_as_of(*(section.get('as_of') for section in sections))
    text_lines = ['[Investment Overview]', '']
    for index, section in enumerate(sections):
        text_lines.append(section['title'])
        text_lines.append('')
        text_lines.extend([f'- {line}' for line in section['lines']])
        if index < len(sections) - 1:
            text_lines.append('')
    text_lines.extend(['', 'Try: /invest bonds | /invest stocks | /invest fcn'])
    return {'title': '[Investment Overview]', 'sections': sections, 'as_of': overview_as_of, 'text': '\n'.join(text_lines)}


def query_summary(query: str) -> dict[str, object]:
    """
    Query routing algorithm:
    1) normalize query text,
    2) resolve overview vs domain aliases (EN + CJK),
    3) detect detail query "<alias> <keyword>",
    4) dispatch to matching summary/detail builder.
    """
    stripped = query.strip()
    normalized = stripped.casefold()
    snapshot = load_snapshot()

    overview_terms = {'', 'overview', 'summary', 'all', CJK_OVERVIEW, CJK_ALL, '\u6295\u8cc7\u7e3d\u89bd'}
    bond_terms = ('bonds', 'bond', CJK_BOND, 'fixed income')
    stock_terms = ('stocks', 'stock', CJK_STOCK, 'equities', 'equity')
    fcn_terms = ('fcn', 'fcns', CJK_FCN, '\u7d50\u69cb\u5546\u54c1')

    if normalized in {t.casefold() for t in overview_terms}:
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
        'title': 'Supported queries:',
        'lines': [
            '/invest overview',
            '/invest bonds',
            '/invest stocks',
            '/invest fcn',
            '/stock <name>',
            '/bond <name>',
            '/fcn <keyword>',
        ],
        'as_of': None,
        'text': '\n'.join([
            'Supported queries:',
            '',
            '- /invest overview',
            '- /invest bonds',
            '- /invest stocks',
            '- /invest fcn',
            '- /stock <name>',
            '- /bond <name>',
            '- /fcn <keyword>',
        ]),
    }


def _to_native(value: Any) -> Any:
    """Recursively convert numpy/pandas scalars to JSON-native Python types."""
    if isinstance(value, dict):
        return {k: _to_native(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_native(v) for v in value]
    if hasattr(value, 'item'):
        try:
            return value.item()
        except Exception:
            return value
    return value


def _safe_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    clean = frame.where(pd.notna(frame), None)
    return _to_native(clean.to_dict(orient='records'))


def _with_weight(frame: pd.DataFrame, value_col: str, weight_col: str = 'weight') -> pd.DataFrame:
    """Normalize value_col into a ratio column for ranking/percentage charts."""
    if frame.empty or value_col not in frame.columns:
        return frame
    total = frame[value_col].sum()
    frame[weight_col] = (frame[value_col] / total) if total else 0.0
    return frame


def build_bond_charts_payload(snapshot: InvestmentSnapshot | None = None) -> dict[str, object]:
    """
    Bond chart aggregation algorithm:
    - Group by analytical dimensions (currency/rating/counterparty/type/year/company).
    - Compute weights on selected dimensions for percentage visuals.
    - Return chart-ready record arrays so UI rendering stays stateless.
    """
    snapshot = snapshot or load_snapshot()
    bond_df = snapshot.bond_df
    if bond_df.empty:
        return {'available': False, 'reason': 'no_data', 'as_of': snapshot.bond_as_of}

    metrics = {
        'investment_amount': fmt_amount(bond_df['face_amount'].sum()) if 'face_amount' in bond_df.columns else 'N/A',
        'avg_ytm': fmt_pct(bond_df['ytm'].mean()) if 'ytm' in bond_df.columns else 'N/A',
        'avg_duration': (f"{bond_df['duration_years'].mean():,.2f} years" if 'duration_years' in bond_df.columns and pd.notna(bond_df['duration_years'].mean()) else 'N/A'),
    }

    currency_df = (
        bond_df.groupby('currency', dropna=False)['face_amount'].sum().reset_index().sort_values('face_amount', ascending=False)
        if {'currency', 'face_amount'}.issubset(bond_df.columns) else pd.DataFrame()
    )
    rating_df = (
        bond_df.groupby('rating_bucket', dropna=False)['face_amount'].sum().reset_index().sort_values('face_amount', ascending=False)
        if {'rating_bucket', 'face_amount'}.issubset(bond_df.columns) else pd.DataFrame()
    )
    counterparty_df = (
        bond_df.groupby('counterparty', dropna=False)['face_amount'].sum().reset_index().sort_values('face_amount', ascending=False)
        if {'counterparty', 'face_amount'}.issubset(bond_df.columns) else pd.DataFrame()
    )
    bond_type_df = (
        bond_df.groupby('bond_type', dropna=False)['face_amount'].sum().reset_index().sort_values('face_amount', ascending=False)
        if {'bond_type', 'face_amount'}.issubset(bond_df.columns) else pd.DataFrame()
    )
    maturity_df = (
        bond_df.groupby('maturity_year', dropna=False)['face_amount'].sum().reset_index().sort_values('maturity_year')
        if {'maturity_year', 'face_amount'}.issubset(bond_df.columns) else pd.DataFrame()
    )
    company_df = (
        bond_df.groupby('company_code', dropna=False)['face_amount'].sum().reset_index().sort_values('face_amount', ascending=False)
        if {'company_code', 'face_amount'}.issubset(bond_df.columns) else pd.DataFrame()
    )

    counterparty_df = _with_weight(counterparty_df, 'face_amount')
    bond_type_df = _with_weight(bond_type_df, 'face_amount')
    company_df = _with_weight(company_df, 'face_amount')

    cashflow_df = snapshot.bond_cashflow_df.copy()
    if not cashflow_df.empty and 'cashflow_type' in cashflow_df.columns:
        cashflow_df['cashflow_type'] = cashflow_df['cashflow_type'].fillna('unknown')

    return _to_native({
        'available': True,
        'as_of': snapshot.bond_as_of,
        'metrics': metrics,
        'charts': {
            'currency': _safe_records(currency_df),
            'rating': _safe_records(rating_df),
            'counterparty': _safe_records(counterparty_df),
            'bond_type': _safe_records(bond_type_df),
            'maturity_year': _safe_records(maturity_df),
            'company': _safe_records(company_df),
            'cashflow': _safe_records(cashflow_df),
        },
    })


def build_stock_charts_payload(snapshot: InvestmentSnapshot | None = None) -> dict[str, object]:
    snapshot = snapshot or load_snapshot()
    stock_df = snapshot.stock_df
    if stock_df.empty:
        return {'available': False, 'reason': 'no_data', 'as_of': snapshot.stock_as_of}

    total_cost = stock_df['total_cost_jpy'].sum() if 'total_cost_jpy' in stock_df.columns else 0
    total_market = stock_df['market_value_jpy'].sum() if 'market_value_jpy' in stock_df.columns else 0
    total_pnl = stock_df['unrealized_pnl_jpy'].sum() if 'unrealized_pnl_jpy' in stock_df.columns else 0
    overall_return = (total_pnl / total_cost) if total_cost else None

    company_df = (
        stock_df.groupby('company_code', dropna=False)[['total_cost_jpy', 'unrealized_pnl_jpy']].sum().reset_index()
        if {'company_code', 'total_cost_jpy', 'unrealized_pnl_jpy'}.issubset(stock_df.columns) else pd.DataFrame()
    )
    if not company_df.empty:
        company_df['pnl_pct'] = company_df['unrealized_pnl_jpy'] / company_df['total_cost_jpy'].replace(0, pd.NA)
        company_df['pnl_pct'] = company_df['pnl_pct'].fillna(0.0)

    stock_pnl_df = (
        stock_df.groupby('security_name_zh', dropna=False)[['unrealized_pnl_jpy', 'total_cost_jpy']].sum().reset_index()
        if {'security_name_zh', 'unrealized_pnl_jpy', 'total_cost_jpy'}.issubset(stock_df.columns) else pd.DataFrame()
    )
    if not stock_pnl_df.empty:
        stock_pnl_df['return_pct'] = stock_pnl_df['unrealized_pnl_jpy'] / stock_pnl_df['total_cost_jpy'].replace(0, pd.NA)
        stock_pnl_df['return_pct'] = stock_pnl_df['return_pct'].fillna(0.0)

    market_df = (
        stock_df.groupby('security_name_zh', dropna=False)[['market_value_jpy', 'total_cost_jpy']].sum().reset_index().sort_values('market_value_jpy', ascending=False)
        if {'security_name_zh', 'market_value_jpy', 'total_cost_jpy'}.issubset(stock_df.columns) else pd.DataFrame()
    )
    if not market_df.empty:
        total_market_cost = market_df['total_cost_jpy'].sum()
        market_df['investment_weight'] = market_df['total_cost_jpy'] / total_market_cost if total_market_cost else 0.0

    heatmap_df = (
        stock_df.groupby(['company_code', 'security_name_zh'], dropna=False)['unrealized_pnl_jpy'].sum().reset_index()
        if {'company_code', 'security_name_zh', 'unrealized_pnl_jpy'}.issubset(stock_df.columns) else pd.DataFrame()
    )

    return _to_native({
        'available': True,
        'as_of': snapshot.stock_as_of,
        'metrics': {
            'total_cost': total_cost,
            'total_market': total_market,
            'total_pnl': total_pnl,
            'overall_return': overall_return,
        },
        'charts': {
            'company': _safe_records(company_df),
            'stock_pnl': _safe_records(stock_pnl_df),
            'market_value': _safe_records(market_df),
            'heatmap': _safe_records(heatmap_df),
        },
    })


def _build_fcn_analysis1_detail(frame: pd.DataFrame) -> pd.DataFrame:
    """
    FCN coupon pivot algorithm:
    - Bucket rows by trade-year x status,
    - pivot to wide table,
    - fill missing buckets with 0,
    - compute Total for sorting/reporting.
    """
    if frame.empty:
        return pd.DataFrame()
    df = frame.copy()
    if 'trade_date' in df.columns:
        df['trade_date'] = pd.to_datetime(df['trade_date'], errors='coerce')
        df['trade_year'] = df['trade_date'].dt.year
    else:
        df['trade_year'] = None
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


def _build_fcn_analysis2_detail(frame: pd.DataFrame) -> pd.DataFrame:
    """FCN investment pivot by status_group with deterministic missing-column fill."""
    if frame.empty:
        return pd.DataFrame()
    piv = frame.pivot_table(index=['company_code', 'underlying'], columns='status_group', values='investment_amount_jpy', aggfunc='sum', fill_value=0).reset_index()
    if STATUS_MATURED not in piv.columns:
        piv[STATUS_MATURED] = 0
    if STATUS_OUTSTANDING not in piv.columns:
        piv[STATUS_OUTSTANDING] = 0
    piv['Total'] = piv[STATUS_MATURED] + piv[STATUS_OUTSTANDING]
    return piv[['company_code', 'underlying', STATUS_MATURED, STATUS_OUTSTANDING, 'Total']].sort_values(['company_code', 'Total'], ascending=[True, False])


def build_fcn_charts_payload(snapshot: InvestmentSnapshot | None = None) -> dict[str, object]:
    snapshot = snapshot or load_snapshot()
    fcn_df = snapshot.fcn_df
    if fcn_df.empty:
        return {'available': False, 'reason': 'no_data', 'as_of': snapshot.fcn_as_of}

    due_180 = (
        fcn_df.loc[fcn_df['days_to_maturity'].between(0, 180, inclusive='both'), 'investment_amount_jpy'].sum()
        if {'days_to_maturity', 'investment_amount_jpy'}.issubset(fcn_df.columns) else 0
    )
    outstanding = (
        fcn_df.loc[fcn_df['status_group'] == STATUS_OUTSTANDING, 'investment_amount_jpy'].sum()
        if {'status_group', 'investment_amount_jpy'}.issubset(fcn_df.columns) else 0
    )

    company_status = (
        fcn_df.groupby(['company_code', 'status_group'], dropna=False)[['investment_amount_jpy']].sum().reset_index()
        if {'company_code', 'status_group', 'investment_amount_jpy'}.issubset(fcn_df.columns) else pd.DataFrame()
    )
    company_total = (
        fcn_df.groupby('company_code', dropna=False)[['investment_amount_jpy']].sum().reset_index()
        if {'company_code', 'investment_amount_jpy'}.issubset(fcn_df.columns) else pd.DataFrame()
    )

    analysis1 = _build_fcn_analysis1_detail(fcn_df)
    analysis2 = _build_fcn_analysis2_detail(fcn_df)

    return _to_native({
        'available': True,
        'as_of': snapshot.fcn_as_of,
        'metrics': {
            'sum_invest': fcn_df['investment_amount_jpy'].sum() if 'investment_amount_jpy' in fcn_df.columns else 0,
            'sum_coupon': fcn_df['coupon_income_jpy'].sum() if 'coupon_income_jpy' in fcn_df.columns else 0,
            'outstanding': outstanding,
            'due_180': due_180,
        },
        'charts': {
            'company_status': _safe_records(company_status),
            'company_total': _safe_records(company_total),
        },
        'tables': {
            'analysis1': _safe_records(analysis1),
            'analysis2': _safe_records(analysis2),
        },
    })
