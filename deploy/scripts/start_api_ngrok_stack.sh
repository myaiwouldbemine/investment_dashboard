#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/ericarthuang/.openclaw/workspace/investment_dashboard"
API_PORT="${API_PORT:-8000}"
API_LOG="${API_LOG:-/tmp/investment_api.log}"
NGROK_LOG="${NGROK_LOG:-/tmp/investment_api_ngrok.log}"
NGROK_URL_FILE="${NGROK_URL_FILE:-/tmp/investment_api_ngrok_url}"

cd "$PROJECT_DIR"

if [[ ! -x ".venv/bin/uvicorn" ]]; then
  echo "[ERROR] .venv/bin/uvicorn not found. Please install dependencies first."
  exit 1
fi

if ! command -v ngrok >/dev/null 2>&1; then
  echo "[ERROR] ngrok not found in PATH. Install ngrok in WSL first."
  exit 1
fi

# Stop previous processes to avoid duplicate listeners.
pkill -f "uvicorn api:app --host 0.0.0.0 --port ${API_PORT}" >/dev/null 2>&1 || true
pkill -f "ngrok http ${API_PORT}" >/dev/null 2>&1 || true

nohup .venv/bin/uvicorn api:app --host 0.0.0.0 --port "$API_PORT" >"$API_LOG" 2>&1 &

api_ready="false"
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
    api_ready="true"
    break
  fi
  sleep 1
done

if [[ "$api_ready" != "true" ]]; then
  echo "[ERROR] API did not become healthy in time."
  echo "[HINT] Check log: $API_LOG"
  exit 1
fi

nohup ngrok http "$API_PORT" >"$NGROK_LOG" 2>&1 &

ngrok_url=""
for _ in $(seq 1 30); do
  ngrok_url="$(python3 - <<'PY'
import json
import urllib.request

try:
    data = json.loads(urllib.request.urlopen('http://127.0.0.1:4040/api/tunnels', timeout=2).read().decode())
    for tunnel in data.get('tunnels', []):
        url = tunnel.get('public_url', '')
        if url.startswith('https://'):
            print(url)
            break
except Exception:
    pass
PY
)"
  if [[ -n "$ngrok_url" ]]; then
    break
  fi
  sleep 1
done

if [[ -n "$ngrok_url" ]]; then
  printf '%s\n' "$ngrok_url" >"$NGROK_URL_FILE"
fi

echo "[OK] API is running on http://127.0.0.1:${API_PORT}"
if [[ -n "$ngrok_url" ]]; then
  echo "[OK] ngrok URL: $ngrok_url"
  echo "[NEXT] Set Streamlit Secret: INVESTMENT_API_BASE_URL=\"$ngrok_url\""
else
  echo "[WARN] ngrok URL not detected yet."
  echo "[HINT] Wait 5-10 seconds, then check: cat $NGROK_URL_FILE"
  echo "[HINT] ngrok log: $NGROK_LOG"
fi
