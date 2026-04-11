#!/usr/bin/env bash
set -euo pipefail

API_PORT="${API_PORT:-8000}"

pkill -f "uvicorn api:app --host 0.0.0.0 --port ${API_PORT}" >/dev/null 2>&1 || true
pkill -f "ngrok http ${API_PORT}" >/dev/null 2>&1 || true

echo "[OK] Stopped API/ngrok for port ${API_PORT}."
