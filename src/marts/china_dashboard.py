from __future__ import annotations
import pandas as pd

def build_china_company_mart(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    grouped = frame.groupby(["company_name", "currency"], dropna=False)["amount"].sum().reset_index().pivot(index="company_name", columns="currency", values="amount").fillna(0).reset_index()
    grouped["total_rmb_equiv"] = grouped.drop(columns=["company_name"]).sum(axis=1)
    return grouped

def build_china_bank_mart(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    grouped = frame.groupby(["bank_name", "currency"], dropna=False)["amount"].sum().reset_index()
    return grouped.sort_values("amount", ascending=False)
