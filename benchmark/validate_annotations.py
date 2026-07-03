# benchmark/validate_annotations.py
"""
benchmark/validate_annotations.py
---------------------------------
Automated validation tool to verify the integrity of tracking annotations (gt.txt)
against standard quality assurance criteria:
  - Bounding box dimension sanity (non-zero area, height bounds, aspect ratio)
  - Speed limit bounds (spatial frame-to-frame jumps)
  - Track ID class role consistency (ensuring IDs do not drift classes)
"""

import os
import sys
import argparse

def validate_gt_file(gt_path: str, max_jump_pixels: float = 200.0, min_height: float = 20.0) -> bool:
    if not os.path.exists(gt_path):
        print(f"[qa] Error: Ground-truth file not found: {gt_path}")
        return False

    passed = True
    issues = []
    
    # Store track state
    # track_id -> (prev_frame, prev_centroid_x, prev_centroid_y, class_role)
    track_histories = {}
    
    line_idx = 0
    with open(gt_path, "r") as f:
        for line in f:
            line_idx += 1
            line = line.strip()
            if not line or line.startswith("#"):
                continue
                
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 6:
                issues.append(f"Line {line_idx}: Invalid format (expected at least 6 comma-separated fields, got {len(parts)}).")
                passed = False
                continue
                
            try:
                frame_id = int(float(parts[0]))
                track_id = int(float(parts[1]))
                x_min    = float(parts[2])
                y_min    = float(parts[3])
                width    = float(parts[4])
                height   = float(parts[5])
                class_role = int(float(parts[6])) if len(parts) > 6 else 1
            except ValueError:
                issues.append(f"Line {line_idx}: Failed to parse numeric values.")
                passed = False
                continue
                
            # Aspect ratio & dimensions check
            if width <= 0 or height <= 0:
                issues.append(f"Line {line_idx}: Invalid dimensions width={width}, height={height} (must be positive).")
                passed = False
                
            if height < min_height:
                issues.append(f"Line {line_idx}: Bounding box height too small ({height:.1f}px < {min_height:.1f}px).")
                passed = False

            aspect_ratio = width / max(0.001, height)
            if aspect_ratio > 1.5:
                # Warning only - could be seated or crawling, but flag as potential issue
                issues.append(f"Line {line_idx}: Warning - anomalous aspect ratio (w/h = {aspect_ratio:.2f} > 1.5).")
            
            # Centroid computation
            cx = x_min + width / 2.0
            cy = y_min + height / 2.0
            
            # Track history and jump checks
            if track_id in track_histories:
                prev_frame, prev_cx, prev_cy, prev_role = track_histories[track_id]
                
                # Check for class drift
                if class_role != prev_role:
                    issues.append(f"Frame {frame_id}: Track ID {track_id} drifted class from {prev_role} to {class_role}.")
                    passed = False
                    
                # Check for frame jump (limit checks on sequential frames only)
                if frame_id == prev_frame + 1:
                    dist = ((cx - prev_cx) ** 2 + (cy - prev_cy) ** 2) ** 0.5
                    if dist > max_jump_pixels:
                        issues.append(f"Frame {frame_id}: Track ID {track_id} jumped {dist:.1f}px from frame {prev_frame} (max limit={max_jump_pixels}px).")
                        passed = False
            
            # Update history state
            track_histories[track_id] = (frame_id, cx, cy, class_role)
            
    # Output QA scan summary
    print(f"[qa] Scanned {line_idx} lines in {gt_path}")
    if passed:
        print("[qa] SUCCESS: Annotation file passed all integrity gates.")
    else:
        print(f"[qa] FAILURE: Identified {len(issues)} validation problems:")
        for issue in issues[:20]: # show first 20 problems
            print(f"  • {issue}")
        if len(issues) > 20:
            print(f"  • ... and {len(issues) - 20} more issues.")
            
    return passed

def main():
    parser = argparse.ArgumentParser(description="Annotation Quality Assurance Integrity Check.")
    parser.add_argument("--gt", required=True, help="Path to tracking gt.txt file to validate")
    parser.add_argument("--max-jump", type=float, default=200.0, help="Maximum allowed frame-to-frame shift in pixels")
    parser.add_argument("--min-height", type=float, default=20.0, help="Minimum bounding box height allowed")
    args = parser.parse_args()
    
    success = validate_gt_file(args.gt, args.max_jump, args.min_height)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
