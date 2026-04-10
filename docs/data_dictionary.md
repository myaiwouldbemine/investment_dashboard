# Bond Data Dictionary

## Workbook

Source file: `Bonds Analysis.xlsx`

Sheets used:
- `Database_Bonds`: bond positions and summary metrics
- `Database_Payback`: coupon and principal cashflows
- `Batabase_Limit`: rating-based investment limits

## Staging tables

### `stg_bond_position`
Core bond position table with issuer, rating, yield, tenor, and invested amounts.

### `stg_bond_cashflow`
Cashflow schedule with coupon dates and total payback amounts.

### `stg_bond_limit`
Rating limit master table for exposure monitoring.

## Mart tables

### `mart_bond_dashboard_position`
Dashboard-ready positions with portfolio weights and maturity buckets.

### `mart_bond_dashboard_cashflow`
Monthly and yearly cashflow aggregation.

### `mart_bond_dashboard_limit_usage`
Current rating exposure compared with configured limits.

### `mart_ai_alerts`
Bond-specific alerts for maturity horizon and limit usage.
