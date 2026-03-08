"""
Person tracker using ByteTrack-style multi-object tracking.

Wraps the Ultralytics built-in ByteTrack integration and provides a
simple dictionary of active person tracks keyed by integer track ID.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Track:
    """Represents a single tracked person."""

    track_id: int
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    active: bool = True

    @property
    def duration(self) -> float:
        """Time in seconds this track has been observed."""
        return self.last_seen - self.first_seen

    @property
    def center(self) -> Tuple[int, int]:
        """Centre point of the bounding box."""
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)


class Tracker:
    """
    Multi-object person tracker.

    Uses the Ultralytics ByteTrack integration when a YOLO model is
    provided, otherwise falls back to a lightweight IoU-based tracker
    suitable for testing without GPU / model files.
    """

    def __init__(
        self,
        model=None,
        iou_threshold: float = 0.3,
        max_age: int = 30,
        min_hits: int = 2,
    ) -> None:
        """
        Initialise the tracker.

        Args:
            model: Ultralytics YOLO model instance with ByteTrack support.
                   When *None* the fallback IoU tracker is used.
            iou_threshold: Minimum IoU for matching detections to existing tracks.
            max_age: Number of frames a track can be invisible before deletion.
            min_hits: Minimum consecutive hits before a track is confirmed.
        """
        self._model = model
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.min_hits = min_hits

        self._tracks: Dict[int, Track] = {}
        self._next_id = 1
        self._frame_number = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def update(
        self, person_detections: List, frame: Optional[np.ndarray] = None
    ) -> Dict[int, Track]:
        """
        Update tracker state with new person detections.

        Args:
            person_detections: List of :class:`~src.detector.Detection` objects
                               for which ``is_person`` is ``True``.
            frame: Current video frame (used by ByteTrack; can be *None*).

        Returns:
            Dictionary mapping track ID → :class:`Track` for all currently
            active tracks.
        """
        self._frame_number += 1
        current_time = time.time()

        if self._model is not None and frame is not None:
            return self._update_bytetrack(person_detections, frame, current_time)
        return self._update_iou(person_detections, current_time)

    @property
    def active_tracks(self) -> Dict[int, Track]:
        """All currently active tracks."""
        return {tid: t for tid, t in self._tracks.items() if t.active}

    def reset(self) -> None:
        """Clear all track state."""
        self._tracks.clear()
        self._next_id = 1
        self._frame_number = 0

    # ------------------------------------------------------------------
    # ByteTrack integration
    # ------------------------------------------------------------------

    def _update_bytetrack(
        self,
        person_detections: List,
        frame: np.ndarray,
        current_time: float,
    ) -> Dict[int, Track]:
        """Run Ultralytics ByteTrack and sync internal track dictionary."""
        try:
            results = self._model.track(
                frame,
                persist=True,
                tracker="bytetrack.yaml",
                classes=[0],  # COCO person
                verbose=False,
            )
            active_ids = set()
            if results and results[0].boxes is not None and results[0].boxes.id is not None:
                for box, track_id in zip(
                    results[0].boxes.xyxy.tolist(),
                    results[0].boxes.id.tolist(),
                ):
                    tid = int(track_id)
                    x1, y1, x2, y2 = [int(v) for v in box]
                    conf = float(results[0].boxes.conf[0].item())
                    active_ids.add(tid)
                    if tid in self._tracks:
                        self._tracks[tid].bbox = (x1, y1, x2, y2)
                        self._tracks[tid].last_seen = current_time
                        self._tracks[tid].active = True
                    else:
                        self._tracks[tid] = Track(
                            track_id=tid,
                            bbox=(x1, y1, x2, y2),
                            confidence=conf,
                            first_seen=current_time,
                            last_seen=current_time,
                        )

            # Mark tracks not seen this frame as inactive
            for tid, track in self._tracks.items():
                if tid not in active_ids:
                    track.active = False

        except Exception as exc:  # noqa: BLE001
            logger.error("ByteTrack update error: %s", exc)

        return self.active_tracks

    # ------------------------------------------------------------------
    # Fallback IoU tracker
    # ------------------------------------------------------------------

    def _update_iou(
        self,
        person_detections: List,
        current_time: float,
    ) -> Dict[int, Track]:
        """Simple IoU-based tracker used when no YOLO model is available."""
        new_bboxes = [d.bbox for d in person_detections]
        new_confs = [d.confidence for d in person_detections]

        active_ids = list(self._tracks.keys())
        matched_track_ids = set()
        matched_det_indices = set()

        # Match existing tracks to new detections
        for tid in active_ids:
            best_iou = self.iou_threshold
            best_det_idx = -1
            for di, bbox in enumerate(new_bboxes):
                if di in matched_det_indices:
                    continue
                iou_val = self._iou(self._tracks[tid].bbox, bbox)
                if iou_val > best_iou:
                    best_iou = iou_val
                    best_det_idx = di
            if best_det_idx >= 0:
                self._tracks[tid].bbox = new_bboxes[best_det_idx]
                self._tracks[tid].confidence = new_confs[best_det_idx]
                self._tracks[tid].last_seen = current_time
                self._tracks[tid].active = True
                matched_track_ids.add(tid)
                matched_det_indices.add(best_det_idx)
            else:
                age = current_time - self._tracks[tid].last_seen
                if age > self.max_age:
                    self._tracks[tid].active = False

        # Create new tracks for unmatched detections
        for di, bbox in enumerate(new_bboxes):
            if di not in matched_det_indices:
                new_tid = self._next_id
                self._next_id += 1
                self._tracks[new_tid] = Track(
                    track_id=new_tid,
                    bbox=bbox,
                    confidence=new_confs[di],
                    first_seen=current_time,
                    last_seen=current_time,
                )

        return self.active_tracks

    @staticmethod
    def _iou(
        box_a: Tuple[int, int, int, int], box_b: Tuple[int, int, int, int]
    ) -> float:
        """Compute Intersection-over-Union between two bounding boxes."""
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)

        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h

        area_a = (ax2 - ax1) * (ay2 - ay1)
        area_b = (bx2 - bx1) * (by2 - by1)
        union_area = area_a + area_b - inter_area

        if union_area <= 0:
            return 0.0
        return inter_area / union_area
