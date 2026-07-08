"""
phase1/visualizer.py
====================
Frame overlay renderer for Phase 1.

Draws per frame:
  - Zone polygon outlines (color-coded)
  - Zone name labels
  - Bounding box per person (color = zone color)
  - Person ID label ("Person N")
  - Trajectory tail (last TAIL_LEN bottom-center positions)
  - Current zone label under each person
  - HUD: frame number, timestamp, live counts

No business KPIs. No alerts. No dashboard gauges.
"""

from __future__ import annotations
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from phase1.tracker import TrackedPerson
from phase1.zone_map import ZoneMap, OUTSIDE


TAIL_LEN = 40          # Number of past positions in trajectory tail
FONT = cv2.FONT_HERSHEY_SIMPLEX
OUTSIDE_COLOR = (160, 160, 160)   # Gray for persons in no zone


class Visualizer:
    """
    Stateful renderer. Must be called once per frame with the same frame_id
    sequence as the tracker.
    """

    def __init__(self, zone_map: ZoneMap, tail_len: int = TAIL_LEN):
        self.zone_map = zone_map
        self.tail_len = tail_len

        # Per-person trajectory history: {person_id: deque of (x, y) bottom-centers}
        self._tails: Dict[int, deque] = defaultdict(lambda: deque(maxlen=tail_len))

        # Colors
        self._zone_colors = zone_map.zone_colors      # BGR
        self._zone_polys = zone_map.zone_polygons

    def _get_color(self, zone: str) -> Tuple[int, int, int]:
        return self._zone_colors.get(zone, OUTSIDE_COLOR)

    def render(
        self,
        frame: np.ndarray,
        frame_id: int,
        timestamp_sec: float,
        persons: List[TrackedPerson],
        current_zones: Dict[int, str],
        total_unique_ids: int,
        id_switch_count: int,
    ) -> np.ndarray:
        """
        Draw all overlays onto a copy of the frame and return it.
        Does NOT modify the original frame.
        """
        out = frame.copy()

        # ── 1. Zone polygons ────────────────────────────────────────────────
        for zone_name, poly in self._zone_polys.items():
            color = self._zone_colors.get(zone_name, OUTSIDE_COLOR)
            # Semi-transparent fill
            overlay = out.copy()
            cv2.fillPoly(overlay, [poly], color)
            cv2.addWeighted(overlay, 0.08, out, 0.92, 0, out)
            # Solid border
            cv2.polylines(out, [poly], isClosed=True, color=color, thickness=2)
            # Zone label (top-left corner of bounding rect)
            x, y, w, h = cv2.boundingRect(poly)
            cv2.putText(out, zone_name, (x + 6, y + 22),
                        FONT, 0.65, color, 2, cv2.LINE_AA)

        # ── 2. Per-person overlays ──────────────────────────────────────────
        for person in persons:
            pid = person.person_id
            zone = current_zones.get(pid, OUTSIDE)
            color = self._get_color(zone)
            x1, y1, x2, y2 = person.bbox
            bc = person.bottom_center

            # Trajectory tail
            self._tails[pid].append(bc)
            pts = list(self._tails[pid])
            for i in range(1, len(pts)):
                alpha = i / len(pts)
                pt_color = tuple(int(c * alpha) for c in color)
                cv2.line(out, pts[i - 1], pts[i], pt_color, 2, cv2.LINE_AA)

            # Bounding box
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)

            # Bottom-center dot (zone assignment point)
            cv2.circle(out, bc, 5, color, -1)

            # Person ID label (above bbox)
            label = f"Person {pid}"
            (lw, lh), _ = cv2.getTextSize(label, FONT, 0.55, 1)
            cv2.rectangle(out, (x1, y1 - lh - 8), (x1 + lw + 4, y1), color, -1)
            cv2.putText(out, label, (x1 + 2, y1 - 4),
                        FONT, 0.55, (0, 0, 0), 1, cv2.LINE_AA)

            # Zone label (below bbox)
            zone_label = zone
            cv2.putText(out, zone_label, (x1, y2 + 16),
                        FONT, 0.45, color, 1, cv2.LINE_AA)

        # ── 3. HUD ──────────────────────────────────────────────────────────
        hud_lines = [
            f"Frame: {frame_id:06d}",
            f"Time:  {timestamp_sec:.2f}s",
            f"Visible: {len(persons)}",
            f"Unique IDs: {total_unique_ids}",
            f"ID switches: {id_switch_count}",
        ]
        for i, line in enumerate(hud_lines):
            y = 24 + i * 22
            cv2.putText(out, line, (10, y), FONT, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(out, line, (10, y), FONT, 0.55, (30, 30, 30), 1, cv2.LINE_AA)

        return out

    def save_audit_frame(self, frame: np.ndarray, path: str):
        """Save a rendered frame to disk for Loop 5 visual audit."""
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        cv2.imwrite(path, frame)


def make_video_writer(path: str, fps: float, width: int, height: int) -> cv2.VideoWriter:
    """Create an H264 VideoWriter for the annotated output video."""
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    return cv2.VideoWriter(path, fourcc, fps, (width, height))


import os
