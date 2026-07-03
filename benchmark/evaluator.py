# benchmark/evaluator.py
"""
benchmark/evaluator.py
----------------------
Core metric calculation engine using pure Python and SciPy assignment.
Computes detection metrics (Precision, Recall, F1), tracking metrics
(MOTA, IDF1, ID Switches), counting accuracy, and business metrics (Dwell Time Error).
"""

import numpy as np
from typing import Dict, List, Tuple, Set
from scipy.optimize import linear_sum_assignment

def _iou(a: List[float], b: List[float]) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter == 0.0:
        return 0.0
    aa = (a[2] - a[0]) * (a[3] - a[1])
    ab = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (aa + ab - inter + 1e-9)

class TrackingEvaluator:
    def __init__(self, iou_threshold: float = 0.50):
        self.iou_threshold = iou_threshold

    def evaluate_clip(
        self,
        predictions: Dict[int, List[Tuple[int, List[float], float, str]]],
        ground_truth: Dict[int, List[Dict[str, any]]]
    ) -> Dict[str, any]:
        """
        Calculates MOTA, IDF1, ID Switches, Precision, Recall, and Counting Accuracy.
        
        Parameters:
        -----------
        predictions: Dict[frame_id, List[(track_id, bbox, conf, role)]]
        ground_truth: Dict[frame_id, List[{"bbox": [x1,y1,x2,y2], "track_id": int, "class_id": int}]]
        """
        # Collect unique frames in evaluation
        all_frames = sorted(list(set(predictions.keys()) | set(ground_truth.keys())))
        
        # MOT metrics counters
        total_gt_boxes = 0
        total_pred_boxes = 0
        false_negatives = 0
        false_positives = 0
        id_switches = 0
        
        # Track maps
        prev_matches = {}  # gt_id -> pred_id
        
        # Re-ID IDF1 accumulation metrics
        gt_track_spans = {}   # gt_id -> set(frame_id)
        pred_track_spans = {} # pred_id -> set(frame_id)
        identity_matches = {} # (gt_id, pred_id) -> match_count
        
        # Counting and dwell time metrics accumulation
        gt_dwells = {}        # gt_id -> {entry_ts, exit_ts, role}
        pred_dwells = {}      # pred_id -> {entry_ts, exit_ts, role}
        
        # Fill ground truth lifecycle spans
        for fid in all_frames:
            gt_list = ground_truth.get(fid, [])
            for gt in gt_list:
                gt_id = gt["track_id"]
                gt_track_spans.setdefault(gt_id, set()).add(fid)
                
            pred_list = predictions.get(fid, [])
            for pr in pred_list:
                pred_id = pr[0]
                pred_track_spans.setdefault(pred_id, set()).add(fid)

        # ── Frame-by-frame Matching Loop ─────────────────────────────────────
        for fid in all_frames:
            gt_list = ground_truth.get(fid, [])
            pred_list = predictions.get(fid, [])
            
            total_gt_boxes += len(gt_list)
            total_pred_boxes += len(pred_list)
            
            if not gt_list:
                false_positives += len(pred_list)
                continue
            if not pred_list:
                false_negatives += len(gt_list)
                # clear previous matching history
                for gt in gt_list:
                    prev_matches.pop(gt["track_id"], None)
                continue
                
            # Build cost assignment matrix based on IoU distance (1.0 - IoU)
            n_gt = len(gt_list)
            n_pr = len(pred_list)
            cost = np.ones((n_gt, n_pr), dtype=np.float64)
            for i, gt in enumerate(gt_list):
                for j, pr in enumerate(pred_list):
                    cost[i, j] = 1.0 - _iou(gt["bbox"], pr[1])
                    
            # Perform Hungarian assignment
            rows, cols = linear_sum_assignment(cost)
            matched_gt = set()
            matched_pr = set()
            
            for r, c in zip(rows, cols):
                if cost[r, c] < (1.0 - self.iou_threshold):
                    matched_gt.add(r)
                    matched_pr.add(c)
                    
                    gt_id = gt_list[r]["track_id"]
                    pred_id = pred_list[c][0]
                    
                    # Accumulate matches for IDF1
                    identity_matches[(gt_id, pred_id)] = identity_matches.get((gt_id, pred_id), 0) + 1
                    
                    # Check for ID switch
                    if gt_id in prev_matches:
                        if prev_matches[gt_id] != pred_id:
                            id_switches += 1
                    prev_matches[gt_id] = pred_id
                    
            # Log missed ground truth detections as False Negatives
            for i, gt in enumerate(gt_list):
                if i not in matched_gt:
                    false_negatives += 1
                    prev_matches.pop(gt["track_id"], None)  # delete link
                    
            # Log unmatched predictions as False Positives
            for j, pr in enumerate(pred_list):
                if j not in matched_pr:
                    false_positives += 1

        # ── 1. Calculate MOTA ──────────────────────────────────────────────────
        mota = 1.0 - (false_negatives + false_positives + id_switches) / max(total_gt_boxes, 1)
        mota = max(0.0, mota)

        # ── 2. Calculate IDF1 ──────────────────────────────────────────────────
        # IDF1 optimal mapping: Match complete ground truth tracks to complete predicted tracks
        unique_gt_ids = list(gt_track_spans.keys())
        unique_pred_ids = list(pred_track_spans.keys())
        
        n_gt_tracks = len(unique_gt_ids)
        n_pr_tracks = len(unique_pred_ids)
        
        # Build global ID match cost matrix using match length overlaps
        idf1_cost = np.zeros((n_gt_tracks, n_pr_tracks), dtype=np.float64)
        for i, g_id in enumerate(unique_gt_ids):
            for j, p_id in enumerate(unique_pred_ids):
                overlap = identity_matches.get((g_id, p_id), 0)
                len_sum = len(gt_track_spans[g_id]) + len(pred_track_spans[p_id])
                # cost is cost matrix, lower = better, so minimize difference
                idf1_cost[i, j] = len_sum - 2.0 * overlap
                
        # Perform assignment optimization for IDF1 mapping
        best_overlap_sum = 0
        if n_gt_tracks > 0 and n_pr_tracks > 0:
            rows_id, cols_id = linear_sum_assignment(idf1_cost)
            for r, c in zip(rows_id, cols_id):
                g_id = unique_gt_ids[r]
                p_id = unique_pred_ids[c]
                best_overlap_sum += identity_matches.get((g_id, p_id), 0)
                
        # IDF1 = 2 * IDTP / (2 * IDTP + IDFP + IDFN)
        # IDTP is simply the sum of overlapping frames mapped between matched IDs
        idtp = best_overlap_sum
        idfp = total_pred_boxes - idtp
        idfn = total_gt_boxes - idtp
        idf1 = (2.0 * idtp) / max(2.0 * idtp + idfp + idfn, 1.0)

        # ── 3. Calculate Detection Metrics ──────────────────────────────────────
        tp = total_gt_boxes - false_negatives
        precision = tp / max(tp + false_positives, 1)
        recall = tp / max(tp + false_negatives, 1)
        f1_score = (2.0 * precision * recall) / max(precision + recall, 1e-9)

        # ── 4. Calculate Counting & Semantic Accuracy ─────────────────────────
        # Separate guest vs staff totals
        gt_unique_ids = set(unique_gt_ids)
        pred_unique_ids = set(unique_pred_ids)
        
        gt_guests = set()
        gt_staff = set()
        for fid in all_frames:
            for gt in ground_truth.get(fid, []):
                if gt["class_id"] == 2:  # staff
                    gt_staff.add(gt["track_id"])
                else:
                    gt_guests.add(gt["track_id"])
                    
        # Remove staff from guest count if they were classified as both to keep clean
        gt_guests -= gt_staff
        
        # Extract unique prediction role assignments (majority class per track)
        pred_roles = {}
        for fid in all_frames:
            for pr in predictions.get(fid, []):
                pred_roles.setdefault(pr[0], []).append(pr[3])
                
        pred_guests = set()
        pred_staff = set()
        for p_id, roles in pred_roles.items():
            is_staff = roles.count("staff") >= roles.count("guest")
            if is_staff:
                pred_staff.add(p_id)
            else:
                pred_guests.add(p_id)

        # Absolute Counting Accuracy (ACA) for Guests
        gt_count = len(gt_guests)
        pred_count = len(pred_guests)
        counting_accuracy = 1.0 - (abs(pred_count - gt_count) / max(gt_count, 1))
        counting_accuracy = max(0.0, counting_accuracy)

        # Ghost tracks: predictions that never match any real person
        ghost_tracks = 0
        for p_id in unique_pred_ids:
            has_match = any(identity_matches.get((g_id, p_id), 0) > 0 for g_id in unique_gt_ids)
            if not has_match:
                ghost_tracks += 1

        return {
            "mota": float(mota),
            "idf1": float(idf1),
            "id_switches": int(id_switches),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1_score),
            "gt_unique_guests": int(gt_count),
            "pred_unique_guests": int(pred_count),
            "gt_unique_staff": int(len(gt_staff)),
            "pred_unique_staff": int(len(pred_staff)),
            "counting_accuracy": float(counting_accuracy),
            "ghost_tracks": int(ghost_tracks),
            "total_frames": int(len(all_frames))
        }
