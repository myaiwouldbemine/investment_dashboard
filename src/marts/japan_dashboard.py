from __future__ import annotations

import pandas as pd


def build_japan_stock_mart(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    output = frame.copy()
    total_cost = output["total_cost_jpy"].sum()
    total_market = output["market_value_jpy"].sum()
    output["investment_weight"] = output["total_cost_jpy"] / total_cost if total_cost else 0
    output["market_weight"] = output["market_value_jpy"] / total_market if total_market else 0
    output["cost_gap_pct"] = (output["last_price_jpy"] - output["avg_cost_jpy"]) / output["avg_cost_jpy"]
    output = output.sort_values(["market_value_jpy", "unrealized_pnl_jpy"], ascending=[False, False])
    return output
