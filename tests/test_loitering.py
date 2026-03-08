"""Unit tests for src/loitering_detector.py."""

from __future__ import annotations

import time

import pytest

from src.loitering_detector import LoiterEvent, LoiteringDetector
from src.tracker import Track
from src.zones import Zone, ZoneManager


def _make_zone_manager():
    zone = Zone(
        name="test_zone",
        polygon=[(0, 0), (500, 0), (500, 500), (0, 500)],
        zone_type="restricted",
    )
    zm = ZoneManager([zone])
    return zm


def _make_track(track_id=1, bbox=(100, 100, 200, 400), first_seen=None):
    now = time.time()
    return Track(
        track_id=track_id,
        bbox=bbox,
        confidence=0.9,
        first_seen=first_seen if first_seen is not None else now,
        last_seen=now,
    )


class TestLoiteringDetector:
    def setup_method(self):
        self.zm = _make_zone_manager()
        self.detector = LoiteringDetector(
            zone_manager=self.zm,
            threshold_seconds=5.0,  # low for testing
            cooldown_seconds=2.0,
        )

    def test_no_event_below_threshold(self):
        track = _make_track(first_seen=time.time())
        events = self.detector.update({1: track})
        assert events == []

    def test_event_above_threshold(self):
        # Simulate track that entered the zone 10 seconds ago
        old_time = time.time() - 10
        track = _make_track(first_seen=old_time)
        # Manually prime the entry time
        self.detector._zone_entry_times[1] = {"test_zone": old_time}
        events = self.detector.update({1: track})
        assert len(events) == 1
        assert events[0].track_id == 1
        assert events[0].zone_name == "test_zone"
        assert events[0].duration >= 10

    def test_cooldown_prevents_duplicate(self):
        old_time = time.time() - 10
        track = _make_track(first_seen=old_time)
        self.detector._zone_entry_times[1] = {"test_zone": old_time}
        events1 = self.detector.update({1: track})
        assert len(events1) == 1
        # Second call within cooldown should not fire again
        events2 = self.detector.update({1: track})
        assert len(events2) == 0

    def test_track_leaves_zone(self):
        """Person outside zone — no entry time recorded."""
        # bbox outside zone (0-500 x 0-500) → foot at (150, 600)
        track = _make_track(bbox=(100, 500, 200, 600))
        events = self.detector.update({1: track})
        assert events == []
        assert 1 not in self.detector._zone_entry_times

    def test_duration_returns_zero_not_in_zone(self):
        dur = self.detector.get_duration(track_id=99, zone_name="test_zone")
        assert dur == 0.0

    def test_reset_clears_state(self):
        old_time = time.time() - 10
        self.detector._zone_entry_times[1] = {"test_zone": old_time}
        self.detector.reset()
        assert self.detector._zone_entry_times == {}
