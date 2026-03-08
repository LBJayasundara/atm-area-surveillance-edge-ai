# ATM Area Surveillance Edge AI System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)](https://python.org)

Real-time intelligent surveillance system for detecting suspicious activities near ATMs or banking areas using computer vision and edge computing.

## Features

- 🔫 **Weapon Detection** — guns and knives detected in real time
- 😷 **Face Concealment Detection** — helmets and masks in restricted zones
- 🚶 **Loitering Detection** — persons staying > 120 s near ATMs
- 📱 **Mobile Alerts** — instant push notifications to Flutter app
- 🔌 **Edge AI** — runs entirely on Raspberry Pi 4 (no cloud dependency)
- 🔒 **Secure REST API** — token-authenticated Flask API

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/LBJayasundara/atm-area-surveillance-edge-ai.git
cd atm-area-surveillance-edge-ai

# 2. Install (on Raspberry Pi)
bash scripts/install.sh

# 3. Configure (edit RTSP URL and auth token)
nano config/config.yaml

# 4. Start
bash scripts/start.sh
```

## System Architecture

```
IP CCTV Camera (RTSP)
        │
        ▼
  VideoStream (src/video_stream.py)
        │  frames
        ▼
  Detector (src/detector.py)          ← YOLOv8 nano
        │  detections
        ▼
  Tracker (src/tracker.py)            ← ByteTrack
        │  tracks
        ├──► LoiteringDetector (src/loitering_detector.py)
        │         │ loiter events
        └──► ActivityAnalyzer (src/activity_analyzer.py)
                  │ activity events
                  ▼
           AlertManager (src/alert_manager.py)
                  │  SQLite + snapshots
                  ▼
           APIServer (src/api_server.py)   ←── Flutter App
```

## Detection Classes

| Class | ID | Description |
|-------|----|-------------|
| gun | 0 | Firearms |
| knife | 1 | Bladed weapons |
| helmet | 2 | Helmets worn in ATM zone |
| mask | 3 | Face masks in restricted areas |
| person | — | COCO pretrained (tracking) |

## Tech Stack

| Component | Technology |
|-----------|------------|
| Edge AI | Python 3.9, OpenCV, YOLOv8 nano |
| Tracking | ByteTrack |
| API | Flask + SQLite |
| Mobile App | Flutter 3 |

## Directory Structure

```
atm-area-surveillance-edge-ai/
├── src/               # Core Python modules
├── config/            # YAML config and zone definitions
├── data/              # Dataset preparation scripts
├── training/          # Model training and export
├── database/          # SQLite schema and init
├── scripts/           # Install/start/stop scripts
├── deployment/        # systemd service, nginx config
├── tests/             # pytest test suite
├── models/            # Model files (gitignored)
├── mobile_app/        # Flutter application
├── docs/              # Documentation
├── main.py            # Entry point
└── requirements.txt
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Dataset Preparation](docs/DATASET_PREPARATION.md)
- [Model Training](docs/TRAINING.md)
- [API Documentation](docs/API_DOCUMENTATION.md)
- [Raspberry Pi Deployment](docs/DEPLOYMENT.md)
- [Mobile App](docs/MOBILE_APP.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## Ethical Disclaimer

This system is designed for **legitimate security monitoring** of ATM areas.
It does **not** store personal identity data. Use in compliance with applicable
privacy laws. Intended for research and educational purposes.

## License

MIT — see [LICENSE](LICENSE).