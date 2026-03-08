"""
YOLOv8 object detector for ATM surveillance.

Detects the four custom classes (gun, knife, helmet, mask) plus the COCO
*person* class using a lightweight YOLOv8-nano model.

Detection classes
-----------------
Custom model:
  0 – gun
  1 – knife
  2 – helmet
  3 – mask

COCO person class ID: 0 (when using the default COCO model as a fallback).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.logger import get_logger

logger = get_logger(__name__)

# Human-readable labels for the custom model classes
CUSTOM_CLASS_NAMES: Dict[int, str] = {
    0: "gun",
    1: "knife",
    2: "helmet",
    3: "mask",
}

# COCO class ID for person
COCO_PERSON_CLASS_ID = 0


@dataclass
class Detection:
    """Single object detection result."""

    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    is_person: bool = False
    metadata: Dict = field(default_factory=dict)


class Detector:
    """
    YOLOv8 object detector wrapping Ultralytics inference.

    Uses a custom model for weapon/concealment detection and optionally
    a second COCO-pretrained model for person detection.
    """

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        person_model_path: Optional[str] = None,
        person_confidence_threshold: float = 0.5,
        device: str = "cpu",
    ) -> None:
        """
        Initialise the detector.

        Args:
            model_path: Path to the custom YOLOv8 .pt or .onnx model.
            confidence_threshold: Minimum confidence for custom detections.
            iou_threshold: IoU threshold for NMS.
            person_model_path: Optional path to a COCO model for person detection.
                               If *None*, person detection falls back to the custom
                               model if it includes person, or is skipped.
            person_confidence_threshold: Minimum confidence for person detections.
            device: Inference device, e.g. "cpu" or "0" (GPU).
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.person_model_path = person_model_path
        self.person_confidence_threshold = person_confidence_threshold
        self.device = device

        self._model = None
        self._person_model = None

        self._load_models()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Run inference on a single frame.

        Args:
            frame: BGR image as a NumPy array.

        Returns:
            List of :class:`Detection` instances.
        """
        detections: List[Detection] = []

        if self._model is None:
            logger.error("Custom model not loaded — skipping detection.")
            return detections

        try:
            results = self._model(
                frame,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                verbose=False,
            )
            detections.extend(self._parse_results(results, is_person_model=False))
        except Exception as exc:  # noqa: BLE001
            logger.error("Inference error (custom model): %s", exc)

        # Person detection from separate model
        if self._person_model is not None:
            try:
                person_results = self._person_model(
                    frame,
                    conf=self.person_confidence_threshold,
                    iou=self.iou_threshold,
                    verbose=False,
                    classes=[COCO_PERSON_CLASS_ID],
                )
                detections.extend(
                    self._parse_results(person_results, is_person_model=True)
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("Inference error (person model): %s", exc)

        return detections

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_models(self) -> None:
        """Load YOLOv8 model(s), logging errors without raising."""
        try:
            from ultralytics import YOLO  # type: ignore[import]

            self._model = YOLO(self.model_path)
            self._model.to(self.device)
            logger.info("Custom model loaded from %s", self.model_path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load custom model from %s: %s", self.model_path, exc)

        if self.person_model_path:
            try:
                from ultralytics import YOLO  # type: ignore[import]

                self._person_model = YOLO(self.person_model_path)
                self._person_model.to(self.device)
                logger.info("Person model loaded from %s", self.person_model_path)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Failed to load person model from %s: %s",
                    self.person_model_path,
                    exc,
                )

    def _parse_results(
        self, results, *, is_person_model: bool
    ) -> List[Detection]:
        """
        Convert Ultralytics *Results* objects to :class:`Detection` instances.

        Args:
            results: Ultralytics Results list returned by model inference.
            is_person_model: Whether the results come from the COCO person model.

        Returns:
            List of Detection instances.
        """
        detections: List[Detection] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]

                if is_person_model:
                    class_name = "person"
                    is_person = True
                else:
                    class_name = CUSTOM_CLASS_NAMES.get(class_id, f"class_{class_id}")
                    is_person = False

                detections.append(
                    Detection(
                        class_id=class_id,
                        class_name=class_name,
                        confidence=confidence,
                        bbox=(x1, y1, x2, y2),
                        is_person=is_person,
                    )
                )
        return detections
