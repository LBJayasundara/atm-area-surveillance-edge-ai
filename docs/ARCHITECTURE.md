# System Architecture

## Overview

The ATM Area Surveillance system follows an **edge-first** design: all inference
runs on a Raspberry Pi 4 co-located with the camera. No video or images are
transmitted to the cloud — only compact JSON alert records and JPEG snapshots
are served via the local REST API.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Raspberry Pi 4                               │
│                                                                     │
│  ┌───────────────┐   ┌───────────────┐   ┌────────────────────┐    │
│  │  VideoStream  │──▶│   Detector    │──▶│     Tracker        │    │
│  │  (RTSP read) │   │  (YOLOv8 nano)│   │  (ByteTrack/IoU)   │    │
│  └───────────────┘   └───────────────┘   └────────┬───────────┘    │
│                                                    │ tracks         │
│  ┌──────────────────────────────────────────────┐ │                 │
│  │          LoiteringDetector                   │◀┘                 │
│  │   (zone occupancy × 120 s threshold)        │                   │
│  └───────────────────┬──────────────────────────┘                   │
│                      │ loiter events                                │
│  ┌───────────────────▼──────────────────────────┐                   │
│  │          ActivityAnalyzer                    │                   │
│  │  (weapon / concealment / loitering routing)  │                   │
│  └───────────────────┬──────────────────────────┘                   │
│                      │ activity events                              │
│  ┌───────────────────▼──────────────────────────┐                   │
│  │           AlertManager                       │                   │
│  │  (SQLite persistence, snapshot capture)      │                   │
│  └───────────────────┬──────────────────────────┘                   │
│                      │                                              │
│  ┌───────────────────▼──────────────────────────┐                   │
│  │            APIServer (Flask)                 │◀────── Flutter App│
│  │  GET /alerts  POST /acknowledge  GET /stats  │                   │
│  └──────────────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

1. **Capture** — `VideoStream` reads RTSP frames in a background thread.
2. **Detect** — `Detector` runs YOLOv8 nano inference each processed frame,
   returning a list of `Detection` objects (class, bbox, confidence).
3. **Track** — `Tracker` associates person detections across frames using
   ByteTrack (or an IoU fallback), maintaining a `Track` dictionary.
4. **Loitering** — `LoiteringDetector` checks each track's occupancy in
   restricted zones and fires a `LoiterEvent` after 120 s.
5. **Analyse** — `ActivityAnalyzer` applies confidence thresholds and
   cooldown filtering, producing `ActivityEvent` instances.
6. **Alert** — `AlertManager` assigns IDs, saves snapshots, and persists
   records in SQLite.
7. **Serve** — `APIServer` exposes the REST API for the Flutter app.

## Technology Choices

| Decision | Rationale |
|----------|-----------|
| YOLOv8 nano | Lightest model; ~50 ms inference on Raspberry Pi 4 |
| ByteTrack | Efficient, requires only bounding boxes (no ReID) |
| SQLite | Zero-configuration embedded DB; suitable for ≤ 10k alerts |
| Flask | Minimal overhead REST framework |
| Flutter | Cross-platform (Android + iOS) with a single codebase |
| RTSP + OpenCV | Industry standard; works with any IP camera |

## Threading Model

```
Main Thread
    │
    ├── VideoStream thread (background, daemon)
    │       └── writes latest frame to FrameQueue
    │
    ├── Main processing loop (main thread)
    │       └── reads frame → detect → track → loiter → analyze → alert
    │
    └── APIServer thread (background, daemon)
            └── serves Flask requests
```
