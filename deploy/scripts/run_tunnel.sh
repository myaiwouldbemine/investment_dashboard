#!/usr/bin/env bash
set -euo pipefail

URL_FILE=/tmp/investment_dashboard_tunnel_url
LOG_FILE=/tmp/cloudflared-tunnel.log

: > "$LOG_FILE"

cloudflared tunnel --url http://localhost:8501 --loglevel info 2>&1 | tee -a "$LOG_FILE" | while IFS= read -r line; do
  echo "$line"

  url="$(printf '%s\n' "$line" | grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' | head -n1 || true)"
  if [[ -n "$url" ]]; then
    printf '%s\n' "$url" > "$URL_FILE"
  fi
done
