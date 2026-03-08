"""Unit tests for src/tracker.py."""

from __future__ import annotations

import time

import pytest

from src.detector import Detection
from src.tracker import Track, Tracker


def _make_person(bbox, conf=0.8):
    return Detection(
        class_id=0,
        class_name="person",
        confidence=conf,
        bbox=bbox,
        is_person=True,
    )


class TestTrack:
    def test_duration(self):
        t0 = time.time() - 10
        track = Track(track_id=1, bbox=(0, 0, 50, 100), confidence=0.9, first_seen=t0)
        assert track.duration >= 10

    def test_center(self):
        track = Track(track_id=1, bbox=(0, 0, 100, 200), confidence=0.9)
        assert track.center == (50, 100)


class TestTrackerFallback:
    """Tests for the IoU-based fallback tracker (no YOLO model)."""

    def setup_method(self):
        self.tracker = Tracker(iou_threshold=0.3)

    def test_new_detection_creates_track(self):
        dets = [_make_person((10, 10, 100, 200))]
        tracks = self.tracker.update(dets)
        assert len(tracks) == 1

    def test_same_person_keeps_same_id(self):
        dets = [_make_person((10, 10, 100, 200))]
        tracks1 = self.tracker.update(dets)
        tid1 = list(tracks1.keys())[0]

        # Slightly moved bounding box — should match existing track
        dets2 = [_make_person((12, 12, 102, 202))]
        tracks2 = self.tracker.update(dets2)
        tid2 = list(tracks2.keys())[0]

        assert tid1 == tid2

    def test_two_people_two_tracks(self):
        dets = [
            _make_person((0, 0, 50, 100)),
            _make_person((200, 200, 250, 300)),
        ]
        tracks = self.tracker.update(dets)
        assert len(tracks) == 2

    def test_reset_clears_state(self):
        dets = [_make_person((10, 10, 60, 110))]
        self.tracker.update(dets)
        self.tracker.reset()
        assert len(self.tracker.active_tracks) == 0
        assert self.tracker._next_id == 1

    def test_iou_zero_for_non_overlapping(self):
        iou = Tracker._iou((0, 0, 10, 10), (20, 20, 30, 30))
        assert iou == 0.0

    def test_iou_one_for_identical(self):
        iou = Tracker._iou((0, 0, 100, 100), (0, 0, 100, 100))
        assert iou == pytest.approx(1.0)

    def test_iou_partial_overlap(self):
        # Two boxes sharing a 50x100 area
        iou = Tracker._iou((0, 0, 100, 100), (50, 0, 150, 100))
        # intersection = 50*100=5000, union = 2*10000 - 5000 = 15000
        assert iou == pytest.approx(5000 / 15000, rel=1e-3)
