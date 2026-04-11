# API + ngrok Auto-Start and Data Update

This guide gives you two practical workflows:
- Auto-start API + ngrok on boot
- Update source files and refresh dashboard data

## 1) One-command startup (manual)

From WSL:

```bash
cd /home/ericarthuang/.openclaw/workspace/investment_dashboard
./deploy/scripts/start_api_ngrok_stack.sh
```

What it does:
- Stops old API/ngrok processes for port `8000`
- Starts `uvicorn api:app --port 8000`
- Waits for `/health`
- Starts `ngrok http 8000`
- Writes URL to `/tmp/investment_api_ngrok_url`

Stop command:

```bash
./deploy/scripts/stop_api_ngrok_stack.sh
```

## 2) Auto-start on boot (systemd)

Prerequisite:
- WSL has systemd enabled
- `ngrok` installed and authtoken configured in WSL

Install services:

```bash
cd /home/ericarthuang/.openclaw/workspace/investment_dashboard
sudo cp deploy/systemd/investment-dashboard-api.service /etc/systemd/system/
sudo cp deploy/systemd/investment-dashboard-ngrok-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now investment-dashboard-api.service
sudo systemctl enable --now investment-dashboard-ngrok-api.service
```

Check status:

```bash
systemctl status investment-dashboard-api --no-pager
systemctl status investment-dashboard-ngrok-api --no-pager
```

After reboot, get ngrok URL:

```bash
curl -s http://127.0.0.1:4040/api/tunnels
```

Then set Streamlit Secret:

- `INVESTMENT_API_BASE_URL="https://<your-ngrok-domain>"`

## 3) Update data source files

Expected source filenames (fixed):
- `bond_source.xlsx`
- `stock_source.xlsx`
- `fcn_source.xlsx`

Default source folder:
- `/mnt/c/Users/ericarthuang/Downloads`

Run copy only:

```bash
cd /home/ericarthuang/.openclaw/workspace/investment_dashboard
./deploy/scripts/update_data_files.sh
```

Run copy + pipeline:

```bash
./deploy/scripts/update_data_files.sh --run-pipeline
```

Use custom source folder:

```bash
./deploy/scripts/update_data_files.sh --downloads-dir "/mnt/c/Users/<you>/Downloads" --run-pipeline
```

## 4) Quick verification checklist

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/api/v1/investments/charts/bonds | head
curl -s http://127.0.0.1:8000/api/v1/investments/charts/stocks | head
curl -s http://127.0.0.1:8000/api/v1/investments/charts/fcn | head
```

If all three chart endpoints return JSON with `"available": true`, Streamlit can render charts in API mode.
