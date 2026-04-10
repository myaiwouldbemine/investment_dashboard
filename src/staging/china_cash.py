from __future__ import annotations

import pandas as pd

from src.utils.numbers import coerce_numeric

CHINA_CASH_COLUMNS = [
    "batch_id", "as_of_date", "company_name", "company_code", "currency", "balance_type", "bank_name", "branch_name",
    "amount", "position_ratio", "deposit_rate", "term_years", "start_date", "maturity_date", "days_to_maturity",
    "total_amount", "total_ratio", "amount_rmb_equiv", "bank_category", "is_state_owned_bank", "note", "source_sheet", "source_row_no",
]

SNAPSHOT_COLUMNS = ["batch_id", "as_of_date", "company_name", "metric_name", "metric_value", "fx_rate", "source_sheet"]


def empty_china_cash_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=CHINA_CASH_COLUMNS)


def parse_china_summary_sheet(frame: pd.DataFrame, batch_id: str, source_sheet: str, fx_rate: float | None = None) -> pd.DataFrame:
    output_rows: list[dict[str, object]] = []
    if frame.empty or len(frame) < 3:
        return empty_china_cash_frame()

    for row_no in range(2, len(frame)):
        row = frame.iloc[row_no]
        company = row.iloc[0]
        if pd.isna(company) or str(company).strip() in {"", "總計", "PSA總計"}:
            continue
        company_name = str(company).strip()
        note = row.iloc[16] if len(row) > 16 else None
        rmb_total = coerce_numeric(row.iloc[4])
        usd_total = coerce_numeric(row.iloc[11])
        usd_rmb_equiv = coerce_numeric(row.iloc[13])
        grand_total = coerce_numeric(row.iloc[14])
        if rmb_total is not None:
            output_rows.append({
                "batch_id": batch_id,
                "as_of_date": None,
                "company_name": company_name,
                "company_code": company_name,
                "currency": "RMB",
                "balance_type": "summary_total",
                "bank_name": None,
                "branch_name": None,
                "amount": rmb_total,
                "position_ratio": None,
                "deposit_rate": None,
                "term_years": None,
                "start_date": None,
                "maturity_date": None,
                "days_to_maturity": None,
                "total_amount": rmb_total,
                "total_ratio": None,
                "amount_rmb_equiv": rmb_total,
                "bank_category": None,
                "is_state_owned_bank": None,
                "note": note,
                "source_sheet": source_sheet,
                "source_row_no": row_no + 1,
            })
        if usd_total is not None:
            output_rows.append({
                "batch_id": batch_id,
                "as_of_date": None,
                "company_name": company_name,
                "company_code": company_name,
                "currency": "USD",
                "balance_type": "summary_total",
                "bank_name": None,
                "branch_name": None,
                "amount": usd_total,
                "position_ratio": None,
                "deposit_rate": None,
                "term_years": None,
                "start_date": None,
                "maturity_date": None,
                "days_to_maturity": None,
                "total_amount": grand_total,
                "total_ratio": None,
                "amount_rmb_equiv": usd_rmb_equiv,
                "bank_category": None,
                "is_state_owned_bank": None,
                "note": note,
                "source_sheet": source_sheet,
                "source_row_no": row_no + 1,
            })
    return pd.DataFrame(output_rows, columns=CHINA_CASH_COLUMNS)


def parse_china_monthly_snapshot(frame: pd.DataFrame, batch_id: str, source_sheet: str) -> pd.DataFrame:
    if frame.empty or len(frame) < 4:
        return pd.DataFrame(columns=SNAPSHOT_COLUMNS)

    header_row = frame.iloc[0]
    metric_rows = {
        "rmb_total": frame.iloc[1],
        "usd_rmb_equiv": frame.iloc[2],
        "grand_total": frame.iloc[3],
    }
    date_columns = []
    for idx in range(8, len(header_row)):
        label = header_row.iloc[idx]
        if pd.isna(label):
            continue
        text = str(label).strip()
        if "/" in text:
            date_columns.append((idx, text))

    rows = []
    fx_rate = coerce_numeric(metric_rows["usd_rmb_equiv"].iloc[6])
    for idx, date_label in date_columns:
        as_of_date = pd.to_datetime(date_label + '/01', errors='coerce')
        if pd.isna(as_of_date):
            continue
        for metric_name, metric_row in metric_rows.items():
            rows.append({
                "batch_id": batch_id,
                "as_of_date": as_of_date,
                "company_name": None,
                "metric_name": metric_name,
                "metric_value": coerce_numeric(metric_row.iloc[idx]),
                "fx_rate": fx_rate,
                "source_sheet": source_sheet,
            })
    return pd.DataFrame(rows, columns=SNAPSHOT_COLUMNS)
