from __future__ import annotations

import pandas as pd


def build_ai_alerts(bond_position: pd.DataFrame) -> pd.DataFrame:
    alerts = []
    if not bond_position.empty:
        maturity_limit = pd.Timestamp.today().normalize() + pd.Timedelta(days=180)
        soon = pd.to_datetime(bond_position["maturity_date"], errors="coerce") <= maturity_limit
        for _, row in bond_position.loc[soon.fillna(False)].iterrows():
            alerts.append({
                "domain": "bond",
                "alert_type": "maturity_due_soon",
                "entity_name": str(row.get("issuer_name") or ""),
                "severity": "medium",
                "message": "Bond matures within 180 days",
                "status": "open",
            })
    return pd.DataFrame(alerts)
