from __future__ import annotations
from pathlib import Path
import json
import pandas as pd


def list_sheets(workbook_path: str) -> list[str]:
    return pd.ExcelFile(workbook_path, engine="openpyxl").sheet_names


def load_sheet(workbook_path: str, sheet_name: str, header=None) -> pd.DataFrame:
    return pd.read_excel(workbook_path, sheet_name=sheet_name, engine="openpyxl", header=header)


def frame_to_raw_rows(frame: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    records = []
    for row_number, (_, row) in enumerate(frame.iterrows(), start=1):
        raw_payload = {str(key): value for key, value in row.to_dict().items()}
        record = {
            "sheet_name": sheet_name,
            "row_number": row_number,
            "raw_json": json.dumps(raw_payload, ensure_ascii=False, default=str),
            "loaded_at": pd.Timestamp.utcnow().isoformat(),
        }
        for idx, value in enumerate(row.tolist()):
            record[f"col_{idx + 1:02d}"] = None if pd.isna(value) else str(value)
        records.append(record)
    return pd.DataFrame(records)


def workbook_exists(workbook_path: str) -> bool:
    return Path(workbook_path).exists()
