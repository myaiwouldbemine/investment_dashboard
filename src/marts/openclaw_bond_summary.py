from __future__ import annotations

import pandas as pd


def build_openclaw_bond_summary(position_df: pd.DataFrame, cashflow_df: pd.DataFrame) -> dict[str, object]:
    summary = {
        "portfolio": {},
        "top_exposures": [],
        "cashflow": {},
    }
    if not position_df.empty:
        summary["portfolio"] = {
            "total_face_amount": float(position_df["face_amount"].sum()),
            "avg_ytm": float(position_df["ytm"].mean()) if not position_df["ytm"].dropna().empty else None,
            "avg_duration_years": float(position_df["duration_years"].mean()) if not position_df["duration_years"].dropna().empty else None,
            "issuer_count": int(position_df["issuer_name"].nunique()),
            "currency_mix": position_df.groupby("currency", dropna=False)["face_amount"].sum().to_dict(),
        }
        top = position_df.groupby("issuer_name", dropna=False)["face_amount"].sum().reset_index().sort_values("face_amount", ascending=False).head(10)
        summary["top_exposures"] = top.to_dict(orient="records")
    if not cashflow_df.empty:
        near = cashflow_df.sort_values(["cashflow_year", "cashflow_month"]).head(12)
        summary["cashflow"] = {
            "next_12_rows": near.to_dict(orient="records"),
            "yearly_total": cashflow_df.groupby("cashflow_year", dropna=False)["total_payback"].sum().to_dict(),
        }
    return summary
