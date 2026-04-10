from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
from hashlib import md5
from pathlib import Path
import pandas as pd

@dataclass(slots=True)
class ImportBatch:
    batch_id: str
    source_file_name: str
    source_file_path: str
    source_domain: str
    file_date: str | None
    imported_at: str
    status: str = "loaded"
    notes: str | None = None

def build_batch_id(source_path: str, imported_at: datetime | None = None) -> str:
    timestamp = imported_at or datetime.utcnow()
    digest = md5(f"{source_path}|{timestamp.isoformat()}".encode("utf-8")).hexdigest()[:10]
    return f"batch_{timestamp:%Y%m%d%H%M%S}_{digest}"

def register_batch(source_path: str, source_domain: str, file_date: str | None = None) -> pd.DataFrame:
    path = Path(source_path)
    imported_at = datetime.utcnow()
    batch = ImportBatch(build_batch_id(source_path, imported_at), path.name, str(path), source_domain, file_date, imported_at.isoformat())
    return pd.DataFrame([asdict(batch)])
