#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/ericarthuang/.openclaw/workspace/investment_dashboard"
INBOX_DIR="$PROJECT_DIR/data/inbox"
DOWNLOADS_DIR_DEFAULT="/mnt/c/Users/ericarthuang/Downloads"
DOWNLOADS_DIR="$DOWNLOADS_DIR_DEFAULT"
RUN_PIPELINE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --downloads-dir)
      DOWNLOADS_DIR="$2"
      shift 2
      ;;
    --run-pipeline)
      RUN_PIPELINE="true"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--downloads-dir <path>] [--run-pipeline]"
      exit 1
      ;;
  esac
done

mkdir -p "$INBOX_DIR"

required=(
  "bond_source.xlsx"
  "stock_source.xlsx"
  "fcn_source.xlsx"
)

for name in "${required[@]}"; do
  src="$DOWNLOADS_DIR/$name"
  dst="$INBOX_DIR/$name"

  if [[ ! -f "$src" ]]; then
    echo "[ERROR] Missing file: $src"
    exit 1
  fi

  cp -f "$src" "$dst"
  echo "[OK] Copied: $src -> $dst"
done

if [[ "$RUN_PIPELINE" == "true" ]]; then
  cd "$PROJECT_DIR"
  if [[ ! -x ".venv/bin/python" ]]; then
    echo "[ERROR] .venv/bin/python not found."
    exit 1
  fi

  echo "[INFO] Running pipeline..."
  .venv/bin/python run_pipeline.py
  echo "[OK] Pipeline finished."
else
  echo "[INFO] Pipeline not executed. Add --run-pipeline to run it now."
fi

echo "[NEXT] Validate files in: $INBOX_DIR"
