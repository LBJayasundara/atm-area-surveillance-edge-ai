"""
Loitering detection module.

Tracks how long each person has been present inside restricted zones and
raises a loitering event once the configurable threshold (default 120 s)
is exceeded.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from src.logger import get_logger
from src.tracker import Track
from src.zones import ZoneManager

logger = get_logger(__name__)


@dataclass
class LoiterEvent:
    """Encapsulates a single loitering detection event."""

    track_id: int
    zone_name: str
    duration: float  # seconds spent in zone
    bbox: tuple
    timestamp: float = field(default_factory=time.time)


class LoiteringDetector:
    """
    Monitors zone occupancy per person track and detects loitering.

    A person is considered *loitering* when they have been continuously
    present in a zone for longer than ``threshold_seconds``.
    """

    def __init__(
        self,
        zone_manager: ZoneManager,
        threshold_seconds: float = 120.0,
        zone_names: Optional[List[str]] = None,
        cooldown_seconds: float = 60.0,
    ) -> None:
        """
        Initialise the loitering detector.

        Args:
            zone_manager: :class:`~src.zones.ZoneManager` with registered zones.
            threshold_seconds: Duration (s) before loitering is flagged.
            zone_names: Restrict monitoring to these zone names. When *None*
                        all zones are monitored.
            cooldown_seconds: Minimum time (s) between repeated loitering
                              alerts for the same (track, zone) pair.
        """
        self.zone_manager = zone_manager
        self.threshold_seconds = threshold_seconds
        self.zone_names = set(zone_names) if zone_names else None
        self.cooldown_seconds = cooldown_seconds

        # track_id → {zone_name → entry_timestamp}
        self._zone_entry_times: Dict[int, Dict[str, float]] = {}
        # track_id → {zone_name → last_alert_timestamp}
        self._last_alert_times: Dict[int, Dict[str, float]] = {}

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def update(self, tracks: Dict[int, Track]) -> List[LoiterEvent]:
        """
        Update occupancy state and return new loitering events.

        Args:
            tracks: Active tracks from :class:`~src.tracker.Tracker`.

        Returns:
            List of :class:`LoiterEvent` for all newly triggered loitering
            detections this frame.
        """
        current_time = time.time()
        events: List[LoiterEvent] = []

        active_track_ids = set(tracks.keys())

        # Remove stale state for disappeared tracks
        for tid in list(self._zone_entry_times.keys()):
            if tid not in active_track_ids:
                del self._zone_entry_times[tid]

        for track_id, track in tracks.items():
            occupied_zones = self.zone_manager.zones_containing_bbox(track.bbox)
            monitored = self._monitored_zones(occupied_zones)

            # Only initialise state for tracks that are (or were) in a zone
            if monitored or track_id in self._zone_entry_times:
                entry_map = self._zone_entry_times.setdefault(track_id, {})
            else:
                entry_map = {}

            # Update entry times
            for zone_name in monitored:
                if zone_name not in entry_map:
                    entry_map[zone_name] = current_time
                    logger.debug(
                        "Track %d entered zone '%s'.", track_id, zone_name
                    )

            # Remove zones the person has left
            for zone_name in list(entry_map.keys()):
                if zone_name not in monitored:
                    logger.debug(
                        "Track %d left zone '%s'.", track_id, zone_name
                    )
                    del entry_map[zone_name]

            # Check threshold
            for zone_name, entry_time in entry_map.items():
                duration = current_time - entry_time
                if duration >= self.threshold_seconds:
                    if self._can_alert(track_id, zone_name, current_time):
                        events.append(
                            LoiterEvent(
                                track_id=track_id,
                                zone_name=zone_name,
                                duration=duration,
                                bbox=track.bbox,
                                timestamp=current_time,
                            )
                        )
                        self._record_alert(track_id, zone_name, current_time)
                        logger.info(
                            "Loitering detected: track %d in zone '%s' for %.1f s.",
                            track_id,
                            zone_name,
                            duration,
                        )

        return events

    def get_duration(self, track_id: int, zone_name: str) -> float:
        """
        Return seconds a track has been in *zone_name*, or 0 if not present.

        Args:
            track_id: Person track identifier.
            zone_name: Name of the zone.

        Returns:
            Elapsed seconds, or 0.0 if the track is not in the zone.
        """
        entry_map = self._zone_entry_times.get(track_id, {})
        if zone_name not in entry_map:
            return 0.0
        return time.time() - entry_map[zone_name]

    def reset(self) -> None:
        """Clear all internal state."""
        self._zone_entry_times.clear()
        self._last_alert_times.clear()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _monitored_zones(self, zone_names: List[str]) -> Set[str]:
        """Filter zone names to only those being monitored."""
        if self.zone_names is None:
            return set(zone_names)
        return set(zone_names) & self.zone_names

    def _can_alert(self, track_id: int, zone_name: str, current_time: float) -> bool:
        """Return True if the cooldown period has elapsed since the last alert."""
        last = self._last_alert_times.get(track_id, {}).get(zone_name, 0.0)
        return (current_time - last) >= self.cooldown_seconds

    def _record_alert(self, track_id: int, zone_name: str, current_time: float) -> None:
        """Record the timestamp of the latest alert for (track_id, zone_name)."""
        self._last_alert_times.setdefault(track_id, {})[zone_name] = current_time
