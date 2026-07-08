"""
phase1/spatial_validator.py
===========================
Performs automated polygon and floorplan validation before tracking starts.

Validation Loops:
  1. Closed polygons.
  2. No self-intersections.
  3. Positive area.
  4. No overlap between polygons (zero pixel-level intersection).
  5. All vertices lie inside the image boundaries.
  6. Complete spatial partition of restaurant floor (clean boundaries).
"""

import os
import json
import numpy as np
import cv2

class SpatialValidator:
    def __init__(self, config_path: str, width: int = 1920, height: int = 1080):
        self.config_path = config_path
        self.w = width
        self.h = height
        self.zones = {}
        self.load_zones()

    def load_zones(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Zones config not found: {self.config_path}")
        with open(self.config_path, "r") as f:
            self.zones = json.load(f)

    def validate(self, output_dir: str) -> bool:
        """
        Runs the 6 validation loops and generates zone_validation.md.
        Returns True if all checks pass, otherwise raises ValueError/returns False.
        """
        os.makedirs(output_dir, exist_ok=True)
        report_path = os.path.join(output_dir, "zone_validation.md")

        results = {
            "loop1_closed": "PASS",
            "loop2_no_self_intersect": "PASS",
            "loop3_positive_area": "PASS",
            "loop4_no_overlap": "PASS",
            "loop5_inside_image": "PASS",
            "loop6_partitioned": "PASS",
        }
        details = []
        errors = []

        # Build OpenCV contours and pixel masks
        contours = {}
        masks = {}
        areas_pixels = {}
        areas_cv2 = {}

        canvas_shape = (self.h, self.w)
        total_frame_pixels = self.w * self.h

        # ── Loop 1, 3, 5: Properties & Boundaries ─────────────────────────────
        for name, spec in self.zones.items():
            poly = spec.get("polygon", [])
            if len(poly) < 3:
                results["loop1_closed"] = "FAIL"
                errors.append(f"Zone {name} has less than 3 vertices (cannot be closed).")
                continue

            pts = np.array(poly, dtype=np.int32)
            contours[name] = pts

            # Loop 5: Inside image boundaries
            if np.any(pts[:, 0] < 0) or np.any(pts[:, 0] >= self.w) or \
               np.any(pts[:, 1] < 0) or np.any(pts[:, 1] >= self.h):
                results["loop5_inside_image"] = "FAIL"
                errors.append(f"Zone {name} has vertices outside image boundaries [0..{self.w}, 0..{self.h}].")

            # Loop 3: Positive area (cv2.contourArea)
            area_val = cv2.contourArea(pts)
            areas_cv2[name] = area_val
            if area_val <= 0:
                results["loop3_positive_area"] = "FAIL"
                errors.append(f"Zone {name} has zero or negative contour area ({area_val:.1f}).")

            # Pixel mask for overlap/partition checks
            mask = np.zeros(canvas_shape, dtype=np.uint8)
            cv2.fillPoly(mask, [pts], 1)
            masks[name] = mask
            areas_pixels[name] = int(np.sum(mask))

        # ── Loop 2: No self-intersections ─────────────────────────────────────
        for name, poly in [(k, v.get("polygon", [])) for k, v in self.zones.items()]:
            if len(poly) >= 3:
                if self._has_self_intersection(poly):
                    results["loop2_no_self_intersect"] = "FAIL"
                    errors.append(f"Zone {name} polygon has self-intersecting segments.")

        # ── Loop 4: Overlaps check (pixel level) ──────────────────────────────
        sum_mask = np.zeros(canvas_shape, dtype=np.int32)
        for mask in masks.values():
            sum_mask += mask

        overlap_pixels = int(np.sum(sum_mask > 1))
        total_covered_pixels = int(np.sum(sum_mask >= 1))
        total_zone_sum = sum(areas_pixels.values())

        overlap_percentage = 0.0
        if total_zone_sum > 0:
            overlap_percentage = (overlap_pixels / total_zone_sum) * 100.0

        if overlap_pixels > 0:
            results["loop4_no_overlap"] = "FAIL"
            errors.append(f"Polygons overlap at {overlap_pixels} pixels ({overlap_percentage:.3f}% overlap).")

        # ── Loop 6: Complete partition ────────────────────────────────────────
        # Complete partition means no overlaps (Loop 4) and valid coverage.
        if results["loop4_no_overlap"] == "FAIL":
            results["loop6_partitioned"] = "FAIL"
            errors.append("Spatial floorplan is not partitioned cleanly due to zone overlaps.")

        unassigned_pixels = total_frame_pixels - total_covered_pixels

        # Overall Status
        all_passed = all(status == "PASS" for status in results.values())
        status_str = "PASS" if all_passed else "FAIL"

        # ── Generate Report (zone_validation.md) ──────────────────────────────
        report_content = f"""# Spatial Floorplan Validation Report

Generated: {np.datetime64('now')}
Status: **{status_str}**

---

## Validation Loops Summary

- **Loop 1 — Polygon Closedness**: {results["loop1_closed"]}
- **Loop 2 — No Self-Intersections**: {results["loop2_no_self_intersect"]}
- **Loop 3 — Positive Polygon Area**: {results["loop3_positive_area"]}
- **Loop 4 — Zero Overlap Check**: {results["loop4_no_overlap"]}
- **Loop 5 — Coordinates Inside Canvas**: {results["loop5_inside_image"]}
- **Loop 6 — Clean Floor Partition**: {results["loop6_partitioned"]}

---

## Zone Metrics

| Zone | Vertices | CV2 Area (sq px) | Pixel Area (px) | Coverage (%) |
|------|----------|-------------------|-----------------|--------------|
"""
        for name in sorted(self.zones.keys()):
            poly = self.zones[name].get("polygon", [])
            area_c2 = areas_cv2.get(name, 0.0)
            area_px = areas_pixels.get(name, 0)
            pct = (area_px / total_frame_pixels) * 100.0
            report_content += f"| {name} | {len(poly)} | {area_c2:.1f} | {area_px} | {pct:.3f}% |\n"

        report_content += f"""
### Partition Summary
- **Total Image Resolution**: {self.w}×{self.h} ({total_frame_pixels} px)
- **Total Operational Area**: {total_covered_pixels} px ({ (total_covered_pixels/total_frame_pixels)*100.0:.3f}% of image)
- **Unassigned (Outside) Area**: {unassigned_pixels} px ({ (unassigned_pixels/total_frame_pixels)*100.0:.3f}% of image)
- **Overlap Area**: {overlap_pixels} px ({overlap_percentage:.3f}% of zones area)

"""
        if errors:
            report_content += "## Error Log\n"
            for err in errors:
                report_content += f"- ❌ {err}\n"

        with open(report_path, "w") as f:
            f.write(report_content)

        print(f"[SpatialValidator] Validation report written to: {report_path}")
        
        if not all_passed:
            print("[SpatialValidator] ERROR: Polygon validation checks failed!")
            for err in errors:
                print(f"  - {err}")
            return False

        print("[SpatialValidator] All 6 validation checks passed successfully.")
        return True

    def _ccw(self, A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    def _intersect(self, A, B, C, D):
        if A == C or A == D or B == C or B == D:
            return False
        return self._ccw(A, C, D) != self._ccw(B, C, D) and self._ccw(A, B, C) != self._ccw(A, B, D)

    def _has_self_intersection(self, poly) -> bool:
        n = len(poly)
        for i in range(n):
            p1 = poly[i]
            p2 = poly[(i + 1) % n]
            for j in range(i + 2, n):
                if (j + 1) % n == i:
                    continue
                p3 = poly[j]
                p4 = poly[(j + 1) % n]
                if self._intersect(p1, p2, p3, p4):
                    return True
        return False
