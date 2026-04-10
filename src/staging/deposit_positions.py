from __future__ import annotations

from typing import Iterable

import pandas as pd

from src.utils.dates import excel_serial_to_date
from src.utils.numbers import coerce_numeric

BANK_TRANSLATION = str.maketrans({
    "銀": "银",
    "農": "农",
    "國": "国",
    "業": "业",
    "廣": "广",
    "發": "发",
    "東": "东",
    "華": "华",
    "匯": "汇",
    "豐": "丰",
    "龍": "龙",
    "蘇": "苏",
    "臺": "台",
})

ENTITY_MAP = {
    "PDC": "PDC",
    "ITC": "ITC",
    "Sili": "Silitech",
}

SKIP_COMPANY_TOKENS = ("小計", "合計", "人民幣合計", "美元合計")


def normalize_text(value) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    text = str(value).replace("\n", " ").strip()
    return text or None


def normalize_bank_name(value) -> str | None:
    text = normalize_text(value)
    if not text:
        return None
    return text.translate(BANK_TRANSLATION)


def safe_date(value):
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    return excel_serial_to_date(value)


def build_bank_dimension(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output.columns = [normalize_text(col) or str(col) for col in output.columns]
    rename_map = {
        "銀行名稱": "bank_name",
        "銀行分類（注1）": "bank_category",
        "公開上市": "is_listed",
        "中國大陸系統重要性銀行（注2）": "is_systemically_important",
        "主要股東": "major_shareholders",
        "執業區域分布": "coverage_region",
        "其他說明": "note",
    }
    output = output.rename(columns=rename_map)
    keep_cols = [col for col in rename_map.values() if col in output.columns]
    output = output[keep_cols].copy()
    output = output.loc[output["bank_name"].notna()].copy()
    output["bank_name"] = output["bank_name"].map(normalize_bank_name)
    if "bank_category" in output.columns:
        output["bank_category"] = output["bank_category"].map(normalize_text)
    output["is_state_owned_bank"] = output.get("bank_category", pd.Series(index=output.index)).fillna("").astype(str).str.contains("國有|国有")
    return output.drop_duplicates(subset=["bank_name"], keep="first")


def extract_fx_rate(frame: pd.DataFrame, fallback: float) -> float:
    dense = frame.dropna(how="all").dropna(axis=1, how="all")
    for _, row in dense.head(5).iterrows():
        for value in row.tolist():
            numeric = coerce_numeric(value)
            if numeric is not None and 6 <= numeric <= 8:
                return numeric
    return fallback


def _prepare_detail_sheet(frame: pd.DataFrame) -> pd.DataFrame:
    dense = frame.dropna(how="all").dropna(axis=1, how="all").copy()
    if dense.empty:
        return pd.DataFrame()
    main_header = [normalize_text(value) or f"col_{idx}" for idx, value in enumerate(dense.iloc[0, :14].tolist())]
    main_body = dense.iloc[2:, :14].copy().reset_index(drop=True)
    main_body.columns = main_header
    main_body["備註說明"] = dense.iloc[2:, -1].reset_index(drop=True)
    main_body = main_body.loc[main_body[["公司", "往來銀行"]].notna().any(axis=1)].copy()
    return main_body


def _build_rows(record: dict, company_group: str, currency: str) -> list[dict]:
    company_name = normalize_text(record.get("公司"))
    if not company_name or any(token in company_name for token in SKIP_COMPANY_TOKENS):
        return []
    bank_name = normalize_bank_name(record.get("往來銀行"))
    if not bank_name:
        return []
    branch_name = normalize_text(record.get("往來分行"))
    total_amount = coerce_numeric(record.get("合計"))
    total_ratio = coerce_numeric(record.get("存款%"))
    rate = coerce_numeric(record.get("年利率"))
    amount_bucket = coerce_numeric(record.get("存款金額"))
    start_date = safe_date(record.get("起存日"))
    maturity_date = safe_date(record.get("到期日"))
    days_to_maturity = coerce_numeric(record.get("距到期剩餘天數"))
    note = normalize_text(record.get("備註說明"))
    rows: list[dict] = []

    def append_row(deposit_type: str, amount, term_value=None, use_term_dates: bool = False):
        numeric_amount = coerce_numeric(amount)
        if numeric_amount is None or numeric_amount == 0:
            return
        rows.append({
            "company_group": company_group,
            "company_name": company_name,
            "bank_name": bank_name,
            "branch_name": branch_name,
            "currency": currency,
            "deposit_type": deposit_type,
            "amount": numeric_amount,
            "deposit_rate": rate if use_term_dates or deposit_type == "通知存款" else None,
            "term_years": coerce_numeric(term_value) if use_term_dates else None,
            "start_date": start_date if use_term_dates else None,
            "maturity_date": maturity_date if use_term_dates else None,
            "days_to_maturity": days_to_maturity if use_term_dates else None,
            "total_amount": total_amount,
            "total_ratio": total_ratio,
            "note": note,
        })

    append_row("活存", record.get("活期存款"))
    append_row("通知存款", record.get("通知存款"))
    ncd_term = record.get("可轉讓存單") or record.get("可轉讓大額存單")
    append_row("NCD", amount_bucket, ncd_term, True if coerce_numeric(ncd_term) else False)
    append_row("定存", amount_bucket, record.get("定期存款"), True if coerce_numeric(record.get("定期存款")) else False)

    if not rows and total_amount:
        rows.append({
            "company_group": company_group,
            "company_name": company_name,
            "bank_name": bank_name,
            "branch_name": branch_name,
            "currency": currency,
            "deposit_type": "其他",
            "amount": total_amount,
            "deposit_rate": rate,
            "term_years": None,
            "start_date": start_date,
            "maturity_date": maturity_date,
            "days_to_maturity": days_to_maturity,
            "total_amount": total_amount,
            "total_ratio": total_ratio,
            "note": note,
        })
    return rows


def extract_deposit_rows(frame: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    prepared = _prepare_detail_sheet(frame)
    if prepared.empty:
        return pd.DataFrame()
    prefix, currency_token = sheet_name.split("-", 1)
    company_group = ENTITY_MAP.get(prefix, prefix)
    currency = "USD" if "USD" in currency_token.upper() else "RMB"
    rows = []
    for _, row in prepared.iterrows():
        rows.extend(_build_rows(row.to_dict(), company_group, currency))
    output = pd.DataFrame(rows)
    if output.empty:
        return output
    output["company_name"] = output["company_name"].map(normalize_text)
    output["company_group"] = output["company_group"].map(normalize_text)
    output["bank_name"] = output["bank_name"].map(normalize_bank_name)
    output["branch_name"] = output["branch_name"].map(normalize_text)
    output["note"] = output["note"].map(normalize_text)
    return output


def apply_deposit_enrichment(frame: pd.DataFrame, fx_rate: float, bank_dim: pd.DataFrame | None = None) -> pd.DataFrame:
    output = frame.copy()
    output["amount_rmb_equiv"] = output.apply(
        lambda row: row["amount"] * fx_rate if row["currency"] == "USD" else row["amount"],
        axis=1,
    )
    if bank_dim is not None and not bank_dim.empty:
        enrich_cols = ["bank_name", "bank_category", "is_state_owned_bank"]
        output = output.merge(bank_dim[enrich_cols], on="bank_name", how="left")
    else:
        output["bank_category"] = None
        output["is_state_owned_bank"] = None
    output["days_to_maturity"] = output["days_to_maturity"].fillna(
        (pd.to_datetime(output["maturity_date"], errors="coerce") - pd.Timestamp.today().normalize()).dt.days
    )
    return output


def build_deposit_staging(detail_frames: Iterable[tuple[str, pd.DataFrame]], bank_dim: pd.DataFrame | None, fx_rate: float) -> pd.DataFrame:
    parts = [extract_deposit_rows(frame, sheet_name) for sheet_name, frame in detail_frames]
    parts = [frame for frame in parts if not frame.empty]
    if not parts:
        return pd.DataFrame()
    output = pd.concat(parts, ignore_index=True)
    output = apply_deposit_enrichment(output, fx_rate=fx_rate, bank_dim=bank_dim)
    return output.sort_values(["company_group", "company_name", "bank_name", "currency", "deposit_type"]).reset_index(drop=True)
