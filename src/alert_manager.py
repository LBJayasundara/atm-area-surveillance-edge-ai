"""
Alert manager — generates alert records, captures snapshots, and persists
them to an SQLite database.

Alert JSON format
-----------------
{
    "id": "alert_20260308_143218_001",
    "activity": "Weapon Detected",
    "activity_type": "weapon",
    "detected_object": "gun",
    "confidence": 0.91,
    "timestamp": "2026-03-08T14:32:18Z",
    "location": "ATM Entrance",
    "image": "snapshot_143218.jpg",
    "acknowledged": false,
    "metadata": {
        "person_id": 42,
        "bounding_box": [120, 230, 180, 310],
        "zone": "restricted_atm_zone",
        "camera_id": "cam_01"
    }
}
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from src.activity_analyzer import ActivityEvent
from src.logger import get_logger

logger = get_logger(__name__)


class AlertManager:
    """
    Creates, persists, and serves alert records.

    Responsibilities:
    - Assign unique IDs to alerts
    - Save snapshot images to disk (with bounding-box overlay)
    - Persist alerts to SQLite
    - Acknowledge alerts
    - Serve alerts to the REST API layer
    """

    def __init__(
        self,
        db_path: str = "database/alerts.db",
        snapshot_dir: str = "snapshots",
        camera_id: str = "cam_01",
        location: str = "ATM Entrance",
    ) -> None:
        """
        Initialise the alert manager.

        Args:
            db_path: Path to the SQLite database file.
            snapshot_dir: Directory where snapshot images are saved.
            camera_id: Identifier for the camera producing the feed.
            location: Human-readable location label for alerts.
        """
        self.db_path = db_path
        self.snapshot_dir = snapshot_dir
        self.camera_id = camera_id
        self.location = location

        self._alert_counter = 0

        os.makedirs(snapshot_dir, exist_ok=True)
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def create_alert(
        self,
        event: ActivityEvent,
        frame: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        Create an alert record for *event*, optionally saving a snapshot.

        Args:
            event: :class:`~src.activity_analyzer.ActivityEvent` to record.
            frame: Optional current video frame for snapshot capture.

        Returns:
            Alert dictionary following the project JSON schema.
        """
        self._alert_counter += 1
        ts = datetime.fromtimestamp(event.timestamp, tz=timezone.utc)
        alert_id = f"alert_{ts.strftime('%Y%m%d_%H%M%S')}_{self._alert_counter:03d}"
        timestamp_str = ts.strftime("%Y-%m-%dT%H:%M:%SZ")

        image_filename = ""
        if frame is not None:
            image_filename = self._save_snapshot(frame, event, ts)

        alert: Dict[str, Any] = {
            "id": alert_id,
            "activity": event.activity,
            "activity_type": event.activity_type,
            "detected_object": event.detected_object,
            "confidence": round(event.confidence, 4),
            "timestamp": timestamp_str,
            "location": self.location,
            "image": image_filename,
            "acknowledged": False,
            "metadata": {
                "person_id": event.person_id,
                "bounding_box": list(event.bbox),
                "zone": event.zone_name,
                "camera_id": self.camera_id,
                **event.metadata,
            },
        }

        self._persist_alert(alert)
        logger.info("Alert created: %s (%s)", alert_id, event.activity)
        return alert

    def get_alerts(
        self,
        limit: int = 50,
        offset: int = 0,
        activity_type: Optional[str] = None,
        acknowledged: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve alerts from the database.

        Args:
            limit: Maximum number of records to return.
            offset: Pagination offset.
            activity_type: Optional filter, e.g. "weapon".
            acknowledged: Optional filter by acknowledgement status.

        Returns:
            List of alert dictionaries, newest first.
        """
        query = "SELECT data FROM alerts WHERE 1=1"
        params: List[Any] = []

        if activity_type:
            query += " AND activity_type = ?"
            params.append(activity_type)
        if acknowledged is not None:
            query += " AND acknowledged = ?"
            params.append(1 if acknowledged else 0)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(query, params).fetchall()
            return [json.loads(row[0]) for row in rows]
        except sqlite3.Error as exc:
            logger.error("DB query error: %s", exc)
            return []

    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Mark an alert as acknowledged.

        Args:
            alert_id: Unique alert identifier.

        Returns:
            True on success, False if the alert was not found.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT data FROM alerts WHERE alert_id = ?", (alert_id,)
                )
                row = cursor.fetchone()
                if row is None:
                    return False
                alert = json.loads(row[0])
                alert["acknowledged"] = True
                conn.execute(
                    "UPDATE alerts SET acknowledged = 1, data = ? WHERE alert_id = ?",
                    (json.dumps(alert), alert_id),
                )
            logger.info("Alert %s acknowledged.", alert_id)
            return True
        except sqlite3.Error as exc:
            logger.error("DB acknowledge error: %s", exc)
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Return summary statistics.

        Returns:
            Dictionary with total_alerts, unacknowledged_alerts, and
            counts broken down by activity_type.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
                unacked = conn.execute(
                    "SELECT COUNT(*) FROM alerts WHERE acknowledged = 0"
                ).fetchone()[0]
                by_type = conn.execute(
                    "SELECT activity_type, COUNT(*) FROM alerts GROUP BY activity_type"
                ).fetchall()
            return {
                "total_alerts": total,
                "unacknowledged_alerts": unacked,
                "by_activity_type": {row[0]: row[1] for row in by_type},
            }
        except sqlite3.Error as exc:
            logger.error("DB stats error: %s", exc)
            return {}

    def snapshot_path(self, filename: str) -> Optional[str]:
        """
        Resolve the full path to a snapshot image.

        Args:
            filename: Image filename (basename only).

        Returns:
            Absolute path if the file exists, otherwise None.
        """
        # Sanitise filename to prevent path traversal
        safe_name = Path(filename).name
        full_path = os.path.join(self.snapshot_dir, safe_name)
        return full_path if os.path.isfile(full_path) else None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Create the alerts table if it does not exist."""
        create_sql = """
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id TEXT UNIQUE NOT NULL,
            activity_type TEXT NOT NULL,
            acknowledged INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL,
            data TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_alerts_activity_type ON alerts(activity_type);
        CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alerts(acknowledged);
        CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(create_sql)
        except sqlite3.Error as exc:
            logger.error("DB initialisation error: %s", exc)

    def _persist_alert(self, alert: Dict[str, Any]) -> None:
        """Insert an alert record into the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO alerts
                        (alert_id, activity_type, acknowledged, created_at, data)
                    VALUES (?, ?, 0, ?, ?)
                    """,
                    (
                        alert["id"],
                        alert["activity_type"],
                        time.time(),
                        json.dumps(alert),
                    ),
                )
        except sqlite3.Error as exc:
            logger.error("DB insert error: %s", exc)

    def _save_snapshot(
        self,
        frame: np.ndarray,
        event: ActivityEvent,
        ts: datetime,
    ) -> str:
        """
        Save a snapshot image with bounding-box overlay.

        Args:
            frame: BGR video frame.
            event: Activity event with bbox information.
            ts: Timestamp for the filename.

        Returns:
            Basename of the saved image file.
        """
        img = frame.copy()
        x1, y1, x2, y2 = event.bbox
        color = (0, 0, 255) if event.activity_type == "weapon" else (0, 165, 255)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        label = f"{event.detected_object} {event.confidence:.2f}"
        cv2.putText(
            img,
            label,
            (x1, max(y1 - 8, 0)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )

        filename = f"snapshot_{ts.strftime('%Y%m%d_%H%M%S')}_{self._alert_counter:03d}.jpg"
        path = os.path.join(self.snapshot_dir, filename)
        try:
            cv2.imwrite(path, img)
            logger.debug("Snapshot saved: %s", path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to save snapshot %s: %s", path, exc)
            return ""
        return filename
