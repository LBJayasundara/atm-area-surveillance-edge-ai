"""
Main entry point for the ATM Area Surveillance Edge AI system.

Integrates all modules into a real-time detection pipeline:

    VideoStream → Detector → Tracker → LoiteringDetector
        → ActivityAnalyzer → AlertManager → APIServer
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time

import yaml

from src.activity_analyzer import ActivityAnalyzer
from src.alert_manager import AlertManager
from src.api_server import APIServer
from src.detector import Detector
from src.logger import get_logger
from src.loitering_detector import LoiteringDetector
from src.optimization import FrameQueue, FrameRateController, PerformanceMonitor
from src.tracker import Tracker
from src.video_stream import VideoStream
from src.zones import ZoneManager

try:
    from src.firebase_client import FirebaseClient
except ImportError:  # pragma: no cover
    FirebaseClient = None  # type: ignore[assignment,misc]

logger = get_logger(__name__)

_RUNNING = True


def _signal_handler(signum: int, frame) -> None:  # noqa: ANN001
    global _RUNNING
    logger.info("Shutdown signal received (%d). Stopping…", signum)
    _RUNNING = False


def load_config(config_path: str) -> dict:
    """Load YAML configuration file.

    Args:
        config_path: Path to the YAML config.

    Returns:
        Parsed configuration dictionary.
    """
    with open(config_path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def build_zone_manager(config: dict) -> ZoneManager:
    """Initialise ZoneManager from config or zones JSON file.

    Args:
        config: Top-level configuration dictionary.

    Returns:
        Populated :class:`~src.zones.ZoneManager`.
    """
    zones_json = config.get("zones", {}).get("json_path", "config/zones.json")
    if os.path.isfile(zones_json):
        return ZoneManager.from_json(zones_json)
    logger.warning("zones.json not found at %s — starting with no zones.", zones_json)
    return ZoneManager()


def run(config_path: str = "config/config.yaml") -> None:
    """
    Run the main detection pipeline.

    Args:
        config_path: Path to the YAML configuration file.
    """
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    cfg = load_config(config_path)
    cam_cfg = cfg.get("camera", {})
    model_cfg = cfg.get("model", {})
    api_cfg = cfg.get("api", {})
    detection_cfg = cfg.get("detection", {})
    logging_cfg = cfg.get("logging", {})

    logger.info("Starting ATM Surveillance system…")

    # --- Zones ---
    zone_manager = build_zone_manager(cfg)

    # --- Video stream ---
    stream = VideoStream(
        rtsp_url=cam_cfg.get("rtsp_url", "rtsp://192.168.1.100:554/stream"),
        width=cam_cfg.get("width", 1280),
        height=cam_cfg.get("height", 720),
        fps=cam_cfg.get("fps", 15),
    )
    stream.start()

    # --- Detector ---
    detector = Detector(
        model_path=model_cfg.get("path", "models/atm_surveillance.pt"),
        confidence_threshold=model_cfg.get("confidence_threshold", 0.5),
        iou_threshold=model_cfg.get("iou_threshold", 0.45),
        person_model_path=model_cfg.get("person_model_path"),
        person_confidence_threshold=model_cfg.get("person_confidence_threshold", 0.5),
        device=model_cfg.get("device", "cpu"),
    )

    # --- Tracker ---
    tracker = Tracker(
        iou_threshold=detection_cfg.get("tracker_iou_threshold", 0.3),
        max_age=detection_cfg.get("tracker_max_age", 30),
    )

    # --- Loitering detector ---
    loiter_detector = LoiteringDetector(
        zone_manager=zone_manager,
        threshold_seconds=detection_cfg.get("loitering_threshold_seconds", 120),
        cooldown_seconds=detection_cfg.get("loitering_cooldown_seconds", 60),
    )

    # --- Activity analyser ---
    analyzer = ActivityAnalyzer(
        zone_manager=zone_manager,
        alert_cooldown_seconds=detection_cfg.get("alert_cooldown_seconds", 30),
        weapon_confidence_threshold=detection_cfg.get("weapon_confidence_threshold", 0.6),
        concealment_confidence_threshold=detection_cfg.get(
            "concealment_confidence_threshold", 0.65
        ),
    )

    # --- Alert manager ---
    firebase_cfg = cfg.get("firebase", {})
    firebase_client = None
    if FirebaseClient is not None and firebase_cfg.get("credentials_path"):
        firebase_client = FirebaseClient(
            credentials_path=firebase_cfg.get("credentials_path", ""),
            storage_bucket=firebase_cfg.get("storage_bucket", ""),
            collection_name=firebase_cfg.get("collection_name", "alerts"),
            fcm_topic=firebase_cfg.get("fcm_topic", "atm_alerts"),
        )
        if firebase_client.available:
            logger.info("Firebase integration active.")
        else:
            logger.warning("Firebase configured but unavailable — alerts stored locally only.")
            firebase_client = None

    alert_manager = AlertManager(
        db_path=cfg.get("database", {}).get("path", "database/alerts.db"),
        snapshot_dir=cfg.get("snapshots", {}).get("dir", "snapshots"),
        camera_id=cam_cfg.get("camera_id", "cam_01"),
        location=cam_cfg.get("location", "ATM Entrance"),
        firebase_client=firebase_client,
    )

    # --- API server ---
    api = APIServer(
        alert_manager=alert_manager,
        zone_manager=zone_manager,
        host=api_cfg.get("host", "0.0.0.0"),
        port=api_cfg.get("port", 5000),
        auth_token=api_cfg.get("auth_token"),
    )
    api.start()

    # --- Performance helpers ---
    frc = FrameRateController(target_fps=cfg.get("performance", {}).get("target_fps", 8))
    frame_queue = FrameQueue(maxsize=2)
    perf = PerformanceMonitor(window=30)

    logger.info("Pipeline ready — waiting for frames…")

    global _RUNNING
    stats_interval = 30  # print stats every N seconds
    last_stats_time = time.time()

    while _RUNNING:
        ret, frame = stream.read()
        if not ret:
            time.sleep(0.05)
            continue

        if not frc.should_process():
            continue

        t_start = time.monotonic()

        # Detection
        detections = detector.detect(frame)

        # Person tracking
        person_dets = [d for d in detections if d.is_person]
        tracks = tracker.update(person_dets, frame)

        # Loitering
        loiter_events = loiter_detector.update(tracks)

        # Activity analysis
        events = analyzer.analyze(detections, loiter_events)

        # Alert generation
        for event in events:
            alert_manager.create_alert(event, frame)

        t_end = time.monotonic()
        perf.record_frame((t_end - t_start) * 1000)

        # Periodic stats logging
        now = time.time()
        if now - last_stats_time >= stats_interval:
            summary = perf.summary()
            logger.info(
                "Performance — FPS: %.1f | Latency: %.1f ms | Memory: %.0f MB",
                summary["fps"],
                summary["avg_latency_ms"],
                summary["memory_mb"],
            )
            last_stats_time = now

    # Graceful shutdown
    stream.stop()
    logger.info("ATM Surveillance system stopped.")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="ATM Area Surveillance Edge AI")
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to configuration YAML file (default: config/config.yaml)",
    )
    args = parser.parse_args()
    run(config_path=args.config)


if __name__ == "__main__":
    main()
