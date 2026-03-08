"""
Polygon-based zone management for ATM surveillance.

Zones define restricted areas (ATM entrance, queue area, etc.) within
the camera field of view. Each zone is described by a polygon of pixel
coordinates. Points-in-polygon tests are used to determine whether a
person is inside a zone.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Zone:
    """A named polygonal region of interest within a camera frame."""

    name: str
    polygon: List[Tuple[int, int]]  # ordered list of (x, y) vertices
    zone_type: str = "restricted"  # "restricted" | "queue" | "entrance"
    description: str = ""

    def __post_init__(self) -> None:
        if len(self.polygon) < 3:
            raise ValueError(
                f"Zone '{self.name}' must have at least 3 vertices, "
                f"got {len(self.polygon)}."
            )

    def contains_point(self, point: Tuple[int, int]) -> bool:
        """
        Test whether *point* lies inside or on the boundary of this zone.

        Uses the ray-casting algorithm (OpenCV point-in-polygon test).

        Args:
            point: (x, y) pixel coordinate.

        Returns:
            True when the point is inside or on the polygon boundary.
        """
        pts = np.array(self.polygon, dtype=np.float32).reshape((-1, 1, 2))
        result = int(
            __import__("cv2").pointPolygonTest(pts, (float(point[0]), float(point[1])), False)
        )
        return result >= 0

    def contains_bbox(self, bbox: Tuple[int, int, int, int]) -> bool:
        """
        Return True if the bottom-centre point of *bbox* is inside the zone.

        Using the foot of the bounding box approximates the person's position
        on the ground plane, which is more robust than using the full bbox.

        Args:
            bbox: (x1, y1, x2, y2) bounding box.

        Returns:
            True when the person is considered to be standing in this zone.
        """
        x1, y1, x2, y2 = bbox
        foot_x = (x1 + x2) // 2
        foot_y = y2  # bottom of the bounding box
        return self.contains_point((foot_x, foot_y))

    @property
    def np_polygon(self) -> np.ndarray:
        """Polygon as an ``(N, 1, 2)`` NumPy array suitable for OpenCV."""
        return np.array(self.polygon, dtype=np.int32).reshape((-1, 1, 2))


class ZoneManager:
    """
    Manages multiple named zones loaded from config or JSON file.
    """

    def __init__(self, zones: Optional[List[Zone]] = None) -> None:
        self._zones: Dict[str, Zone] = {}
        if zones:
            for zone in zones:
                self.add_zone(zone)

    # ------------------------------------------------------------------
    # Zone management
    # ------------------------------------------------------------------

    def add_zone(self, zone: Zone) -> None:
        """Register a zone. Overwrites any existing zone with the same name."""
        self._zones[zone.name] = zone
        logger.debug("Zone '%s' registered (%d vertices).", zone.name, len(zone.polygon))

    def remove_zone(self, name: str) -> bool:
        """Remove a zone by name. Returns True if it existed."""
        if name in self._zones:
            del self._zones[name]
            return True
        return False

    def get_zone(self, name: str) -> Optional[Zone]:
        """Return a zone by name, or None if not found."""
        return self._zones.get(name)

    @property
    def zones(self) -> Dict[str, Zone]:
        """All registered zones."""
        return dict(self._zones)

    # ------------------------------------------------------------------
    # Point / bbox tests
    # ------------------------------------------------------------------

    def zones_containing_point(self, point: Tuple[int, int]) -> List[str]:
        """Return names of all zones that contain *point*."""
        return [name for name, zone in self._zones.items() if zone.contains_point(point)]

    def zones_containing_bbox(self, bbox: Tuple[int, int, int, int]) -> List[str]:
        """Return names of all zones whose ground plane contains *bbox*."""
        return [name for name, zone in self._zones.items() if zone.contains_bbox(bbox)]

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_json(cls, path: str) -> "ZoneManager":
        """
        Load zones from a JSON file.

        Expected format::

            [
              {
                "name": "restricted_atm_zone",
                "zone_type": "restricted",
                "description": "Main ATM alcove",
                "polygon": [[100, 200], [400, 200], [400, 500], [100, 500]]
              },
              ...
            ]

        Args:
            path: File system path to the JSON file.

        Returns:
            A :class:`ZoneManager` populated with the parsed zones.
        """
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        zones = []
        for entry in data:
            try:
                zone = Zone(
                    name=entry["name"],
                    polygon=[tuple(pt) for pt in entry["polygon"]],  # type: ignore[misc]
                    zone_type=entry.get("zone_type", "restricted"),
                    description=entry.get("description", ""),
                )
                zones.append(zone)
            except (KeyError, ValueError) as exc:
                logger.error("Skipping invalid zone entry %s: %s", entry, exc)
        manager = cls(zones)
        logger.info("Loaded %d zone(s) from %s", len(zones), path)
        return manager

    def to_json(self, path: str) -> None:
        """
        Persist current zones to a JSON file.

        Args:
            path: Destination file path.
        """
        data = [
            {
                "name": zone.name,
                "zone_type": zone.zone_type,
                "description": zone.description,
                "polygon": zone.polygon,
            }
            for zone in self._zones.values()
        ]
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("Zones saved to %s", path)
