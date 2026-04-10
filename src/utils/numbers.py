from typing import Any
import pandas as pd

EXCEL_ERROR_TOKENS = {"#VALUE!", "#REF!", "#DIV/0!", "#N/A"}

def coerce_numeric(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped in EXCEL_ERROR_TOKENS:
            return None
        try:
            return float(stripped.replace(",", ""))
        except ValueError:
            return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
