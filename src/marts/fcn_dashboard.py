from __future__ import annotations

import pandas as pd


def build_fcn_summary(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    total_investment = frame['investment_amount_jpy'].sum()
    total_coupon = frame['coupon_income_jpy'].sum()
    outstanding = frame.loc[frame['status_group'] == '未到期', 'investment_amount_jpy'].sum()
    due_180 = frame.loc[frame['days_to_maturity'].between(0, 180, inclusive='both'), 'investment_amount_jpy'].sum()
    return pd.DataFrame([{
        'total_investment_jpy': total_investment,
        'total_coupon_jpy': total_coupon,
        'outstanding_jpy': outstanding,
        'due_180_jpy': due_180,
        'avg_coupon_rate': frame['coupon_rate'].mean(),
        'avg_strike_buffer_pct': frame['strike_buffer_pct'].mean(),
        'position_count': len(frame),
        'underlying_count': frame['underlying'].nunique(),
    }])


def _group(frame: pd.DataFrame, key: str) -> pd.DataFrame:
    grouped = frame.groupby(key, dropna=False)[['investment_amount_jpy', 'coupon_income_jpy']].sum().reset_index()
    total = grouped['investment_amount_jpy'].sum()
    grouped['weight'] = grouped['investment_amount_jpy'] / total if total else 0
    return grouped.sort_values('investment_amount_jpy', ascending=False)


def build_fcn_by_company(frame: pd.DataFrame) -> pd.DataFrame:
    return _group(frame, 'company_code')


def build_fcn_by_underlying(frame: pd.DataFrame) -> pd.DataFrame:
    return _group(frame, 'underlying')


def build_fcn_by_status(frame: pd.DataFrame) -> pd.DataFrame:
    return _group(frame, 'status_group')


def build_fcn_maturity(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.loc[frame['maturity_date'].notna()].copy()
    if output.empty:
        return pd.DataFrame(columns=['maturity_month', 'investment_amount_jpy'])
    output['maturity_month'] = output['maturity_date'].dt.to_period('M').astype(str)
    return output.groupby('maturity_month', dropna=False)[['investment_amount_jpy']].sum().reset_index().sort_values('maturity_month')


def _interest_pivot(frame: pd.DataFrame, index_col: str) -> pd.DataFrame:
    output = frame.copy()
    output['trade_year'] = output['trade_date'].dt.year
    output['bucket'] = '其他'
    output.loc[output['trade_year'] == 2025, 'bucket'] = '2025年'
    output.loc[(output['trade_year'] == 2026) & (output['status_group'] == '已到期'), 'bucket'] = '2026年_已到期'
    output.loc[(output['trade_year'] == 2026) & (output['status_group'] == '未到期'), 'bucket'] = '2026年_未到期'
    pivot = output.pivot_table(index=index_col, columns='bucket', values='coupon_income_jpy', aggfunc='sum', fill_value=0).reset_index()
    for col in ['2025年', '2026年_已到期', '2026年_未到期']:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot['2026年_合計'] = pivot['2026年_已到期'] + pivot['2026年_未到期']
    pivot['總計'] = pivot['2025年'] + pivot['2026年_合計']
    return pivot[[index_col, '2025年', '2026年_已到期', '2026年_未到期', '2026年_合計', '總計']].sort_values('總計', ascending=False)


def _investment_pivot(frame: pd.DataFrame, index_col: str) -> pd.DataFrame:
    pivot = frame.pivot_table(index=index_col, columns='status_group', values='investment_amount_jpy', aggfunc='sum', fill_value=0).reset_index()
    for col in ['已到期', '未到期']:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot['總計'] = pivot['已到期'] + pivot['未到期']
    return pivot[[index_col, '已到期', '未到期', '總計']].sort_values('總計', ascending=False)


def build_fcn_interest_company(frame: pd.DataFrame) -> pd.DataFrame:
    return _interest_pivot(frame, 'company_code')


def build_fcn_interest_underlying(frame: pd.DataFrame) -> pd.DataFrame:
    return _interest_pivot(frame, 'underlying')


def build_fcn_investment_company(frame: pd.DataFrame) -> pd.DataFrame:
    return _investment_pivot(frame, 'company_code')


def build_fcn_investment_underlying(frame: pd.DataFrame) -> pd.DataFrame:
    return _investment_pivot(frame, 'underlying')
