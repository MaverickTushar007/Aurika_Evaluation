# benchmark/run_benchmark.py
"""
benchmark/run_benchmark.py
--------------------------
Command-line interface to execute tracking benchmarks.
Parses a configuration YAML, runs the detection + tracking pipeline,
collects evaluation metrics, runs regression validation, and writes reports.

Usage:
  python benchmark/run_benchmark.py --config benchmark/configs/baseline_v6.yaml --split val
"""

import os
import sys
import time
import argparse
import yaml
import numpy as np
import torch
import cv2
from datetime import datetime
from ultralytics import YOLO

# Add root folder to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark.loader import DatasetLoader
from benchmark.evaluator import TrackingEvaluator
from benchmark.regression import RegressionChecker
from benchmark.report import ReportGenerator
from benchmark.tracker_wrapper import TrackerWrapper
from run_dark_test import apply_nms

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to config YAML")
    parser.add_argument("--split", default="val", choices=["val", "test", "dev_val"], help="Dataset split")
    parser.add_argument("--dataset-dir", default="roboflow_filtered", help="Path to the datasets directory")
    parser.add_argument("--log-root", default="benchmark/runs", help="Root folder for output logs")
    parser.add_argument("--tracker", default="bytetrack_baseline", choices=["bytetrack_baseline", "botsort", "ocsort", "bytetrack_boxmot"], help="Tracker implementation to evaluate")
    args = parser.parse_args()

    # ── 1. Load Config ────────────────────────────────────────────────────────
    if not os.path.exists(args.config):
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)

    with open(args.config, "r") as f:
        config = yaml.safe_load(f)

    # Prepare outputs
    timestamp = datetime.now().strftime("exp_%Y%m%d_%H%M%S")
    exp_dir = os.path.join(args.log_root, f"{timestamp}_{args.tracker}")
    os.makedirs(exp_dir, exist_ok=True)

    print(f"[bench] Running split '{args.split}' using configuration: {args.config}")
    print(f"[bench] Output directory: {exp_dir}")

    # Save copy of config for reproducibility
    with open(os.path.join(exp_dir, "config_backup.yaml"), "w") as f:
        yaml.dump(config, f)

    # ── 2. Initialize Hardware & Model ────────────────────────────────────────
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"[bench] Initalizing device: {device}")

    model_cfg = config.get("model", {})
    weights = model_cfg.get("weights", "yolo11m.pt")
    conf_threshold = model_cfg.get("conf_threshold", 0.20)
    classes = model_cfg.get("classes", [0])

    print(f"[bench] Loading YOLO model {weights} ...")
    detector = YOLO(weights)

    # ── 3. Dataset Discovery ──────────────────────────────────────────────────
    # Note: If no custom datasets directory is present, we fallback to evaluate on the default video file
    loader = DatasetLoader(args.dataset_dir)
    clips = loader.get_available_clips()

    # Fallback to local file evaluation if the dataset split directory does not exist yet
    if not clips:
        print("[bench] No dataset directories found in 'roboflow_filtered'. Simulating run against 'Dark_lighting.mp4'...")
        # We will dynamically mock a clip configuration for execution
        local_video = "Dark_lighting.mp4"
        if not os.path.exists(local_video):
            print(f"Error: Video file {local_video} not found. Cannot evaluate.")
            sys.exit(1)
        clips = ["Dark_lighting_Default"]
        # Create a mock loader configuration
        class MockLoader:
            def get_clip_paths(self, name):
                return local_video, ""
            def load_gt_annotations(self, path):
                return {}
        loader = MockLoader()

    # ── 4. Main Processing Loop ───────────────────────────────────────────────
    tracker_cfg = config.get("tracker", {})
    preproc_cfg = config.get("preprocessing", {})
    clahe_cfg = preproc_cfg.get("clahe", {})
    
    # Initialize trackers and evaluation accumulators
    evaluator = TrackingEvaluator()
    all_predictions = {}
    all_ground_truth = {}
    
    total_processed_frames = 0
    t_start = time.time()

    CLIP_ZONES = {
        "Site_01_Counter_01": (540.0, 270.0, 723.0, 540.0),
        "Site_02_Dining_01": (-1.0, -1.0, -1.0, -1.0),
        "Site_03_Cafe_01": (360.0, 180.0, 482.0, 360.0)
    }
    MOTION_RATIO_STAFF = 0.18
    MOTION_MIN_FRAMES = 15

    for clip in clips:
        video_path, gt_path = loader.get_clip_paths(clip)
        if not os.path.exists(video_path):
            print(f"[bench] Skipping clip {clip}: Video path does not exist ({video_path})")
            continue

        print(f"[bench] Processing clip: {clip} ({video_path})")
        current_zone = CLIP_ZONES.get(clip, (-1.0, -1.0, -1.0, -1.0))
        gt_data = loader.load_gt_annotations(gt_path)
        # Shift ground-truth frame IDs to align with the global processed frame counter
        shifted_gt_data = {}
        for gt_fid, gt_boxes in gt_data.items():
            global_fid = total_processed_frames + (gt_fid - 1)
            shifted_gt_data[global_fid] = gt_boxes
        all_ground_truth.update(shifted_gt_data)

        # Initialize tracker for the clip using unified wrapper
        tracker = TrackerWrapper(
            tracker_type=args.tracker,
            tracker_cfg=tracker_cfg,
            min_hits=tracker_cfg.get("min_hits", 3),
            count_min_hits=tracker_cfg.get("count_min_hits", 6),
            max_missing=tracker_cfg.get("max_missing", 90)
        )

        cap = cv2.VideoCapture(video_path)
        native_fps = cap.get(cv2.CAP_PROP_FPS) or 30
        skip = max(1, int(native_fps / 8))  # target 8fps

        frame_count = 0
        prev_bboxes = []
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % skip == 0:
                fid = total_processed_frames
                ts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

                # Preprocessing
                if clahe_cfg.get("enabled", True):
                    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
                    l, a, b = cv2.split(lab)
                    clahe = cv2.createCLAHE(clipLimit=clahe_cfg.get("clip_limit", 2.0), tileGridSize=tuple(clahe_cfg.get("tile_grid_size", [8,8])))
                    l_enhanced = clahe.apply(l)
                    frame = cv2.cvtColor(cv2.merge([l_enhanced, a, b]), cv2.COLOR_LAB2BGR)

                # Inference
                results = detector(frame, conf=conf_threshold, verbose=False, device=device, classes=classes)
                raw_bboxes = []
                raw_confs = []
                for box in results[0].boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    if (y2 - y1) < 25:
                        continue
                    raw_bboxes.append([x1, y1, x2, y2])
                    raw_confs.append(conf)

                # NMS
                nms_iou_threshold = model_cfg.get("nms_iou_threshold", 0.50)
                kept = apply_nms(raw_bboxes, raw_confs, iou_threshold=nms_iou_threshold)
                bboxes = [raw_bboxes[i] for i in kept]
                confs = [raw_confs[i] for i in kept]

                # Temporal Detection Consistency (Strategy D)
                if model_cfg.get("enable_temporal_consistency", False):
                    kept_indices = []
                    for idx, (bbox, conf) in enumerate(zip(bboxes, confs)):
                        # Check overlap with any box in prev_bboxes
                        matched = False
                        for p_bbox in prev_bboxes:
                            ix1, iy1 = max(bbox[0], p_bbox[0]), max(bbox[1], p_bbox[1])
                            ix2, iy2 = min(bbox[2], p_bbox[2]), min(bbox[3], p_bbox[3])
                            inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
                            if inter > 0:
                                area_a = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                                area_b = (p_bbox[2] - p_bbox[0]) * (p_bbox[3] - p_bbox[1])
                                iou = inter / (area_a + area_b - inter + 1e-9)
                                if iou >= 0.25:
                                    matched = True
                                    break
                        # Allow immediate entry for high-confidence detections, or if matched temporally
                        if matched or conf >= 0.40:
                            kept_indices.append(idx)
                    bboxes = [bboxes[idx] for idx in kept_indices]
                    confs = [confs[idx] for idx in kept_indices]

                prev_bboxes = bboxes
                detections = [[*bboxes[i], confs[i]] for i in range(len(bboxes))]

                # Tracker Update (passing frame image for boxmot backends)
                track_results = tracker.update(detections, fid, ts, frame_img=frame)

                # Semantic Classification voting Heuristic
                frame_preds = []
                disable_voting = config.get("ablate_semantic_voting", False)
                semantic_strategy = config.get("semantic_strategy", "baseline")
                
                for tid, t_bbox, t_conf, confirmed, countable in track_results:
                    tr = tracker.tracks.get(tid)
                    role = "guest"
                    if tr is not None and not disable_voting:
                        history = tr.get("history", [])
                        
                        if semantic_strategy == "baseline":
                            if len(history) >= MOTION_MIN_FRAMES:
                                pts = np.array(history)
                                disps = np.sqrt(np.sum(np.diff(pts, axis=0) ** 2, axis=1))
                                high_motion = np.mean(disps > 25.0)
                                if high_motion >= MOTION_RATIO_STAFF:
                                    role = "staff"
                                else:
                                    mean_x, mean_y = pts[:, 0].mean(), pts[:, 1].mean()
                                    sx1, sy1, sx2, sy2 = (540.0, 270.0, 723.0, 540.0)
                                    if sx1 <= mean_x <= sx2 and sy1 <= mean_y <= sy2:
                                        role = "staff"
                                        
                        elif semantic_strategy == "strategy_a":
                            # Strategy A: Configurable Zones
                            if len(history) >= MOTION_MIN_FRAMES:
                                pts = np.array(history)
                                disps = np.sqrt(np.sum(np.diff(pts, axis=0) ** 2, axis=1))
                                high_motion = np.mean(disps > 25.0)
                                if high_motion >= MOTION_RATIO_STAFF:
                                    role = "staff"
                                else:
                                    mean_x, mean_y = pts[:, 0].mean(), pts[:, 1].mean()
                                    sx1, sy1, sx2, sy2 = current_zone
                                    if sx1 <= mean_x <= sx2 and sy1 <= mean_y <= sy2:
                                        role = "staff"
                                        
                        elif semantic_strategy == "strategy_b":
                            # Strategy B: Temporal Role Confidence
                            pts = np.array(history)
                            if len(pts) > 0:
                                score = 0.0
                                sx1, sy1, sx2, sy2 = current_zone
                                for pt in pts:
                                    if sx1 <= pt[0] <= sx2 and sy1 <= pt[1] <= sy2:
                                        score += 0.20
                                    else:
                                        score -= 0.05
                                if len(pts) >= 2:
                                    disps = np.sqrt(np.sum(np.diff(pts, axis=0) ** 2, axis=1))
                                    high_motion = np.mean(disps > 25.0)
                                    if high_motion >= 0.15:
                                        score += 0.30
                                if score >= 0.50:
                                    role = "staff"
                                    
                        elif semantic_strategy == "strategy_c":
                            # Strategy C: Activity-based Features (Zone Dwell Ratio)
                            pts = np.array(history)
                            if len(pts) > 0:
                                sx1, sy1, sx2, sy2 = current_zone
                                in_zone_count = sum(1 for pt in pts if sx1 <= pt[0] <= sx2 and sy1 <= pt[1] <= sy2)
                                ratio_in_zone = in_zone_count / len(pts)
                                if ratio_in_zone >= 0.25:
                                    role = "staff"
                                    
                        elif semantic_strategy == "strategy_d":
                            # Strategy D: Hybrid Rule Engine
                            pts = np.array(history)
                            if len(pts) > 0:
                                sx1, sy1, sx2, sy2 = current_zone
                                in_zone_count = sum(1 for pt in pts if sx1 <= pt[0] <= sx2 and sy1 <= pt[1] <= sy2)
                                ratio_in_zone = in_zone_count / len(pts)
                                
                                is_zone = ratio_in_zone >= 0.25
                                is_motion = False
                                if len(pts) >= 2:
                                    disps = np.sqrt(np.sum(np.diff(pts, axis=0) ** 2, axis=1))
                                    high_motion = np.mean(disps > 25.0)
                                    is_motion = high_motion >= 0.15
                                    
                                if is_zone or is_motion:
                                    role = "staff"
                                    
                    frame_preds.append((tid, t_bbox, t_conf, role))

                all_predictions[fid] = frame_preds
                total_processed_frames += 1

            frame_count += 1
        cap.release()

    t_duration = time.time() - t_start
    fps_actual = total_processed_frames / max(t_duration, 0.001)

    print(f"[bench] Inference processing complete. FPS: {fps_actual:.1f}")

    # ── 5. Run Metrics & Regression ───────────────────────────────────────────
    metrics = evaluator.evaluate_clip(all_predictions, all_ground_truth)
    
    # Inject baseline thresholds config into metric structure for comparison report
    reg_cfg = config.get("regression_thresholds", {})
    metrics["target_min_mota"] = reg_cfg.get("min_mota", 0.70)
    metrics["target_min_idf1"] = reg_cfg.get("min_idf1", 0.75)
    metrics["target_max_id_switches"] = reg_cfg.get("max_id_switches", 30)
    metrics["target_min_counting_accuracy"] = reg_cfg.get("min_counting_accuracy", 0.90)
    metrics["target_min_fps"] = reg_cfg.get("min_fps", 12.0)

    checker = RegressionChecker(reg_cfg)
    passed, issues = checker.check_metrics(metrics, fps_actual)

    # ── 6. Save Reports ───────────────────────────────────────────────────────
    report_path = os.path.join(exp_dir, "report.md")
    ReportGenerator.generate_report(
        output_path=report_path,
        config_path=args.config,
        metrics=metrics,
        passed=passed,
        issues=issues,
        fps=fps_actual,
        duration=t_duration
    )

    if not passed:
        print("[bench] WARNING: Regression detected!")
        for issue in issues:
            print(f"  • {issue}")
        sys.exit(2)
    else:
        print("[bench] SUCCESS: All evaluation criteria satisfied.")

if __name__ == "__main__":
    main()
