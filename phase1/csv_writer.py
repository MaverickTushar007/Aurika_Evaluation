"""
phase1/csv_writer.py
====================
Three incremental CSV writers for Phase 1 outputs.

Writers:
  1. TransitionWriter  — one row per confirmed zone transition
  2. FrameHistoryWriter — one row per (person, frame) where person is visible
  3. PersonSummaryWriter — one row per person (written at end / when track ends)

All timestamps are in seconds from video start (float).
No business logic. Pure data recording.
"""

from __future__ import annotations
import csv
import os
from typing import Dict, Optional


# ── Column schemas ─────────────────────────────────────────────────────────────

TRANSITION_COLS = [
    "person_id", "frame", "timestamp_sec",
    "previous_zone", "current_zone",
    "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2",
    "tracker_confidence", "detection_confidence",
]

FRAME_HISTORY_COLS = [
    "frame", "timestamp_sec", "person_id", "current_zone", "track_age",
    "visibility", "tracking_state", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2",
    "bottom_center_x", "bottom_center_y",
    "observation_type", "is_detected", "detection_confidence",
    "association_cost", "frames_since_detection", "track_quality",
]

PERSON_SUMMARY_COLS = [
    "person_id", "first_frame", "last_frame", "total_visible_frames",
    "waiting_entries", "waiting_exits",
    "dining_entries", "dining_exits",
    "reception_entries", "reception_exits",
    "current_zone", "status",
]


# ── Writers ───────────────────────────────────────────────────────────────────

class TransitionWriter:
    """
    Appends one row for each confirmed zone transition.
    Validates: previous_zone != current_zone (no duplicates accepted).
    """

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._f = open(path, "w", newline="")
        self._writer = csv.DictWriter(self._f, fieldnames=TRANSITION_COLS)
        self._writer.writeheader()
        self._row_count = 0

    def write(
        self,
        person_id: int,
        frame: int,
        timestamp_sec: float,
        previous_zone: str,
        current_zone: str,
        bbox: tuple,
        tracker_conf: float,
        det_conf: float,
    ):
        if previous_zone == current_zone:
            return  # guard: never write a no-op transition
        x1, y1, x2, y2 = bbox
        self._writer.writerow({
            "person_id": person_id,
            "frame": frame,
            "timestamp_sec": round(timestamp_sec, 4),
            "previous_zone": previous_zone,
            "current_zone": current_zone,
            "bbox_x1": x1,
            "bbox_y1": y1,
            "bbox_x2": x2,
            "bbox_y2": y2,
            "tracker_confidence": round(tracker_conf, 4),
            "detection_confidence": round(det_conf, 4),
        })
        self._f.flush()
        self._row_count += 1

    @property
    def row_count(self) -> int:
        return self._row_count

    def close(self):
        self._f.close()


class FrameHistoryWriter:
    """
    Appends one row per visible person per frame.
    This is the primary source-of-truth for 'where was each person at each frame'.
    """

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._f = open(path, "w", newline="")
        self._writer = csv.DictWriter(self._f, fieldnames=FRAME_HISTORY_COLS)
        self._writer.writeheader()
        # Track age per person (frames since first seen)
        self._first_frame: Dict[int, int] = {}
        self._row_count = 0

    def write(
        self,
        frame: int,
        timestamp_sec: float,
        person_id: int,
        current_zone: str,
        bbox: tuple,
        bottom_center: tuple,
        visibility: str = "VISIBLE",
        tracking_state: str = "ACTIVE",
        observation_type: str = "OBSERVED",
        is_detected: int = 1,
        detection_confidence: float = 0.0,
        association_cost: float = 0.0,
        frames_since_detection: int = 0,
        track_quality: str = "HIGH",
    ):
        if person_id not in self._first_frame:
            self._first_frame[person_id] = frame
        track_age = frame - self._first_frame[person_id]
        x1, y1, x2, y2 = bbox
        self._writer.writerow({
            "frame": frame,
            "timestamp_sec": round(timestamp_sec, 4),
            "person_id": person_id,
            "current_zone": current_zone,
            "track_age": track_age,
            "visibility": visibility,
            "tracking_state": tracking_state,
            "bbox_x1": x1,
            "bbox_y1": y1,
            "bbox_x2": x2,
            "bbox_y2": y2,
            "bottom_center_x": bottom_center[0],
            "bottom_center_y": bottom_center[1],
            "observation_type": observation_type,
            "is_detected": is_detected,
            "detection_confidence": round(detection_confidence, 4),
            "association_cost": round(association_cost, 4),
            "frames_since_detection": frames_since_detection,
            "track_quality": track_quality,
        })
        self._row_count += 1
        # Periodic flush (every 500 rows)
        if self._row_count % 500 == 0:
            self._f.flush()

    @property
    def row_count(self) -> int:
        return self._row_count

    def close(self):
        self._f.flush()
        self._f.close()


class PersonSummaryWriter:
    """
    Maintains per-person state and writes one summary row per person at the end.
    Updated live as events occur.
    """

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # In-memory state per person
        self._persons: Dict[int, dict] = {}

    def _ensure(self, person_id: int, frame: int, zone: str):
        if person_id not in self._persons:
            self._persons[person_id] = {
                "person_id": person_id,
                "first_frame": frame,
                "last_frame": frame,
                "total_visible_frames": 0,
                "waiting_entries": 0,
                "waiting_exits": 0,
                "dining_entries": 0,
                "dining_exits": 0,
                "reception_entries": 0,
                "reception_exits": 0,
                "current_zone": zone,
                "status": "active",
            }

    def record_frame(self, person_id: int, frame: int, zone: str):
        self._ensure(person_id, frame, zone)
        p = self._persons[person_id]
        p["last_frame"] = max(p["last_frame"], frame)
        p["total_visible_frames"] += 1
        p["current_zone"] = zone

    def record_transition(self, person_id: int, frame: int, prev_zone: str, curr_zone: str):
        """Update entry/exit counts based on a confirmed zone transition."""
        self._ensure(person_id, frame, curr_zone)
        p = self._persons[person_id]

        # Entry into new zone
        if curr_zone == "WAITING":
            p["waiting_entries"] += 1
        elif curr_zone == "DINING":
            p["dining_entries"] += 1
        elif curr_zone == "RECEPTION":
            p["reception_entries"] += 1

        # Exit from old zone
        if prev_zone == "WAITING":
            p["waiting_exits"] += 1
        elif prev_zone == "DINING":
            p["dining_exits"] += 1
        elif prev_zone == "RECEPTION":
            p["reception_exits"] += 1

    def mark_exited(self, person_id: int):
        if person_id in self._persons:
            self._persons[person_id]["status"] = "exited"

    def flush(self):
        """Write all person summaries to CSV (call at end of run)."""
        with open(self.path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=PERSON_SUMMARY_COLS)
            writer.writeheader()
            for person_id in sorted(self._persons.keys()):
                writer.writerow(self._persons[person_id])

    @property
    def persons(self) -> Dict[int, dict]:
        return self._persons
