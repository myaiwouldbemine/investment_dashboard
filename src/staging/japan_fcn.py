from __future__ import annotations
import pandas as pd
from src.utils.dates import excel_serial_to_date
from src.utils.numbers import coerce_numeric

def standardize_japan_fcn(frame: pd.DataFrame, batch_id: str) -> pd.DataFrame:
    output = frame.copy()
    output["batch_id"] = batch_id
    rename_map = {"公司": "company_code", "ISIN": "isin", "Issuer": "issuer", "標的": "underlying_name", "Tenor": "tenor_years", "票息": "coupon_rate", "Spot Price": "spot_price", "Strike Price": "strike_price", "交易日": "trade_date", "交割日": "settlement_date", "到期日": "maturity_date", "領息日": "coupon_date", "投資/日幣": "investment_amount_jpy", "利息預估": "estimated_coupon_jpy"}
    output = output.rename(columns=rename_map)
    for col in ["tenor_years", "coupon_rate", "spot_price", "strike_price", "investment_amount_jpy", "estimated_coupon_jpy"]:
        if col in output.columns:
            output[col] = output[col].map(coerce_numeric)
    for col in ["trade_date", "settlement_date", "maturity_date", "coupon_date"]:
        if col in output.columns:
            output[col] = output[col].map(excel_serial_to_date)
    if {"spot_price", "strike_price"}.issubset(output.columns):
        output["distance_to_strike_pct"] = (output["spot_price"] - output["strike_price"]) / output["strike_price"]
    return output
