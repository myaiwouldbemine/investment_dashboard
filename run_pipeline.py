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
from src.quality import run_post_checks, run_pre_checks
from src.marts.fcn_dashboard import build_fcn_by_company, build_fcn_by_status, build_fcn_by_underlying, build_fcn_interest_company, build_fcn_interest_underlying, build_fcn_investment_company, build_fcn_investment_underlying, build_fcn_maturity, build_fcn_summary
from src.marts.japan_dashboard import build_japan_stock_mart
from src.staging.bond_positions import standardize_bond_cashflows, standardize_bond_positions
from src.staging.deposit_positions import _prepare_detail_sheet, build_bank_dimension, build_deposit_staging, extract_fx_rate
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


def validate_pre(frame: pd.DataFrame, *, domain: str, dataset: str, required_columns: list[str], date_columns: list[str], amount_columns: list[str]) -> None:
    run_pre_checks(
        frame,
        domain=domain,
        dataset=dataset,
        required_columns=required_columns,
        date_columns=date_columns,
        amount_columns=amount_columns,
    )
    log(f"[{domain}] pre-check passed: {dataset}")


def validate_post(frame: pd.DataFrame, *, domain: str, dataset: str, amount_columns: list[str], date_ranges: list[tuple[str, str]]) -> None:
    run_post_checks(
        frame,
        domain=domain,
        dataset=dataset,
        amount_columns=amount_columns,
        date_ranges=date_ranges,
    )
    log(f"[{domain}] post-check passed: {dataset}")


def run_bond_pipeline() -> None:
    source_path = Path(BOND_SOURCE_FILE)
    if not source_path.exists():
        log(f"[bond-pipeline] skip missing source: {source_path}")
        return

    source_frames: dict[str, pd.DataFrame] = {}
    for sheet in BOND_SHEETS:
        frame = load_sheet(str(source_path), sheet_name=sheet, header=0)
        source_frames[sheet] = frame
        raw_rows = frame_to_raw_rows(frame, sheet_name=sheet)
        save_frame(raw_rows, RAW_DIR / "bond" / f"{sheet}.parquet", f"raw {sheet}")

    validate_pre(
        source_frames["Database_Bonds"],
        domain="bond",
        dataset="Database_Bonds",
        required_columns=["ISIN", "公司名", "交易對象", "下單日", "到期日", "投資面額", "交割金額"],
        date_columns=["下單日", "到期日", "交割日"],
        amount_columns=["投資面額", "應付本金", "前手息", "交割金額", "應收利息", "本利合計"],
    )
    validate_pre(
        source_frames["Database_Payback"],
        domain="bond",
        dataset="Database_Payback",
        required_columns=["ISIN", "公司名", "配息日", "應收利息", "本利合計"],
        date_columns=["配息日"],
        amount_columns=["應收利息", "本利合計"],
    )

    positions = standardize_bond_positions(source_frames["Database_Bonds"])
    cashflows = standardize_bond_cashflows(source_frames["Database_Payback"])

    validate_post(
        positions,
        domain="bond",
        dataset="stg_bond_position",
        amount_columns=["face_amount", "principal_amount", "settlement_amount", "cash_total"],
        date_ranges=[("trade_date", "maturity_date"), ("settlement_date", "maturity_date")],
    )
    validate_post(
        cashflows,
        domain="bond",
        dataset="stg_bond_cashflow",
        amount_columns=["coupon_amount", "total_payback"],
        date_ranges=[],
    )

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

    source_frames: dict[str, pd.DataFrame] = {}
    for sheet in STOCK_SHEETS:
        if sheet not in available_sheets:
            continue
        frame = load_sheet(str(source_path), sheet_name=sheet, header=0)
        source_frames[sheet] = frame
        raw_rows = frame_to_raw_rows(frame, sheet_name=sheet)
        save_frame(raw_rows, RAW_DIR / "stock" / f"{sheet}.parquet", f"raw {sheet}")

    validate_pre(
        source_frames["Database_Stock"],
        domain="stock",
        dataset="Database_Stock",
        required_columns=["股票代碼", "公司名", "成交股數", "實際總成本", "市值估算"],
        date_columns=[],
        amount_columns=["成交股數", "成交金額", "手續費", "實際總成本", "平均持股單價", "股價", "市值估算", "未實現損益估算"],
    )

    positions = standardize_japan_stock_positions(source_frames["Database_Stock"])
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
        trade_source = load_sheet(str(source_path), "PSA???????????", header=0)
        validate_pre(
            trade_source,
            domain="stock",
            dataset="PSA???????????",
            required_columns=["公司", "股票代號", "錄音日期", "下單金額", "實際總成本"],
            date_columns=["錄音日期"],
            amount_columns=["下單買價(日幣/股)", "下單股數", "下單金額", "實際成交單價", "實際成交股數", "實際成交金額", "手續費~0.2%", "實際總成本"],
        )
        trades = standardize_japan_stock_trades(trade_source)
    if "PSA??????" in available_sheets:
        price_raw = pd.read_excel(str(source_path), sheet_name="PSA??????", engine="openpyxl", header=0, nrows=120)
        save_frame(frame_to_raw_rows(price_raw, sheet_name="PSA??????"), RAW_DIR / "stock" / "PSA??????.parquet", "raw PSA??????")
        prices = standardize_japan_price_history(price_raw)

    validate_post(
        positions,
        domain="stock",
        dataset="stg_japan_stock_position",
        amount_columns=["shares", "trade_amount_jpy", "total_cost_jpy", "market_value_jpy", "unrealized_pnl_jpy"],
        date_ranges=[],
    )
    validate_post(
        trades,
        domain="stock",
        dataset="stg_japan_stock_trade",
        amount_columns=["order_amount_jpy", "fill_amount_jpy", "total_cost_jpy", "market_value_jpy", "unrealized_pnl_jpy"],
        date_ranges=[],
    )
    validate_post(
        prices,
        domain="stock",
        dataset="stg_japan_price_history",
        amount_columns=["close_price_jpy"],
        date_ranges=[],
    )

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

    source_frames: dict[str, pd.DataFrame] = {}
    for sheet in FCN_SHEETS:
        frame = load_sheet(str(source_path), sheet_name=sheet, header=0)
        source_frames[sheet] = frame
        raw_rows = frame_to_raw_rows(frame, sheet_name=sheet)
        save_frame(raw_rows, RAW_DIR / 'fcn' / f'{sheet}.parquet', f'raw {sheet}')

    validate_pre(
        source_frames["Database_FCN List"],
        domain="fcn",
        dataset="Database_FCN List",
        required_columns=["公司", "ISIN", "標的", "交易日", "到期日", "投資金額(日元)", "利息(日元)"],
        date_columns=["交易日", "交割日", "到期日", "領息日"],
        amount_columns=["Tenor", "票息", "Put Strike(%)", "Spot Price", "Strike Price", "投資金額(日元)", "利息(日元)"],
    )

    positions = standardize_fcn_positions(source_frames['Database_FCN List'])
    validate_post(
        positions,
        domain="fcn",
        dataset="stg_fcn_position",
        amount_columns=["investment_amount_jpy", "coupon_income_jpy", "spot_price", "strike_price"],
        date_ranges=[("trade_date", "maturity_date"), ("settlement_date", "maturity_date"), ("trade_date", "coupon_date")],
    )

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
        prepared_frame = _prepare_detail_sheet(frame)
        validate_pre(
            prepared_frame,
            domain="deposit",
            dataset=sheet,
            required_columns=["公司", "往來銀行", "起存日", "到期日", "合計"],
            date_columns=["起存日", "到期日"],
            amount_columns=["活期存款", "通知存款", "存款金額", "合計", "存款%", "年利率", "距到期剩餘天數"],
        )
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

    validate_post(
        staging,
        domain="deposit",
        dataset="stg_deposit_position",
        amount_columns=["amount", "amount_rmb_equiv", "total_amount", "total_ratio", "deposit_rate"],
        date_ranges=[("start_date", "maturity_date")],
    )

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



