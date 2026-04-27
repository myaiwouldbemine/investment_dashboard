from __future__ import annotations

import pandas as pd


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors='coerce')


def standardize_fcn_positions(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output.columns = [str(col).strip().replace('\n', '') for col in output.columns]
    output = output.rename(columns={
        '公司': 'company_code',
        'ISIN': 'isin',
        'Issuer': 'issuer',
        '標的': 'underlying',
        'Tenor': 'tenor_months',
        '票息': 'coupon_rate',
        'Put Strike(%)': 'put_strike_pct',
        'Spot Price': 'spot_price',
        'Strike Price': 'strike_price',
        '交易日': 'trade_date',
        '交割日': 'settlement_date',
        '到期日': 'maturity_date',
        '領息日': 'coupon_date',
        '投資金額(日元)': 'investment_amount_jpy',
        '利息(日元)': 'coupon_income_jpy',
        'Outstanding': 'status',
    }).copy()
    output = output.loc[output['company_code'].notna()].copy()
    for col in ['company_code', 'isin', 'issuer', 'status']:
        output[col] = output[col].astype(str).str.strip().replace({'nan': None, '-': None})
    output['underlying'] = output['underlying'].astype(str).str.strip().replace({'nan': None, '-': 'COMBO'})
    for col in ['tenor_months', 'coupon_rate', 'put_strike_pct', 'spot_price', 'strike_price', 'investment_amount_jpy', 'coupon_income_jpy']:
        output[col] = _num(output[col])
    for col in ['trade_date', 'settlement_date', 'maturity_date', 'coupon_date']:
        output[col] = pd.to_datetime(output[col], errors='coerce')
    output['coupon_rate_pct'] = output['coupon_rate'] * 100
    output['strike_buffer_pct'] = (output['spot_price'] / output['strike_price'] - 1).where(output['strike_price'].notna())
    output['days_to_maturity'] = (output['maturity_date'] - pd.Timestamp.today().normalize()).dt.days
    _today = pd.Timestamp.today().normalize()
    output['status_group'] = output['maturity_date'].apply(
        lambda d: '已到期' if pd.notna(d) and d.normalize() < _today
                  else ('未到期' if pd.notna(d) else '未分類')
    )
    keep = [
        'company_code', 'isin', 'issuer', 'underlying', 'tenor_months', 'coupon_rate', 'coupon_rate_pct',
        'put_strike_pct', 'spot_price', 'strike_price', 'strike_buffer_pct', 'trade_date', 'settlement_date',
        'maturity_date', 'coupon_date', 'days_to_maturity', 'investment_amount_jpy', 'coupon_income_jpy',
        'status', 'status_group',
    ]
    return output[keep]


