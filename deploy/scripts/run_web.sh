#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/ericarthuang/.openclaw/workspace/investment_dashboard"
cd "$PROJECT_DIR"

if [ -f .env ]; then
  set -a
  # shellcheck source=/dev/null
  . ./.env
  set +a
fi

. .venv/bin/activate
exec streamlit run app.py --server.address 0.0.0.0 --server.port 8501
