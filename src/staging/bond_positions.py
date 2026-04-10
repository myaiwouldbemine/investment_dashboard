from __future__ import annotations

import pandas as pd

from src.utils.dates import excel_serial_to_date
from src.utils.numbers import coerce_numeric

POSITION_COLUMN_MAP = {
    "ISIN": "isin",
    "公司名": "company_code",
    "債券類別": "bond_type",
    "交易對象": "counterparty",
    "商品名稱": "product_name",
    "發行機構": "issuer_name",
    "產業": "industry",
    "投資幣別": "currency",
    "信評(M/S/F)": "rating_text",
    "信評等級": "rating_bucket",
    "票面利率": "coupon_rate",
    "配息頻率": "coupon_frequency",
    "下單日": "trade_date",
    "存續期間": "duration_years",
    "到期日": "maturity_date",
    "買入價": "purchase_price",
    "殖利率": "ytm",
    "投資面額": "face_amount",
    "應付本金": "principal_amount",
    "前手息": "accrued_interest",
    "交割金額": "settlement_amount",
    "交割日": "settlement_date",
    "付息次數": "coupon_count",
    "應收利息": "receivable_interest",
    "本利合計": "cash_total",
    "殖利率區間": "yield_band",
    "存續期區間": "duration_band",
    "加權投資成本": "weighted_cost",
}

NUMERIC_COLS = [
    "coupon_rate", "coupon_frequency", "duration_years", "purchase_price", "ytm", "face_amount", "principal_amount",
    "accrued_interest", "settlement_amount", "coupon_count", "receivable_interest", "cash_total", "weighted_cost",
]

DATE_COLS = ["trade_date", "maturity_date", "settlement_date"]


def _extract_summary_metrics(frame: pd.DataFrame) -> dict[str, float | None]:
    first_row = list(frame.iloc[0]) if not frame.empty else []
    metrics = {
        "total_investment": None,
        "avg_duration_years": None,
        "avg_yield": None,
        "total_profit": None,
        "total_profit_rate": None,
    }
    key_map = {
        "總投資": "total_investment",
        "平均投資年限": "avg_duration_years",
        "年平均收益率": "avg_yield",
        "總收益": "total_profit",
        "總收益率": "total_profit_rate",
    }
    for idx, value in enumerate(first_row):
        if value in key_map and idx + 1 < len(first_row):
            metrics[key_map[value]] = coerce_numeric(first_row[idx + 1])
    return metrics


def standardize_bond_positions(frame: pd.DataFrame) -> pd.DataFrame:
    summary_metrics = _extract_summary_metrics(frame)
    output = frame.rename(columns=POSITION_COLUMN_MAP).copy()
    output = output.loc[output["ISIN"].notna()].copy() if "ISIN" in output.columns else output
    output = output.rename(columns=POSITION_COLUMN_MAP)
    if 'currency' in output.columns:
        output['currency'] = output['currency'].astype(str).str.strip().replace({'nan': None})
    if 'rating_bucket' in output.columns:
        output['rating_bucket'] = output['rating_bucket'].astype(str).str.strip().replace({'nan': None})
    if 'counterparty' in output.columns:
        output['counterparty'] = output['counterparty'].astype(str).str.strip().replace({'nan': None})
    if 'bond_type' in output.columns:
        output['bond_type'] = output['bond_type'].astype(str).str.strip().replace({'nan': None})
    for col in NUMERIC_COLS:
        if col in output.columns:
            output[col] = output[col].map(coerce_numeric)
    for col in DATE_COLS:
        if col in output.columns:
            output[col] = output[col].map(excel_serial_to_date)
    for key, value in summary_metrics.items():
        output[key] = value
    keep_cols = [
        "isin", "company_code", "bond_type", "counterparty", "product_name", "issuer_name", "industry",
        "currency", "rating_text", "rating_bucket", "coupon_rate", "coupon_frequency", "trade_date", "duration_years",
        "maturity_date", "purchase_price", "ytm", "face_amount", "principal_amount", "accrued_interest",
        "settlement_amount", "settlement_date", "coupon_count", "receivable_interest", "cash_total", "yield_band",
        "duration_band", "weighted_cost", "total_investment", "avg_duration_years", "avg_yield", "total_profit",
        "total_profit_rate",
    ]
    return output[keep_cols]


def standardize_bond_cashflows(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.rename(columns={
        "ISIN": "isin",
        "公司名": "company_code",
        "債券類別": "bond_type",
        "交易對象": "counterparty",
        "配息日": "cashflow_date",
        "應收利息": "coupon_amount",
        "本利合計": "total_payback",
    }).copy()
    output = output.loc[output["isin"].notna()].copy()
    output["cashflow_date"] = output["cashflow_date"].map(excel_serial_to_date)
    output["coupon_amount"] = output["coupon_amount"].map(coerce_numeric)
    output["total_payback"] = output["total_payback"].map(coerce_numeric)
    output["cashflow_type"] = output["total_payback"].where(output["coupon_amount"] == output["total_payback"], "coupon_principal")
    output["cashflow_type"] = output["cashflow_type"].replace({output["coupon_amount"].iloc[0] if not output.empty else None: "coupon"})
    output.loc[output["coupon_amount"] == output["total_payback"], "cashflow_type"] = "coupon"
    return output[["isin", "company_code", "bond_type", "counterparty", "cashflow_date", "coupon_amount", "total_payback", "cashflow_type"]]
