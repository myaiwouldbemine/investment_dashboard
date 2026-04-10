from __future__ import annotations
import pandas as pd

def build_quality_log(batch_id: str, domain: str, sheet_name: str, row_no: int, field_name: str, issue_type: str, raw_value: object, resolution: str) -> pd.DataFrame:
    return pd.DataFrame([{"batch_id": batch_id, "domain": domain, "sheet_name": sheet_name, "row_no": row_no, "field_name": field_name, "issue_type": issue_type, "raw_value": raw_value, "resolution": resolution, "logged_at": pd.Timestamp.utcnow()}])
