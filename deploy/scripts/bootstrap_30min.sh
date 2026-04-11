#!/usr/bin/env bash
set -euo pipefail

# 30-minute bootstrap for a fresh WSL environment.
# Safe to re-run: operations are idempotent where possible.

PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
WITH_SYSTEMD="false"
RUN_SMOKE="true"

usage() {
  cat <<USAGE
Usage: $0 [--project-dir <path>] [--python-bin <python>] [--with-systemd] [--skip-smoke]

Options:
  --project-dir <path>   Project root. Default: current working directory
  --python-bin <python>  Python executable. Default: python3
  --with-systemd         Install and enable API/ngrok services (requires sudo)
  --skip-smoke           Skip API/ngrok smoke startup test
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir)
      PROJECT_DIR="$2"; shift 2 ;;
    --python-bin)
      PYTHON_BIN="$2"; shift 2 ;;
    --with-systemd)
      WITH_SYSTEMD="true"; shift ;;
    --skip-smoke)
      RUN_SMOKE="false"; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "[ERROR] Unknown option: $1"
      usage
      exit 1 ;;
  esac
done

cd "$PROJECT_DIR"

echo "[INFO] Project directory: $PROJECT_DIR"

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[ERROR] Missing command: $cmd"
    exit 1
  fi
}

require_file() {
  local f="$1"
  if [[ ! -f "$f" ]]; then
    echo "[ERROR] Missing required file: $f"
    exit 1
  fi
}

require_file "requirements.txt"
require_file "api.py"
require_file "app.py"
require_file "deploy/scripts/start_api_ngrok_stack.sh"
require_file "deploy/scripts/update_data_files.sh"

require_cmd "$PYTHON_BIN"
require_cmd git
require_cmd curl

if ! command -v ngrok >/dev/null 2>&1; then
  echo "[WARN] ngrok not found. Install it before cloud API mode."
  echo "       Ubuntu example: sudo snap install ngrok"
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[INFO] Creating venv: $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  echo "[OK] venv already exists: $VENV_DIR"
fi

echo "[INFO] Installing Python dependencies"
"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV_DIR/bin/pip" install -r requirements.txt >/dev/null

if [[ -d ".githooks" ]]; then
  git config core.hooksPath .githooks
  echo "[OK] Enabled git hook path: .githooks"
else
  echo "[WARN] .githooks folder not found; skipping hook setup"
fi

if [[ "$WITH_SYSTEMD" == "true" ]]; then
  echo "[INFO] Installing systemd services (sudo required)"
  sudo cp deploy/systemd/investment-dashboard-api.service /etc/systemd/system/
  sudo cp deploy/systemd/investment-dashboard-ngrok-api.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable --now investment-dashboard-api.service
  sudo systemctl enable --now investment-dashboard-ngrok-api.service
  echo "[OK] systemd services enabled"
else
  echo "[INFO] Skipping systemd install (use --with-systemd to enable)"
fi

if [[ "$RUN_SMOKE" == "true" ]]; then
  if command -v ngrok >/dev/null 2>&1; then
    echo "[INFO] Running smoke test: start API + ngrok"
    bash deploy/scripts/start_api_ngrok_stack.sh >/tmp/bootstrap_start_stack.log 2>&1 || {
      echo "[ERROR] Smoke test failed. Log: /tmp/bootstrap_start_stack.log"
      exit 1
    }
    if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
      echo "[OK] API health check passed"
    else
      echo "[ERROR] API health check failed after startup"
      exit 1
    fi
    echo "[OK] Smoke test passed"
    echo "[INFO] ngrok URL file: /tmp/investment_api_ngrok_url"
  else
    echo "[WARN] Skip smoke test because ngrok is missing"
  fi
else
  echo "[INFO] Smoke test skipped by option"
fi

echo
echo "========== NEXT ACTIONS =========="
echo "1) Put source files into Windows Downloads:"
echo "   bond_source.xlsx / stock_source.xlsx / fcn_source.xlsx"
echo "2) Run data update:"
echo "   bash deploy/scripts/update_data_files.sh --run-pipeline"
echo "3) Set Streamlit Secret INVESTMENT_API_BASE_URL to current ngrok URL"
echo "4) Verify: /health, Streamlit Cloud page, Telegram /invest"
echo "=================================="