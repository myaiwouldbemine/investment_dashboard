from __future__ import annotations

import pandas as pd


def build_deposit_summary(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    due_30 = frame.loc[frame["days_to_maturity"].between(0, 30, inclusive="both"), "amount_rmb_equiv"].sum()
    due_90 = frame.loc[frame["days_to_maturity"].between(0, 90, inclusive="both"), "amount_rmb_equiv"].sum()
    due_180 = frame.loc[frame["days_to_maturity"].between(0, 180, inclusive="both"), "amount_rmb_equiv"].sum()
    return pd.DataFrame([{
        "total_amount_rmb_equiv": frame["amount_rmb_equiv"].sum(),
        "rmb_amount": frame.loc[frame["currency"] == "RMB", "amount"].sum(),
        "usd_amount": frame.loc[frame["currency"] == "USD", "amount"].sum(),
        "usd_rmb_equiv": frame.loc[frame["currency"] == "USD", "amount_rmb_equiv"].sum(),
        "bank_count": frame["bank_name"].dropna().nunique(),
        "position_count": len(frame),
        "maturity_30d": due_30,
        "maturity_90d": due_90,
        "maturity_180d": due_180,
    }])


def _group_weight(frame: pd.DataFrame, group_col: str) -> pd.DataFrame:
    grouped = frame.groupby(group_col, dropna=False)[["amount_rmb_equiv"]].sum().reset_index()
    total = grouped["amount_rmb_equiv"].sum()
    grouped["weight"] = grouped["amount_rmb_equiv"] / total if total else 0
    return grouped.sort_values("amount_rmb_equiv", ascending=False).reset_index(drop=True)


def build_deposit_by_company(frame: pd.DataFrame) -> pd.DataFrame:
    return _group_weight(frame, "company_group") if not frame.empty else pd.DataFrame()


def build_deposit_by_bank(frame: pd.DataFrame) -> pd.DataFrame:
    return _group_weight(frame, "bank_name") if not frame.empty else pd.DataFrame()


def build_deposit_by_currency(frame: pd.DataFrame) -> pd.DataFrame:
    return _group_weight(frame, "currency") if not frame.empty else pd.DataFrame()


def build_deposit_by_type(frame: pd.DataFrame) -> pd.DataFrame:
    return _group_weight(frame, "deposit_type") if not frame.empty else pd.DataFrame()


def build_deposit_maturity(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    output = frame.loc[frame["maturity_date"].notna()].copy()
    if output.empty:
        return pd.DataFrame()
    output["maturity_month"] = pd.to_datetime(output["maturity_date"], errors="coerce").dt.strftime("%Y-%m")
    grouped = output.groupby("maturity_month", dropna=False)[["amount_rmb_equiv"]].sum().reset_index()
    return grouped.sort_values("maturity_month").reset_index(drop=True)
