#!/usr/bin/env bash
# =============================================================================
# ATM Area Surveillance — Installation Script
# Target: Raspberry Pi 4 (Raspberry Pi OS Bullseye/Bookworm, 64-bit)
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$REPO_DIR/venv"
PYTHON="python3"
SERVICE_NAME="atm-surveillance"

echo "===================================================="
echo " ATM Area Surveillance Installation"
echo " Repo: $REPO_DIR"
echo "===================================================="

# --- System packages ---------------------------------------------------------
echo "[1/8] Installing system packages…"
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
    python3-pip python3-venv python3-dev \
    libopencv-dev ffmpeg libatlas-base-dev \
    libhdf5-dev libjpeg-dev libpng-dev \
    sqlite3 curl git

# --- Python virtual environment ----------------------------------------------
echo "[2/8] Creating Python virtual environment…"
$PYTHON -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip wheel

# --- Python dependencies -----------------------------------------------------
echo "[3/8] Installing Python dependencies…"
pip install -r "$REPO_DIR/requirements.txt"

# --- Directory structure -----------------------------------------------------
echo "[4/8] Creating runtime directories…"
mkdir -p "$REPO_DIR/logs"
mkdir -p "$REPO_DIR/snapshots"
mkdir -p "$REPO_DIR/models"
mkdir -p "$REPO_DIR/database"

# --- Database initialisation -------------------------------------------------
echo "[5/8] Initialising database…"
cd "$REPO_DIR"
python database/init_db.py

# --- Download YOLOv8n base model (person detection) --------------------------
echo "[6/8] Downloading YOLOv8n model…"
python - <<'PYEOF'
try:
    from ultralytics import YOLO
    model = YOLO("yolov8n.pt")
    import shutil, os
    dst = "models/yolov8n.pt"
    src = "yolov8n.pt"
    if os.path.isfile(src) and not os.path.isfile(dst):
        shutil.move(src, dst)
    print("YOLOv8n downloaded to models/yolov8n.pt")
except Exception as e:
    print(f"Warning: Could not download YOLOv8n — {e}")
    print("Place your model manually in models/yolov8n.pt")
PYEOF

# --- Systemd service ---------------------------------------------------------
echo "[7/8] Installing systemd service…"
if [ -d "/etc/systemd/system" ]; then
    sudo cp "$REPO_DIR/deployment/$SERVICE_NAME.service" "/etc/systemd/system/"
    # Patch the service to use the correct repo path and venv
    sudo sed -i "s|/opt/atm-surveillance|$REPO_DIR|g" \
        "/etc/systemd/system/$SERVICE_NAME.service"
    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    echo "  Service enabled. Start with: sudo systemctl start $SERVICE_NAME"
else
    echo "  Skipping systemd setup (not running on systemd OS)."
fi

# --- Config reminder ---------------------------------------------------------
echo "[8/8] Configuration reminder…"
echo ""
echo "  Edit config/config.yaml to set:"
echo "    camera.rtsp_url   — your camera RTSP stream URL"
echo "    api.auth_token    — change the default auth token"
echo ""
echo "===================================================="
echo " Installation complete!"
echo " Start:  bash scripts/start.sh"
echo " Stop:   bash scripts/stop.sh"
echo "===================================================="
