#!/usr/bin/env bash
# Start the ATM surveillance system
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="$REPO_DIR/venv/bin/python"
CONFIG="$REPO_DIR/config/config.yaml"
LOG_FILE="$REPO_DIR/logs/start.log"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Virtual environment not found. Run scripts/install.sh first."
    exit 1
fi

echo "Starting ATM Surveillance system…"
cd "$REPO_DIR"
nohup "$VENV_PYTHON" main.py --config "$CONFIG" >> "$LOG_FILE" 2>&1 &
PID=$!
echo "$PID" > /tmp/atm-surveillance.pid
echo "Started with PID $PID (log: $LOG_FILE)"
