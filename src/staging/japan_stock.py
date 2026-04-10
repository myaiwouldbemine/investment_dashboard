from __future__ import annotations

import pandas as pd

from config.settings import STOCK_HISTORY_START_DATE
from src.utils.dates import excel_serial_to_date
from src.utils.numbers import coerce_numeric

POSITION_COLUMN_MAP = {
    "股票代碼": "ticker",
    "股票名稱": "security_name_en",
    "股票中文名稱": "security_name_zh",
    "公司名": "company_code",
    "成交股數": "shares",
    "成交金額": "trade_amount_jpy",
    "手續費": "fee_jpy",
    "實際總成本": "total_cost_jpy",
    "平均持股單價": "avg_cost_jpy",
    "股價": "last_price_jpy",
    "市值估算": "market_value_jpy",
    "未實現損益估算": "unrealized_pnl_jpy",
    "Unnamed: 12": "unrealized_return",
    "損益(%)": "unrealized_return",
}

TRADE_COLUMN_MAP = {
    "公司": "company_code",
    "股票代號": "ticker",
    "Stock (Chinese)": "security_name_zh",
    "錄音日期": "trade_date",
    "下單買價(日幣/股)": "order_price_jpy",
    "下單股數": "order_shares",
    "下單金額": "order_amount_jpy",
    "實際成交單價": "fill_price_jpy",
    "實際成交股數": "fill_shares",
    "實際成交金額": "fill_amount_jpy",
    "手續費~0.2%": "fee_jpy",
    "實際總成本": "total_cost_jpy",
    "市值估算": "market_value_jpy",
    "未實現損益估算": "unrealized_pnl_jpy",
    "投資報酬率": "return_pct",
    "平均持股單價": "avg_cost_jpy",
    "股價": "last_price_jpy",
}

POSITION_NUMERIC = [
    "shares", "trade_amount_jpy", "fee_jpy", "total_cost_jpy", "avg_cost_jpy",
    "last_price_jpy", "market_value_jpy", "unrealized_pnl_jpy", "unrealized_return",
]

TRADE_NUMERIC = [
    "order_price_jpy", "order_shares", "order_amount_jpy", "fill_price_jpy", "fill_shares",
    "fill_amount_jpy", "fee_jpy", "total_cost_jpy", "market_value_jpy", "unrealized_pnl_jpy",
    "return_pct", "avg_cost_jpy", "last_price_jpy",
]


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output.columns = [str(col).replace("\n", "").strip() for col in output.columns]
    return output


def standardize_japan_stock_positions(frame: pd.DataFrame) -> pd.DataFrame:
    output = _normalize_columns(frame).rename(columns=POSITION_COLUMN_MAP).copy()
    output = output.loc[output["ticker"].notna()].copy()
    for col in ["ticker", "security_name_en", "security_name_zh", "company_code"]:
        if col in output.columns:
            output[col] = output[col].astype(str).str.strip().replace({"nan": None})
    for col in POSITION_NUMERIC:
        if col in output.columns:
            output[col] = output[col].map(coerce_numeric)
    if "unrealized_return" not in output.columns or output["unrealized_return"].isna().all():
        output["unrealized_return"] = output["unrealized_pnl_jpy"] / output["total_cost_jpy"]
    keep_cols = [
        "ticker", "security_name_en", "security_name_zh", "company_code", "shares",
        "trade_amount_jpy", "fee_jpy", "total_cost_jpy", "avg_cost_jpy", "last_price_jpy",
        "market_value_jpy", "unrealized_pnl_jpy", "unrealized_return",
    ]
    return output[keep_cols]


def standardize_japan_stock_trades(frame: pd.DataFrame) -> pd.DataFrame:
    output = _normalize_columns(frame).rename(columns=TRADE_COLUMN_MAP).copy()
    output = output.loc[output["ticker"].notna()].copy()
    for col in ["ticker", "security_name_zh", "company_code"]:
        if col in output.columns:
            output[col] = output[col].astype(str).str.strip().replace({"nan": None})
    if "trade_date" in output.columns:
        output["trade_date"] = output["trade_date"].map(excel_serial_to_date)
    for col in TRADE_NUMERIC:
        if col in output.columns:
            output[col] = output[col].map(coerce_numeric)
    keep_cols = [
        "company_code", "ticker", "security_name_zh", "trade_date", "order_price_jpy",
        "order_shares", "order_amount_jpy", "fill_price_jpy", "fill_shares", "fill_amount_jpy",
        "fee_jpy", "total_cost_jpy", "market_value_jpy", "unrealized_pnl_jpy", "return_pct",
        "avg_cost_jpy", "last_price_jpy",
    ]
    return output[keep_cols]


def standardize_japan_price_history(frame: pd.DataFrame) -> pd.DataFrame:
    output = _normalize_columns(frame)
    output = output.loc[output["股票代碼"].notna()].copy()
    output["股票代碼"] = output["股票代碼"].astype(str).str.strip()
    output["股票名稱"] = output["股票名稱"].astype(str).str.strip()
    output["股票中文名稱"] = output["股票中文名稱"].astype(str).str.strip()
    id_cols = ["股票代碼", "股票名稱", "股票中文名稱"]
    cutoff = pd.Timestamp(STOCK_HISTORY_START_DATE)
    date_cols = [
        col for col in output.columns
        if col not in id_cols and pd.notna(pd.to_datetime(col, errors="coerce")) and pd.Timestamp(col) >= cutoff
    ]
    melted = output.melt(id_vars=id_cols, value_vars=date_cols, var_name="price_date", value_name="close_price_jpy")
    melted = melted.rename(columns={
        "股票代碼": "ticker",
        "股票名稱": "security_name_en",
        "股票中文名稱": "security_name_zh",
    })
    melted["price_date"] = pd.to_datetime(melted["price_date"], errors="coerce")
    melted["close_price_jpy"] = melted["close_price_jpy"].map(coerce_numeric)
    melted = melted.loc[melted["price_date"].notna() & melted["close_price_jpy"].notna()].copy()
    return melted[["ticker", "security_name_en", "security_name_zh", "price_date", "close_price_jpy"]]
