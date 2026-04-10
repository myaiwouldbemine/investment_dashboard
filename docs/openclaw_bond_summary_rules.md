# OpenClaw Bond Summary Rules

Use the latest mart outputs:
- `mart_bond_dashboard_position/latest.parquet`
- `mart_bond_dashboard_cashflow/latest.parquet`

## Daily summary order

1. Portfolio headline
- total face amount
- average YTM
- average duration
- number of issuers

2. Concentration highlights
- top 3 issuers by face amount
- top 3 counterparties by face amount
- largest rating bucket exposures

3. Cashflow focus
- next 3 months total payback
- highest payback year
- unusual concentration in one year or month

4. Suggested response style
- Keep the first paragraph short and numeric.
- Use flat bullets for concentration and cashflow items.
- Mention issuer names and larger upcoming cashflow years when available.

## Example prompts for OpenClaw

- Summarize today's bond portfolio structure from the latest mart files.
- Prepare a short morning briefing for the bond portfolio manager.
- Explain which issuers and counterparties matter most right now.
- Summarize the cashflow profile of the bond portfolio.
