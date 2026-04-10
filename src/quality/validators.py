from __future__ import annotations
import pandas as pd

def require_columns(frame: pd.DataFrame, required: list[str]) -> list[str]:
    return [column for column in required if column not in frame.columns]

def duplicate_count(frame: pd.DataFrame, subset: list[str]) -> int:
    if frame.empty:
        return 0
    return int(frame.duplicated(subset=subset).sum())
