from __future__ import annotations

import pandas as pd


def build_bond_position_mart(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    output = frame.copy()
    total_face = output["face_amount"].sum()
    output["portfolio_weight"] = output["face_amount"] / total_face if total_face else 0
    output["maturity_year"] = pd.to_datetime(output["maturity_date"], errors="coerce").dt.year
    keep_cols = [
        "isin", "company_code", "issuer_name", "counterparty", "currency", "rating_bucket", "bond_type",
        "face_amount", "settlement_amount", "ytm", "duration_years", "maturity_date", "maturity_year", "portfolio_weight",
    ]
    return output[keep_cols]


def build_bond_cashflow_mart(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    output = frame.copy()
    output["cashflow_year"] = pd.to_datetime(output["cashflow_date"], errors="coerce").dt.year
    output["cashflow_month"] = pd.to_datetime(output["cashflow_date"], errors="coerce").dt.month
    return output.groupby(["cashflow_year", "cashflow_month", "cashflow_type"], dropna=False)["total_payback"].sum().reset_index()
