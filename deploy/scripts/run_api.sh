#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/ericarthuang/.openclaw/workspace/investment_dashboard"
cd "$PROJECT_DIR"
. .venv/bin/activate
exec uvicorn api:app --host 0.0.0.0 --port 8000
