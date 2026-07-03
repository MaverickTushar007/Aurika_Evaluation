# semantic/role_classifier.py
"""
Role classifier wrapper utilizing MultiModalStaffIdentifier.
"""

import sys
import os
import numpy as np

# Ensure root path is present
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from restaurant_analytics.staff_identifier import MultiModalStaffIdentifier, UniformColorIdentifier

class RoleClassifier:
    def __init__(self, config_loader=None):
        if config_loader:
            threshold = config_loader.get_nested("semantic", "staff_zone_threshold", 0.80)
            self.identifier = MultiModalStaffIdentifier(
                color_identifier=UniformColorIdentifier(
                    lower_hsv=(0, 100, 100),
                    upper_hsv=(10, 255, 255),
                    pixel_ratio_threshold=0.15
                ),
                weights={"color": 0.4, "badge": 0.5, "embedding": 0.6}
            )
            self.min_track_length = config_loader.get_nested("semantic", "min_track_length", 15)
        else:
            self.identifier = MultiModalStaffIdentifier()
            self.min_track_length = 15

    def classify(self, frame, bbox, track_history_len: int) -> str:
        """
        Classifies role as 'staff' or 'guest'.
        """
        if track_history_len < self.min_track_length:
            return "guest"
            
        label, conf = self.identifier.identify_staff(frame, bbox)
        if label is not None:
            return "staff"
        return "guest"
