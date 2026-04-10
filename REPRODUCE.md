# Reproduce

This guide rebuilds the investment dashboard from a clean clone in WSL.

## Prerequisites

- WSL Ubuntu 24.04.
- Python 3.11 or newer.
- Source Excel workbooks available in `/mnt/c/Users/ericarthuang/Downloads/`.

## Source Files

The pipeline reads the workbook paths defined in `config/settings.py`.
If you use different filenames or locations, update that file before running the pipeline.

## Rebuild Steps

1. Open a shell in the repository root.
2. Create a virtual environment and install dependencies.
3. Confirm the source Excel files are present.
4. Run the pipeline to build raw and processed parquet outputs.
5. Start the FastAPI service.
6. Start the Streamlit web UI if you want a browser page for Telegram links.
7. Check `/health` and the summary endpoints.

```bash
cd /home/ericarthuang/.openclaw/workspace/investment_dashboard
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python run_pipeline.py
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

## Streamlit Web UI

If you want a browser page for the Telegram button, start the Streamlit app in another terminal and use that URL for `INVESTMENT_DASHBOARD_URL`.

```bash
cd /home/ericarthuang/.openclaw/workspace/investment_dashboard
. .venv/bin/activate
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

## Systemd Services

If you want both services to keep running in WSL, install the unit files and enable them.

```bash
sudo cp deploy/systemd/investment-dashboard-api.service /etc/systemd/system/investment-dashboard-api.service
sudo cp deploy/systemd/investment-dashboard-web.service /etc/systemd/system/investment-dashboard-web.service
sudo systemctl daemon-reload
sudo systemctl enable investment-dashboard-api investment-dashboard-web
sudo systemctl restart investment-dashboard-api investment-dashboard-web
```

## Verification

```bash
curl http://127.0.0.1:8000/health
python -m unittest tests.test_api -v
```

For the full end-to-end flow, keep the source workbooks in place and run the bot project after the API is healthy.
