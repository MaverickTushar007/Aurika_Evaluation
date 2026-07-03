# benchmark/tracker_wrapper.py
"""
benchmark/tracker_wrapper.py
----------------------------
Unified tracker wrapper class to standardise tracking interface across:
  - Custom ByteTracker (baseline)
  - BoxMOT BotSort (without ReID)
  - BoxMOT OcSort
  - BoxMOT ByteTrack
Exposes identical API signatures, hit-gating logic, and spatial centroid tracking.
"""

import numpy as np
from byte_tracker import ByteTracker as CustomByteTracker
from boxmot.trackers import BotSort, OcSort, ByteTrack as BoxmotByteTrack

class TrackerWrapper:
    def __init__(self, tracker_type, tracker_cfg, min_hits=3, count_min_hits=6, max_missing=90):
        self.tracker_type = tracker_type
        self.min_hits = min_hits
        self.count_min_hits = count_min_hits
        self.max_missing = max_missing
        
        # Internals for boxmot trackers
        self._tracks = {}       # tid -> {"history": []}
        self.track_hits = {}    # tid -> int
        self.last_seen = {}     # tid -> int
        
        if tracker_type == "bytetrack_baseline":
            self.tracker = CustomByteTracker(
                max_dist_active=tracker_cfg.get("max_dist_active", 180),
                max_dist_lost=tracker_cfg.get("max_dist_lost", 120),
                max_missing=max_missing,
                min_hits=min_hits,
                count_min_hits=count_min_hits,
                active_window=tracker_cfg.get("active_window", 8),
                velocity_alpha=tracker_cfg.get("velocity_alpha", 0.30),
                velocity_damp=tracker_cfg.get("velocity_damp", 0.80),
                high_conf_thresh=tracker_cfg.get("high_conf_thresh", 0.30),
                enable_lost_recovery=tracker_cfg.get("enable_lost_recovery", True),
                enable_velocity_predict=tracker_cfg.get("enable_velocity_predict", True),
                adaptive_strategy=tracker_cfg.get("adaptive_strategy", None)
            )
        elif tracker_type == "botsort":
            # Initialize boxmot BotSort without ReID
            self.tracker = BotSort(
                reid_model=None,
                with_reid=False,
                track_high_thresh=tracker_cfg.get("high_conf_thresh", 0.30),
                track_low_thresh=0.10,
                new_track_thresh=0.30,
                track_buffer=max_missing,
                match_thresh=0.80
            )
        elif tracker_type == "ocsort":
            # Initialize boxmot OcSort
            self.tracker = OcSort(
                min_conf=0.10,
                det_thresh=tracker_cfg.get("high_conf_thresh", 0.30),
                max_age=max_missing,
                min_hits=min_hits
            )
        elif tracker_type == "bytetrack_boxmot":
            # Initialize boxmot ByteTrack
            self.tracker = BoxmotByteTrack(
                min_conf=0.10,
                track_thresh=tracker_cfg.get("high_conf_thresh", 0.30),
                track_buffer=max_missing
            )
        else:
            raise ValueError(f"Unknown tracker type: {tracker_type}")

    @property
    def tracks(self):
        if self.tracker_type == "bytetrack_baseline":
            return self.tracker.tracks
        return self._tracks

    def update(self, detections, frame_id, ts, frame_img=None):
        if self.tracker_type == "bytetrack_baseline":
            return self.tracker.update(detections, frame_id, ts)
            
        # Format input detections for BoxMOT [x1, y1, x2, y2, confidence, class_id]
        if not detections:
            self._prune_history(frame_id)
            return []
            
        dets_np = []
        for det in detections:
            dets_np.append([det[0], det[1], det[2], det[3], det[4], 0.0])
        dets_np = np.array(dets_np, dtype=np.float32)
        
        # Ensure image frame exists
        if frame_img is None:
            frame_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
            
        res = self.tracker.update(dets_np, frame_img)
        
        # Convert BoxMOT output back to pipeline expected tuples:
        # (track_id, bbox, confidence, confirmed, countable)
        output_tracks = []
        for i in range(len(res)):
            bbox = res.xyxy[i].tolist()
            tid = int(res.id[i])
            conf = float(res.conf[i])
            
            # Hit tracking
            self.track_hits[tid] = self.track_hits.get(tid, 0) + 1
            self.last_seen[tid] = frame_id
            
            # Spatial history accumulation for semantic classification
            cx = (bbox[0] + bbox[2]) / 2.0
            cy = (bbox[1] + bbox[3]) / 2.0
            self._tracks.setdefault(tid, {"history": []})["history"].append((cx, cy))
            
            confirmed = self.track_hits[tid] >= self.min_hits
            countable = self.track_hits[tid] >= self.count_min_hits
            
            output_tracks.append((tid, bbox, conf, confirmed, countable))
            
        self._prune_history(frame_id)
        return output_tracks

    def _prune_history(self, frame_id):
        for tid in list(self.last_seen):
            if (frame_id - self.last_seen[tid]) > self.max_missing:
                self._tracks.pop(tid, None)
                self.track_hits.pop(tid, None)
                self.last_seen.pop(tid, None)
