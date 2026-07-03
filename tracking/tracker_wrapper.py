# tracking/tracker_wrapper.py
"""
Tracking wrapper consolidating ByteTracker initialization and updates.
"""

import sys
import os
import numpy as np

# Ensure root path is present
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from byte_tracker import ByteTracker

class TrackerWrapper:
    def __init__(self, config_loader=None):
        if config_loader:
            self.tracker = ByteTracker(
                max_dist_active=config_loader.get_nested("tracker", "max_dist_active", 180),
                max_dist_lost=config_loader.get_nested("tracker", "max_dist_lost", 120),
                max_missing=config_loader.get_nested("tracker", "max_missing", 90),
                min_hits=config_loader.get_nested("tracker", "min_hits", 3),
                count_min_hits=config_loader.get_nested("tracker", "count_min_hits", 6),
                active_window=config_loader.get_nested("tracker", "active_window", 8),
                velocity_alpha=config_loader.get_nested("tracker", "velocity_alpha", 0.30),
                velocity_damp=config_loader.get_nested("tracker", "velocity_damp", 0.80),
                high_conf_thresh=config_loader.get_nested("tracker", "high_conf_thresh", 0.30),
                adaptive_strategy=config_loader.get_nested("tracker", "adaptive_strategy", "hybrid")
            )
        else:
            self.tracker = ByteTracker()

    def update(self, detections, frame_id: int, timestamp: float):
        """
        detections: List of [x1, y1, x2, y2, confidence]
        Returns: List of (track_id, [x1, y1, x2, y2], confidence, confirmed, countable)
        """
        return self.tracker.update(detections, frame_id, timestamp)
