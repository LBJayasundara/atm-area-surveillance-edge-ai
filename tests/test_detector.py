"""Unit tests for src/detector.py."""

from __future__ import annotations

import pytest

from src.detector import CUSTOM_CLASS_NAMES, Detection, Detector


class TestDetection:
    def test_creation(self):
        d = Detection(
            class_id=0,
            class_name="gun",
            confidence=0.92,
            bbox=(10, 20, 100, 150),
            is_person=False,
        )
        assert d.class_id == 0
        assert d.class_name == "gun"
        assert d.confidence == pytest.approx(0.92)
        assert d.bbox == (10, 20, 100, 150)
        assert not d.is_person

    def test_person_flag(self):
        d = Detection(
            class_id=0,
            class_name="person",
            confidence=0.85,
            bbox=(0, 0, 50, 100),
            is_person=True,
        )
        assert d.is_person


class TestCustomClassNames:
    def test_all_four_classes_defined(self):
        assert CUSTOM_CLASS_NAMES[0] == "gun"
        assert CUSTOM_CLASS_NAMES[1] == "knife"
        assert CUSTOM_CLASS_NAMES[2] == "helmet"
        assert CUSTOM_CLASS_NAMES[3] == "mask"

    def test_exactly_four_classes(self):
        assert len(CUSTOM_CLASS_NAMES) == 4


class TestDetectorInit:
    """Test Detector initialises gracefully even when model file is absent."""

    def test_init_missing_model_no_crash(self):
        """Detector should log an error but not raise when model file is missing."""
        det = Detector(model_path="/nonexistent/model.pt")
        assert det._model is None

    def test_detect_without_model_returns_empty(self):
        import numpy as np

        det = Detector(model_path="/nonexistent/model.pt")
        frame = np.zeros((480, 640, 3), dtype="uint8")
        result = det.detect(frame)
        assert result == []

    def test_parse_results_is_private(self):
        det = Detector(model_path="/nonexistent/model.pt")
        assert hasattr(det, "_parse_results")
