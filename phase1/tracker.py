"""
phase1/tracker.py
=================
Person-only detection + BoTSORT tracking wrapper.

Rules:
  - Only class == 0 (person) detections are passed downstream.
  - All other classes are silently discarded.
  - Track IDs are stable integers assigned by YOLO's built-in tracker.
  - No business logic. No zone logic. Just boxes + IDs.
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import List, Optional

from ultralytics import YOLO
import numpy as np


# ── Data contract ──────────────────────────────────────────────────────────────

@dataclass
class TrackedPerson:
    """Single tracked person at a single frame."""
    person_id: int                  # stable integer ID from BoTSORT
    bbox: tuple                     # (x1, y1, x2, y2) in pixel coords
    det_conf: float                 # YOLO detection confidence [0..1]
    track_conf: float               # BoTSORT track confidence [0..1]
    is_new: bool                    # True if this ID appeared for the first time
    class_id: int = 0               # always 0 (person)
    association_cost: float = 0.0   # Hungarian matching cost (1 - IoU)

    @property
    def bottom_center(self) -> tuple:
        """Point used for zone assignment: bottom-center of bbox."""
        x1, y1, x2, y2 = self.bbox
        return (int((x1 + x2) / 2), int(y2))

    @property
    def center(self) -> tuple:
        x1, y1, x2, y2 = self.bbox
        return (int((x1 + x2) / 2), int((y1 + y2) / 2))


@dataclass
class FrameResult:
    """All tracked persons at a single frame."""
    frame_id: int
    timestamp_sec: float
    persons: List[TrackedPerson] = field(default_factory=list)
    raw_detections: int = 0         # total detections before class filter
    person_detections: int = 0      # detections after class filter


# ── Tracker ───────────────────────────────────────────────────────────────────

class PersonTracker:
    """
    Wraps YOLO + BoTSORT for person-only tracking.

    Parameters
    ----------
    model_path : str
        Path to .pt YOLO weights file.
    tracker_config : str
        Path to BoTSORT/ByteTrack YAML config.
    det_conf : float
        YOLO detection confidence threshold.
    person_class_ids : list
        Class indices to treat as "person". For yolo_staff_customer.pt:
        0=customer, 1=staff — both are humans, both tracked.
    device : str
        'cpu', 'cuda', 'mps', etc.
    """

    def __init__(
        self,
        model_path: str,
        tracker_config: str,
        det_conf: float = 0.05,
        person_class_ids: Optional[List[int]] = None,
        device: str = "cpu",
    ):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")
        if not os.path.exists(tracker_config):
            raise FileNotFoundError(f"Tracker config not found: {tracker_config}")

        self.model = YOLO(model_path)
        self.tracker_config = tracker_config
        self.det_conf = det_conf
        # Default: detect all human classes in the custom model
        self.person_class_ids = set(person_class_ids) if person_class_ids else set(self.model.names.keys())
        self.device = device

        print(f"[Tracker] Model classes: {self.model.names}")
        print(f"[Tracker] Tracking class IDs: {self.person_class_ids} "
              f"({[self.model.names[c] for c in sorted(self.person_class_ids)]})")

        # Track ID bookkeeping for new-track detection
        self._seen_ids: set = set()
        self._id_switch_candidates: List[dict] = []

    def process_frame(self, frame: np.ndarray, frame_id: int, timestamp_sec: float) -> FrameResult:
        """
        Run YOLO + BoTSORT on one frame. Returns FrameResult with person tracks only.
        """
        result = FrameResult(frame_id=frame_id, timestamp_sec=timestamp_sec)

        # Run tracking (persist=True maintains tracker state across calls)
        # classes=None → detect all, then filter by person_class_ids below
        yolo_results = self.model.track(
            frame,
            persist=True,
            tracker=self.tracker_config,
            conf=self.det_conf,
            verbose=False,
            device=self.device,
        )

        if not yolo_results or yolo_results[0].boxes is None:
            return result

        boxes = yolo_results[0].boxes
        result.raw_detections = len(boxes)

        for box in boxes:
            cls = int(box.cls[0].item()) if box.cls is not None else -1
            # Filter: only accept class IDs designated as persons
            if cls not in self.person_class_ids:
                continue

            # Track ID — may be None if tracker hasn't assigned yet
            if box.id is None:
                continue
            tid = int(box.id[0].item())

            xyxy = box.xyxy[0].cpu().numpy().astype(int)
            x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])

            det_conf = float(box.conf[0].item()) if box.conf is not None else 0.0
            track_conf = det_conf  # BoTSORT doesn't expose separate track score in YOLO API

            is_new = tid not in self._seen_ids
            if is_new:
                self._seen_ids.add(tid)
                if frame_id > 0:
                    # A new ID after frame 0 is a potential ID switch candidate
                    self._id_switch_candidates.append({
                        "frame": frame_id,
                        "person_id": tid,
                        "reason": "new_id_after_start"
                    })

            costs = {}
            if hasattr(self.model, 'predictor') and self.model.predictor is not None:
                if hasattr(self.model.predictor, 'trackers') and len(self.model.predictor.trackers) > 0:
                    tracker_obj = self.model.predictor.trackers[0]
                    costs = getattr(tracker_obj, 'match_costs', {})
            cost = costs.get(tid, 0.0)

            person = TrackedPerson(
                person_id=tid,
                bbox=(x1, y1, x2, y2),
                det_conf=det_conf,
                track_conf=track_conf,
                is_new=is_new,
                class_id=cls,
                association_cost=cost,
            )
            result.persons.append(person)

        result.person_detections = len(result.persons)
        return result

    @property
    def id_switch_candidates(self) -> List[dict]:
        """List of frames where a new ID appeared after frame 0 (potential switches)."""
        return self._id_switch_candidates

    @property
    def unique_ids(self) -> set:
        return self._seen_ids.copy()
