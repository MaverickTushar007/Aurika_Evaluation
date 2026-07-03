# counting/zone_counter.py
"""
Visitor and staff zone counter wrapper using spatial mappings.
"""

import sys
import os
from typing import List, Tuple, Dict, Optional

# Ensure root path is present
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from restaurant_analytics.zone_mapper import ZoneMapper

class ZoneCounter:
    def __init__(self, config_loader=None):
        if config_loader:
            # Load polygon configurations
            coords = config_loader.get_nested("counting", "zone_coords", [[100, 200], [500, 200], [500, 600], [100, 600]])
            zones = {
                "Service_Zone": [tuple(p) for p in coords]
            }
            self.mapper = ZoneMapper(zones=zones)
            self.min_time = config_loader.get_nested("counting", "min_time_seconds", 5.0)
        else:
            zones = {
                "Service_Zone": [(100, 200), (500, 200), (500, 600), (100, 600)]
            }
            self.mapper = ZoneMapper(zones=zones)
            self.min_time = 5.0

    def get_zone(self, bbox: List[float]) -> Optional[str]:
        """Returns the zone string if bbox is inside, else None."""
        return self.mapper.get_zone_for_bbox(bbox)
