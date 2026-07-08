"""
phase1/zone_map.py
==================
Polygon-based zone assignment using bottom-center of bounding box.

Rules:
  - Assignment uses bottom-center point ONLY (never centroid, never area overlap).
  - Hysteresis: a zone transition is only CONFIRMED after the person has been
    in the new zone for HYSTERESIS_FRAMES consecutive frames.
  - This prevents oscillation when a person stands on a polygon boundary.
  - No business logic. Zone names are arbitrary strings.
"""

from __future__ import annotations
import json
import os
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


OUTSIDE = "OUTSIDE"
HYSTERESIS_FRAMES = 10   # frames a person must stay in new zone before transition fires


# ── Zone definition ────────────────────────────────────────────────────────────

class Zone:
    def __init__(self, name: str, polygon: List[List[int]], color: Tuple[int, int, int]):
        self.name = name
        self.color = tuple(color)           # BGR for OpenCV
        self.polygon = np.array(polygon, dtype=np.int32)

    def contains(self, point: Tuple[int, int]) -> bool:
        """Return True if point (x, y) is inside or on the boundary of this polygon."""
        result = cv2.pointPolygonTest(self.polygon, (float(point[0]), float(point[1])), False)
        return result >= 0


# ── Zone map ──────────────────────────────────────────────────────────────────

class ZoneMap:
    """
    Loads zone polygons from a JSON file and provides zone assignment
    with hysteresis debouncing.
    """

    def __init__(self, config_path: str, hysteresis: int = HYSTERESIS_FRAMES):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Zone config not found: {config_path}")

        with open(config_path) as f:
            raw = json.load(f)

        self.zones: List[Zone] = []
        for name, spec in raw.items():
            if name.startswith("_"):
                continue
            color = spec.get("color", [128, 128, 128])
            # Convert RGB → BGR for OpenCV
            bgr = (color[2], color[1], color[0])
            self.zones.append(Zone(name=spec.get("label", name), polygon=spec["polygon"], color=bgr))

        self.hysteresis = hysteresis

        # Per-person hysteresis state: {person_id: {"candidate": zone, "count": n}}
        self._pending: Dict[int, dict] = {}

        # Per-person confirmed current zone
        self._confirmed_zone: Dict[int, str] = {}

    def get_zone_for_point(self, point: Tuple[int, int]) -> str:
        """Return zone name for a point. OUTSIDE if not in any polygon."""
        for zone in self.zones:
            if zone.contains(point):
                return zone.name
        return OUTSIDE

    def assign(self, person_id: int, bottom_center: Tuple[int, int]) -> Tuple[str, Optional[str]]:
        """
        Assign zone with hysteresis.

        Returns
        -------
        (current_confirmed_zone, transition_from_zone_or_None)
            current_confirmed_zone : the stable zone after hysteresis
            transition_from_zone   : the previous zone if a transition just fired, else None
        """
        raw_zone = self.get_zone_for_point(bottom_center)
        confirmed = self._confirmed_zone.get(person_id, OUTSIDE)

        if raw_zone == confirmed:
            # Still in same zone — clear any pending candidate
            self._pending.pop(person_id, None)
            return confirmed, None

        # In a different zone than confirmed — start or continue hysteresis
        pending = self._pending.get(person_id)
        if pending is None or pending["candidate"] != raw_zone:
            # New candidate zone — restart count
            self._pending[person_id] = {"candidate": raw_zone, "count": 1}
            return confirmed, None
        else:
            pending["count"] += 1
            if pending["count"] >= self.hysteresis:
                # Hysteresis satisfied — transition confirmed
                prev_zone = confirmed
                self._confirmed_zone[person_id] = raw_zone
                self._pending.pop(person_id, None)
                return raw_zone, prev_zone
            return confirmed, None

    def initialize_person(self, person_id: int, bottom_center: Tuple[int, int]) -> str:
        """
        Initialize a new person immediately (no hysteresis for first appearance).
        Returns their initial zone.
        """
        zone = self.get_zone_for_point(bottom_center)
        self._confirmed_zone[person_id] = zone
        self._pending.pop(person_id, None)
        return zone

    def remove_person(self, person_id: int):
        """Clean up state when a person's track ends."""
        self._confirmed_zone.pop(person_id, None)
        self._pending.pop(person_id, None)

    def current_zone(self, person_id: int) -> str:
        """Return last confirmed zone for a person (OUTSIDE if unknown)."""
        return self._confirmed_zone.get(person_id, OUTSIDE)

    @property
    def zone_colors(self) -> Dict[str, Tuple[int, int, int]]:
        """BGR color per zone name, for overlay rendering."""
        return {z.name: z.color for z in self.zones}

    @property
    def zone_polygons(self) -> Dict[str, np.ndarray]:
        """Polygon array per zone name."""
        return {z.name: z.polygon for z in self.zones}
