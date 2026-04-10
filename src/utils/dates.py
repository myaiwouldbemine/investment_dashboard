from datetime import datetime, timedelta
from typing import Any
import pandas as pd

def excel_serial_to_date(value: Any) -> pd.Timestamp | None:
    if value in (None, ""):
        return None
    if isinstance(value, (datetime, pd.Timestamp)):
        return pd.Timestamp(value).normalize()
    if isinstance(value, (int, float)):
        return pd.Timestamp(datetime(1899, 12, 30) + timedelta(days=float(value))).normalize()
    try:
        return pd.to_datetime(value).normalize()
    except (TypeError, ValueError):
        return None
