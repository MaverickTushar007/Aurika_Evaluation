from typing import List, Tuple, Dict, Optional
import numpy as np
import cv2

class ZoneMapper:
    """
    Handles floorplan zone mapping, spatial containment, and homography matrix calculations.
    """
    def __init__(self, zones: Dict[str, List[Tuple[float, float]]], homography_matrix: Optional[List[List[float]]] = None, frame_size: Optional[Tuple[int, int]] = None):
        """
        zones: dict of zone_id -> list of polygon vertices (x, y)
        homography_matrix: 3x3 homography matrix list for mapping camera view to top-down coordinates
        frame_size: Optional tuple of actual frame dimensions (width, height)
        """
        self.h_matrix = np.array(homography_matrix) if homography_matrix is not None else None
        
        # Determine canonical size of input zones
        max_x = 0.0
        max_y = 0.0
        for poly in zones.values():
            for pt in poly:
                max_x = max(max_x, pt[0])
                max_y = max(max_y, pt[1])
        
        canonical_w = 1920.0 if (max_x > 1300 or max_y > 800) else 1280.0
        canonical_h = 1080.0 if (max_x > 1300 or max_y > 800) else 720.0
        
        if frame_size is not None:
            w, h = frame_size
            scale_x = w / canonical_w
            scale_y = h / canonical_h
            
            scaled_zones = {}
            for zone_id, poly in zones.items():
                scaled_poly = [(float(pt[0] * scale_x), float(pt[1] * scale_y)) for pt in poly]
                scaled_zones[zone_id] = scaled_poly
            self.zones = scaled_zones
        else:
            self.zones = zones

    def map_pixel_to_floor(self, pixel_coord: Tuple[float, float]) -> Tuple[float, float]:
        """
        Maps a 2D camera pixel coordinate to 2D top-down floor coordinates using the homography matrix.
        """
        if self.h_matrix is None:
            # Return identity mapping if homography matrix is not configured
            return pixel_coord
        
        src_pt = np.array([[[pixel_coord[0], pixel_coord[1]]]], dtype=np.float32)
        dst_pt = cv2.perspectiveTransform(src_pt, self.h_matrix)
        floor_x = float(dst_pt[0][0][0])
        floor_y = float(dst_pt[0][0][1])
        return (floor_x, floor_y)

    def is_inside_zone(self, point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
        """
        OpenCV pointPolygonTest algorithm to determine if a point is inside a polygon.
        """
        if len(polygon) < 3:
            return False
        contour = np.array(polygon, dtype=np.float32)
        dist = cv2.pointPolygonTest(contour, (float(point[0]), float(point[1])), False)
        return dist >= 0

    def get_zone_for_bbox(self, bbox: List[float]) -> Optional[str]:
        """
        Determines the zone for a bounding box. Uses the bottom-center point of the bounding box.
        Nested sub-zones (like Table 101) are checked first by sorting zones by area.
        """
        x1, y1, x2, y2 = bbox
        bottom_center = ((x1 + x2) / 2.0, y2)
        
        target_point = self.map_pixel_to_floor(bottom_center)

        # Sort zones by polygon area (bounding box approximation) in ascending order
        def get_area(poly):
            xs = [pt[0] for pt in poly]
            ys = [pt[1] for pt in poly]
            return (max(xs) - min(xs)) * (max(ys) - min(ys))

        sorted_zones = sorted(self.zones.items(), key=lambda item: get_area(item[1]))

        for zone_id, polygon in sorted_zones:
            if self.is_inside_zone(target_point, polygon):
                return zone_id
        return None
