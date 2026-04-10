from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.settings import (
    FCN_SHEETS,
    FCN_SOURCE_FILE,
    BOND_SHEETS,
    BOND_SOURCE_FILE,
    DEPOSIT_DETAIL_SHEETS,
    DEPOSIT_FX_FALLBACK,
    DEPOSIT_LOOKUP_SHEETS,
    DEPOSIT_SOURCE_FILE,
    INBOX_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    STOCK_SHEETS,
    STOCK_SOURCE_FILE,
)
from src.ingest.excel_loader import frame_to_raw_rows, list_sheets, load_sheet
from src.marts.bond_dashboard import build_bond_cashflow_mart, build_bond_position_mart
from src.marts.deposit_dashboard import (
    build_deposit_by_bank,
    build_deposit_by_company,
    build_deposit_by_currency,
    build_deposit_by_type,
    build_deposit_maturity,
    build_deposit_summary,
)
from src.marts.fcn_dashboard import build_fcn_by_company, build_fcn_by_status, build_fcn_by_underlying, build_fcn_interest_company, build_fcn_interest_underlying, build_fcn_investment_company, build_fcn_investment_underlying, build_fcn_maturity, build_fcn_summary
from src.marts.japan_dashboard import build_japan_stock_mart
from src.staging.bond_positions import standardize_bond_cashflows, standardize_bond_positions
from src.staging.deposit_positions import build_bank_dimension, build_deposit_staging, extract_fx_rate
from src.staging.fcn_positions import standardize_fcn_positions
from src.staging.japan_stock import standardize_japan_price_history, standardize_japan_stock_positions, standardize_japan_stock_trades


def log(message: str) -> None:
    print(message, flush=True)


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    INBOX_DIR.mkdir(parents=True, exist_ok=True)


def save_frame(frame: pd.DataFrame, target: Path, label: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(target, index=False)
    log(f"saved {label}: rows={len(frame)} -> {target}")


def run_bond_pipeline() -> None:
    source_path = Path(BOND_SOURCE_FILE)
    if not source_path.exists():
        log(f"[bond-pipeline] skip missing source: {source_path}")
        return

    for sheet in BOND_SHEETS:
        frame = load_sheet(str(source_path), sheet_name=sheet, header=0)
        raw_rows = frame_to_raw_rows(frame, sheet_name=sheet)
        save_frame(raw_rows, RAW_DIR / "bond" / f"{sheet}.parquet", f"raw {sheet}")

    positions = standardize_bond_positions(load_sheet(str(source_path), "Database_Bonds", header=0))
    cashflows = standardize_bond_cashflows(load_sheet(str(source_path), "Database_Payback", header=0))

    save_frame(positions, PROCESSED_DIR / "stg_bond_position" / "latest.parquet", "stg_bond_position")
    save_frame(cashflows, PROCESSED_DIR / "stg_bond_cashflow" / "latest.parquet", "stg_bond_cashflow")

    position_mart = build_bond_position_mart(positions)
    cashflow_mart = build_bond_cashflow_mart(cashflows)

    save_frame(position_mart, PROCESSED_DIR / "mart_bond_dashboard_position" / "latest.parquet", "mart_bond_dashboard_position")
    save_frame(cashflow_mart, PROCESSED_DIR / "mart_bond_dashboard_cashflow" / "latest.parquet", "mart_bond_dashboard_cashflow")
    log("[bond-pipeline] completed")


def run_stock_pipeline() -> None:
    source_path = Path(STOCK_SOURCE_FILE)
    if not source_path.exists():
        log(f"[stock-pipeline] skip missing source: {source_path}")
        return

    available_sheets = set(list_sheets(str(source_path)))

    for sheet in STOCK_SHEETS:
        if sheet not in available_sheets:
            continue
        frame = load_sheet(str(source_path), sheet_name=sheet, header=0)
        raw_rows = frame_to_raw_rows(frame, sheet_name=sheet)
        save_frame(raw_rows, RAW_DIR / "stock" / f"{sheet}.parquet", f"raw {sheet}")

    positions = standardize_japan_stock_positions(load_sheet(str(source_path), "Database_Stock", header=0))
    stock_mart = build_japan_stock_mart(positions)

    trade_columns = [
        "company_code", "ticker", "security_name_zh", "trade_date", "order_price_jpy",
        "order_shares", "order_amount_jpy", "fill_price_jpy", "fill_shares", "fill_amount_jpy",
        "fee_jpy", "total_cost_jpy", "market_value_jpy", "unrealized_pnl_jpy", "return_pct",
        "avg_cost_jpy", "last_price_jpy",
    ]
    price_columns = ["ticker", "security_name_en", "security_name_zh", "price_date", "close_price_jpy"]
    trades = pd.DataFrame(columns=trade_columns)
    prices = pd.DataFrame(columns=price_columns)

    if "PSA???????????" in available_sheets:
        trades = standardize_japan_stock_trades(load_sheet(str(source_path), "PSA???????????", header=0))
    if "PSA??????" in available_sheets:
        price_raw = pd.read_excel(str(source_path), sheet_name="PSA??????", engine="openpyxl", header=0, nrows=120)
        save_frame(frame_to_raw_rows(price_raw, sheet_name="PSA??????"), RAW_DIR / "stock" / "PSA??????.parquet", "raw PSA??????")
        prices = standardize_japan_price_history(price_raw)

    save_frame(positions, PROCESSED_DIR / "stg_japan_stock_position" / "latest.parquet", "stg_japan_stock_position")
    save_frame(trades, PROCESSED_DIR / "stg_japan_stock_trade" / "latest.parquet", "stg_japan_stock_trade")
    save_frame(prices, PROCESSED_DIR / "stg_japan_price_history" / "latest.parquet", "stg_japan_price_history")
    save_frame(stock_mart, PROCESSED_DIR / "mart_japan_stock_dashboard" / "latest.parquet", "mart_japan_stock_dashboard")
    log("[stock-pipeline] completed")



def run_fcn_pipeline() -> None:
    source_path = Path(FCN_SOURCE_FILE)
    if not source_path.exists():
        log(f'[fcn-pipeline] skip missing source: {source_path}')
        return

    for sheet in FCN_SHEETS:
        frame = load_sheet(str(source_path), sheet_name=sheet, header=0)
        raw_rows = frame_to_raw_rows(frame, sheet_name=sheet)
        save_frame(raw_rows, RAW_DIR / 'fcn' / f'{sheet}.parquet', f'raw {sheet}')

    positions = standardize_fcn_positions(load_sheet(str(source_path), 'Database_FCN List', header=0))
    save_frame(positions, PROCESSED_DIR / 'stg_fcn_position' / 'latest.parquet', 'stg_fcn_position')
    save_frame(build_fcn_summary(positions), PROCESSED_DIR / 'mart_fcn_summary' / 'latest.parquet', 'mart_fcn_summary')
    save_frame(build_fcn_by_company(positions), PROCESSED_DIR / 'mart_fcn_by_company' / 'latest.parquet', 'mart_fcn_by_company')
    save_frame(build_fcn_by_underlying(positions), PROCESSED_DIR / 'mart_fcn_by_underlying' / 'latest.parquet', 'mart_fcn_by_underlying')
    save_frame(build_fcn_by_status(positions), PROCESSED_DIR / 'mart_fcn_by_status' / 'latest.parquet', 'mart_fcn_by_status')
    save_frame(build_fcn_maturity(positions), PROCESSED_DIR / 'mart_fcn_maturity' / 'latest.parquet', 'mart_fcn_maturity')
    save_frame(build_fcn_interest_company(positions), PROCESSED_DIR / 'mart_fcn_interest_company' / 'latest.parquet', 'mart_fcn_interest_company')
    save_frame(build_fcn_interest_underlying(positions), PROCESSED_DIR / 'mart_fcn_interest_underlying' / 'latest.parquet', 'mart_fcn_interest_underlying')
    save_frame(build_fcn_investment_company(positions), PROCESSED_DIR / 'mart_fcn_investment_company' / 'latest.parquet', 'mart_fcn_investment_company')
    save_frame(build_fcn_investment_underlying(positions), PROCESSED_DIR / 'mart_fcn_investment_underlying' / 'latest.parquet', 'mart_fcn_investment_underlying')
    log('[fcn-pipeline] completed')
def run_deposit_pipeline() -> None:
    source_path = Path(DEPOSIT_SOURCE_FILE)
    if not source_path.exists():
        log(f"[deposit-pipeline] skip missing source: {source_path}")
        return

    detail_frames = []
    for sheet in DEPOSIT_DETAIL_SHEETS:
        frame = load_sheet(str(source_path), sheet_name=sheet, header=0)
        raw_rows = frame_to_raw_rows(frame, sheet_name=sheet)
        save_frame(raw_rows, RAW_DIR / "deposit" / f"{sheet}.parquet", f"raw {sheet}")
        detail_frames.append((sheet, frame))

    lookup_frames = {}
    for sheet in DEPOSIT_LOOKUP_SHEETS:
        frame = load_sheet(str(source_path), sheet_name=sheet, header=0)
        lookup_frames[sheet] = frame
        raw_rows = frame_to_raw_rows(frame, sheet_name=sheet)
        save_frame(raw_rows, RAW_DIR / "deposit" / f"{sheet}.parquet", f"raw {sheet}")

    bank_source = lookup_frames.get("????") if lookup_frames.get("????") is not None else lookup_frames.get("????")
    bank_dim = build_bank_dimension(bank_source) if bank_source is not None else pd.DataFrame()
    fx_rate = extract_fx_rate(lookup_frames.get("PSA??08", pd.DataFrame()), DEPOSIT_FX_FALLBACK)
    staging = build_deposit_staging(detail_frames, bank_dim=bank_dim, fx_rate=fx_rate)

    save_frame(staging, PROCESSED_DIR / "stg_deposit_position" / "latest.parquet", "stg_deposit_position")
    save_frame(build_deposit_summary(staging), PROCESSED_DIR / "mart_deposit_summary" / "latest.parquet", "mart_deposit_summary")
    save_frame(build_deposit_by_company(staging), PROCESSED_DIR / "mart_deposit_by_company" / "latest.parquet", "mart_deposit_by_company")
    save_frame(build_deposit_by_bank(staging), PROCESSED_DIR / "mart_deposit_by_bank" / "latest.parquet", "mart_deposit_by_bank")
    save_frame(build_deposit_by_currency(staging), PROCESSED_DIR / "mart_deposit_by_currency" / "latest.parquet", "mart_deposit_by_currency")
    save_frame(build_deposit_by_type(staging), PROCESSED_DIR / "mart_deposit_by_type" / "latest.parquet", "mart_deposit_by_type")
    save_frame(build_deposit_maturity(staging), PROCESSED_DIR / "mart_deposit_maturity" / "latest.parquet", "mart_deposit_maturity")
    if not bank_dim.empty:
        save_frame(bank_dim, PROCESSED_DIR / "dim_bank" / "latest.parquet", "dim_bank")
    log("[deposit-pipeline] completed")


def main() -> None:
    ensure_dirs()
    run_bond_pipeline()
    run_stock_pipeline()
    run_fcn_pipeline()
    run_deposit_pipeline()
    log("pipeline completed")


if __name__ == "__main__":
    main()



