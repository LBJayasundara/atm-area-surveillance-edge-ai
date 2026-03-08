#!/usr/bin/env bash
# Stop the ATM surveillance system
set -euo pipefail

PID_FILE="/tmp/atm-surveillance.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        rm -f "$PID_FILE"
        echo "ATM Surveillance system stopped (PID $PID)."
    else
        echo "Process $PID not running."
        rm -f "$PID_FILE"
    fi
else
    echo "PID file not found — system may not be running."
fi
