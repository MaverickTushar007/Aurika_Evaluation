# benchmark/loader.py
"""
benchmark/loader.py
-------------------
Loads validation/test datasets and ground-truth annotation files (gt.txt)
formatted according to the standard MOT Challenge 2D tracking conventions:
Format:
  frame_id, track_id, x_min, y_min, width, height, class_id, [optional...]
"""

import os
from typing import Dict, List, Tuple

class DatasetLoader:
    def __init__(self, dataset_dir: str):
        """
        dataset_dir: Root folder containing subdirectories for each video site.
                     Example:
                     dataset_dir/
                     ├── Site_1_QSR/
                     │   ├── video.mp4
                     │   └── gt/
                     │       └── gt.txt
        """
        self.dataset_dir = dataset_dir

    def get_available_clips(self) -> List[str]:
        """Returns the list of directory names matching each video site."""
        if not os.path.exists(self.dataset_dir):
            return []
        clips = []
        for name in sorted(os.listdir(self.dataset_dir)):
            full_path = os.path.join(self.dataset_dir, name)
            if os.path.isdir(full_path) and os.path.exists(os.path.join(full_path, "gt", "gt.txt")):
                clips.append(name)
        return clips

    def get_clip_paths(self, clip_name: str) -> Tuple[str, str]:
        """Returns (video_path, gt_annotations_path) for a clip."""
        clip_dir = os.path.join(self.dataset_dir, clip_name)
        # Find any video file
        video_file = None
        for file in os.listdir(clip_dir):
            if file.lower().endswith((".mp4", ".mkv", ".webm", ".avi")):
                video_file = os.path.join(clip_dir, file)
                break
        
        gt_path = os.path.join(clip_dir, "gt", "gt.txt")
        return video_file or "", gt_path

    def load_gt_annotations(self, gt_path: str) -> Dict[int, List[Dict[str, any]]]:
        """
        Loads ground truth tracking boxes indexed by frame ID.
        Returns:
            Dict[frame_id, List[Dict[str, any]]]
            Each Dict contains:
              - bbox: [x1, y1, x2, y2]
              - track_id: int
              - class_id: int
        """
        annotations = {}
        if not os.path.exists(gt_path):
            return annotations

        with open(gt_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 6:
                    continue
                
                try:
                    frame_id = int(float(parts[0]))
                    track_id = int(float(parts[1]))
                    x_min    = float(parts[2])
                    y_min    = float(parts[3])
                    width    = float(parts[4])
                    height   = float(parts[5])
                    class_id = int(float(parts[6])) if len(parts) > 6 else 1  # 1=guest, 2=staff
                    
                    x1, y1 = x_min, y_min
                    x2, y2 = x_min + width, y_min + height
                    
                    bbox = [x1, y1, x2, y2]
                    
                    annotations.setdefault(frame_id, []).append({
                        "bbox": bbox,
                        "track_id": track_id,
                        "class_id": class_id
                    })
                except (ValueError, IndexError):
                    continue
        return annotations
