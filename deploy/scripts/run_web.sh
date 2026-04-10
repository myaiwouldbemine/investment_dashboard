#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/ericarthuang/.openclaw/workspace/investment_dashboard"
cd "$PROJECT_DIR"
. .venv/bin/activate
exec streamlit run app.py --server.address 0.0.0.0 --server.port 8501
