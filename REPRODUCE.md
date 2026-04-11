# Reproduce (Clean Environment Guide)

This guide rebuilds the dashboard in a brand-new WSL machine with the **current architecture**:
- Streamlit Cloud hosts UI
- Local API serves data (through ngrok)
- Data files stay local and are NOT pushed to GitHub

## 1) Prerequisites

- WSL Ubuntu 24.04 with systemd enabled
- Python 3.12+ and `pip`
- `ngrok` installed in WSL and authtoken configured
- Source files available in Windows Downloads

## 2) Clone and bootstrap

```bash
cd /home/<your-user>/.openclaw/workspace
git clone https://github.com/<your-account>/investment_dashboard.git
cd investment_dashboard
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## 3) Enable Git safety guard (one-time)

```bash
git config core.hooksPath .githooks
```

This blocks accidental commits of:
- `data/`
- `*.parquet`, `*.xlsx`, `*.xls`, `*.csv`

## 4) Put source files in Downloads

Windows path:
- `C:\Users\<you>\Downloads\bond_source.xlsx`
- `C:\Users\<you>\Downloads\stock_source.xlsx`
- `C:\Users\<you>\Downloads\fcn_source.xlsx`

## 5) Run data update pipeline

```bash
cd /home/<your-user>/.openclaw/workspace/investment_dashboard
bash deploy/scripts/update_data_files.sh --run-pipeline
```

## 6) Start API + ngrok (manual test)

```bash
./deploy/scripts/start_api_ngrok_stack.sh
curl -s http://127.0.0.1:8000/health
```

Stop when needed:

```bash
./deploy/scripts/stop_api_ngrok_stack.sh
```

## 7) Install auto-start services (recommended)

```bash
sudo cp deploy/systemd/investment-dashboard-api.service /etc/systemd/system/
sudo cp deploy/systemd/investment-dashboard-ngrok-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now investment-dashboard-api.service
sudo systemctl enable --now investment-dashboard-ngrok-api.service
```

Check:

```bash
systemctl status investment-dashboard-api.service --no-pager
systemctl status investment-dashboard-ngrok-api.service --no-pager
```

## 8) Configure Streamlit Cloud Secret

Set `INVESTMENT_API_BASE_URL` to your current ngrok HTTPS URL.

Example:

```text
INVESTMENT_API_BASE_URL="https://xxxx-xxxx.ngrok-free.dev"
```

If ngrok URL rotates, update secret and reboot Streamlit app.

## 9) Verify end-to-end

```bash
curl -s http://127.0.0.1:8000/api/v1/investments/bonds | head
curl -s http://127.0.0.1:8000/api/v1/investments/charts/bonds | head
```

Then verify:
- Streamlit Cloud page loads with numbers/charts
- Telegram `/invest` returns updated summary

## 10) Push code/docs only (never data)

```bash
git add -A
git restore --staged data/ "*.parquet" "*.xlsx" "*.xls" "*.csv" || true
git status --short
git commit -m "update code/docs"
git pull --rebase origin main
git push origin main
```