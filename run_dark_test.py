"""
run_dark_test.py — Production tracking pipeline for Dark_lighting.mp4
======================================================================
Uses the clean v6-restored ByteTracker for precise person tracking.

Usage
-----
    ./venv/bin/python run_dark_test.py [--debug] [--log-diagnostics]

Flags
-----
  --debug            : Overlay track hits & confidence on bounding boxes.
  --log-diagnostics  : Write per-frame diagnostic JSON to pipeline_diag_<ts>.json
  --video            : Path to input video (default: Dark_lighting.mp4)
  --output           : Path to output video (default: output_dark_lighting.mp4)
  --conf             : YOLO detection confidence threshold (default: 0.25)
  --fps-target       : Target FPS for frame sampling (default: 8)
"""

import argparse
import json
import time
import sys
from datetime import datetime, timedelta

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from ingestion.frame_sampler import stream_frames
from byte_tracker import ByteTracker
from restaurant_analytics.visit_manager import VisitManager
from restaurant_analytics.zone_mapper import ZoneMapper
from pipeline_position import load_zones

# ──────────────────────────────────────────────────────────────────────────────
# Visual constants
# ──────────────────────────────────────────────────────────────────────────────
COLOR_GUEST_CONFIRMED = (0, 165, 255)   # Orange – confirmed guest
COLOR_GUEST_TENTATIVE = (60, 100, 180)  # Muted blue-grey – tentative
COLOR_STAFF_CONFIRMED = (0, 220, 0)     # Green – confirmed staff
COLOR_STAFF_TENTATIVE = (0, 130, 0)     # Dim green – tentative
COLOR_TEXT            = (255, 255, 255)
COLOR_BG_STATS        = (20, 20, 20)


def pick_color(role, confirmed):
    if role == "staff":
        return COLOR_STAFF_CONFIRMED if confirmed else COLOR_STAFF_TENTATIVE
    return COLOR_GUEST_CONFIRMED if confirmed else COLOR_GUEST_TENTATIVE


# ──────────────────────────────────────────────────────────────────────────────
# NMS helper – remove duplicate / overlapping detections before tracking
# ──────────────────────────────────────────────────────────────────────────────
def apply_nms(bboxes, confs, iou_threshold=0.50):
    """Greedy NMS. Returns kept indices sorted by confidence (high → low)."""
    if not bboxes:
        return []
    order = sorted(range(len(confs)), key=lambda i: confs[i], reverse=True)
    kept = []
    while order:
        i = order.pop(0)
        kept.append(i)
        suppress = []
        for j in order:
            a, b = bboxes[i], bboxes[j]
            ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
            ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
            inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
            if inter > 0:
                area_a = (a[2]-a[0]) * (a[3]-a[1])
                area_b = (b[2]-b[0]) * (b[3]-b[1])
                iou = inter / (area_a + area_b - inter + 1e-9)
                if iou > iou_threshold:
                    suppress.append(j)
        order = [x for x in order if x not in suppress]
    return kept


# ──────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ──────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug",           action="store_true",
                        help="Overlay hits & confidence on bounding boxes")
    parser.add_argument("--log-diagnostics", action="store_true",
                        help="Write per-frame JSON diagnostics")
    parser.add_argument("--video",           default="Dark_lighting.mp4")
    parser.add_argument("--output",          default="output_dark_lighting.mp4")
    parser.add_argument("--model",           default="yolo11m.pt",
                        help="YOLO model weights file")
    parser.add_argument("--conf",            type=float, default=0.20,
                        help="YOLO detection confidence threshold")
    parser.add_argument("--fps-target",      type=int,   default=8)
    args = parser.parse_args()

    video_path  = args.video
    output_path = args.output

    # ── Device ────────────────────────────────────────────────────────────────
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"
    print(f"[init] Device: {device}")

    # ── Model ─────────────────────────────────────────────────────────────────
    print(f"[init] Loading {args.model} ...")
    detector = YOLO(args.model)
    print(f"[init] Model loaded: {args.model}")

    # ── Tracker ───────────────────────────────────────────────────────────────
    # v6-restored: sensible defaults tuned for dark CCTV footage at 8fps.
    tracker = ByteTracker(
        max_dist_active=180,    # ~3 seat-widths; enough for normal motion
        max_dist_lost=120,      # tighter re-link for lost tracks
        max_missing=90,         # ~11s gap bridge at 8fps (not 60s!)
        min_hits=3,             # show track on screen after 3 detections
        count_min_hits=6,       # count toward totals after 6 detections
        active_window=8,        # frames before a track moves to 'lost'
        velocity_alpha=0.30,    # gentle velocity smoothing
        velocity_damp=0.80,     # velocity fades when track goes missing
        high_conf_thresh=0.30,  # lower for dark footage (yolo11m clusters 0.20-0.45)
        iou_thresh_active=0.15,
        iou_thresh_lost=0.10,
    )

    # ── State ─────────────────────────────────────────────────────────────────
    token_final_class  = {}   # track_id -> "guest" | "staff"
    cumulative_guests  = set()
    cumulative_staff   = set()

    # Milestone 2 & Phase 2 Integration
    visit_manager = VisitManager()
    zone_mapper = ZoneMapper(load_zones())
    VIDEO_START = datetime.now()

    # Service zone coordinates (scaled for 1920x1080 Dark_lighting.mp4)
    # Staff tend to occupy this zone behind the service counter.
    SERVICE_ZONE = (540.0, 270.0, 723.0, 540.0)   # (x_min, y_min, x_max, y_max)
    MOTION_RATIO_STAFF = 0.18     # staff have >=18% of displacements > 25px
    MOTION_MIN_FRAMES  = 15       # need >=15 frames before classifying by motion

    diag_frames = [] if args.log_diagnostics else None

    writer      = None
    frame_count = 0
    t_start     = time.time()

    print(f"[run ] Processing {video_path} at {args.fps_target} fps_target ...")
    for fid, ts, frame in stream_frames(video_path, fps_target=args.fps_target):

        # ── Video writer init ──────────────────────────────────────────────
        if writer is None:
            h, w = frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(output_path, fourcc, args.fps_target, (w, h))

        # ── Detection ─────────────────────────────────────────────────────
        # classes=[0] filters to COCO person class only (no chairs/bottles)
        yolo_results = detector(frame, conf=args.conf, verbose=False,
                                device=device, classes=[0])
        raw_bboxes = []
        raw_confs  = []

        for box in yolo_results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            # Skip bboxes too small to be a real person
            if (y2 - y1) < 25:
                continue
            raw_bboxes.append([x1, y1, x2, y2])
            raw_confs.append(conf)

        # ── NMS (remove overlapping duplicates) ────────────────────────────
        kept   = apply_nms(raw_bboxes, raw_confs, iou_threshold=0.50)
        bboxes = [raw_bboxes[i] for i in kept]
        confs  = [raw_confs[i]  for i in kept]

        # Build detection format expected by ByteTracker: [x1,y1,x2,y2,conf]
        detections = [[*bboxes[i], confs[i]] for i in range(len(bboxes))]

        # ── Tracking ──────────────────────────────────────────────────────
        log_lines    = [] if args.log_diagnostics else None
        track_results = tracker.update(detections, fid, ts, log_lines=log_lines)
        # track_results: list of (track_id, bbox, conf, confirmed, countable)

        # ── Motion-based staff/guest classification ─────────────────────────
        # Uses displacement history to separate staff (high motion / service zone)
        # from guests (seated, low motion).
        for (tid, t_bbox, t_conf, confirmed, countable) in track_results:
            tr = tracker.tracks.get(tid)
            if tr is None:
                continue
            history = tr["history"]
            role = "guest"  # default

            if len(history) >= MOTION_MIN_FRAMES:
                # Compute frame-to-frame displacements
                pts = np.array(history)
                disps = np.sqrt(np.sum(np.diff(pts, axis=0) ** 2, axis=1))
                high_motion_ratio = np.mean(disps > 25.0)

                if high_motion_ratio >= MOTION_RATIO_STAFF:
                    role = "staff"
                else:
                    # Check if mean position is in the service zone
                    mean_x, mean_y = pts[:, 0].mean(), pts[:, 1].mean()
                    sx1, sy1, sx2, sy2 = SERVICE_ZONE
                    if sx1 <= mean_x <= sx2 and sy1 <= mean_y <= sy2:
                        role = "staff"

            token_final_class[tid] = role
            
            dt_ts = VIDEO_START + timedelta(seconds=ts)
            visit = visit_manager.get_visit(tid)
            if not visit:
                visit = visit_manager.handle_track_start(tid, dt_ts, role=role, camera_id=video_path)
            else:
                visit.update_role(role, dt_ts)

            # Update zone
            current_z = zone_mapper.get_zone_for_bbox(t_bbox)
            visit.update_zone(current_z, dt_ts)

            # Only count tracks that have been seen enough times (countable flag)
            if countable:
                if role == "staff":
                    cumulative_staff.add(tid)
                    cumulative_guests.discard(tid)
                else:
                    if tid not in cumulative_staff:
                        cumulative_guests.add(tid)

        # ── Drawing ───────────────────────────────────────────────────────
        for (tid, t_bbox, t_conf, confirmed, countable) in track_results:
            # Only draw confirmed tracks to avoid cluttering screen with ghosts
            if not confirmed:
                continue

            role  = token_final_class.get(tid, "guest")
            color = pick_color(role, confirmed)
            x1, y1, x2, y2 = [int(v) for v in t_bbox]

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            if args.debug:
                tr    = tracker.tracks.get(tid)
                hits  = tr["hits"] if tr else 0
                label = f"#{tid} {role[0].upper()} h={hits} c={t_conf:.2f}"
            else:
                label = f"#{tid} {role}"

            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(frame,
                          (x1, max(y1 - 18, 0)),
                          (x1 + tw + 4, max(y1 - 2, 0)),
                          color, -1)
            cv2.putText(frame, label,
                        (x1 + 2, max(y1 - 5, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

        # ── Dashboard overlay ──────────────────────────────────────────────
        n_covers = len(cumulative_guests)
        n_staff  = len(cumulative_staff)
        active_g = sum(1 for (tid, *rest) in track_results
                       if token_final_class.get(tid) == "guest" and rest[2])  # confirmed
        active_s = sum(1 for (tid, *rest) in track_results
                       if token_final_class.get(tid) == "staff" and rest[2])  # confirmed

        dash_x1, dash_y1, dash_x2, dash_y2 = 10, 10, 430, 115
        cv2.rectangle(frame, (dash_x1, dash_y1), (dash_x2, dash_y2), COLOR_BG_STATS, -1)
        cv2.rectangle(frame, (dash_x1, dash_y1), (dash_x2, dash_y2), (80, 80, 80), 1)

        cv2.putText(frame, "CUSTOMER INTELLIGENCE LIVE SCAN",
                    (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 200, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Covers (Guests): {n_covers}  |  Staff: {n_staff}",
                    (20, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.58, COLOR_TEXT, 2, cv2.LINE_AA)
        cv2.putText(frame, f"Active in Frame: {active_g} Guest(s), {active_s} Staff",
                    (20, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (200, 200, 200), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Video Time: {ts:.1f}s | Frame: {fid} | Tracks: {len(tracker.tracks)}",
                    (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (130, 130, 130), 1, cv2.LINE_AA)

        # ── Diagnostics ────────────────────────────────────────────────────
        if diag_frames is not None:
            diag_frames.append({
                "frame_id":       fid,
                "ts":             round(ts, 3),
                "n_raw_det":      len(raw_bboxes),
                "n_det_post_nms": len(bboxes),
                "confs":          [round(c, 3) for c in confs],
                "n_tracks":       len(track_results),
                "n_active_tracker": tracker.get_active_count(),
                "log":            log_lines or [],
            })

        writer.write(frame)
        frame_count += 1

        if frame_count % 50 == 0:
            elapsed     = time.time() - t_start
            fps_actual  = frame_count / elapsed
            print(
                f"[{ts:6.1f}s | fid={fid:5d}] "
                f"dets={len(bboxes):2d} tracks={len(track_results):2d} "
                f"active={tracker.get_active_count():3d} "
                f"covers={n_covers} staff={n_staff} "
                f"({fps_actual:.1f} fps)"
            )

    # ── Finalise ───────────────────────────────────────────────────────────
    if writer:
        writer.release()
        
    for tid in list(visit_manager.active_visits.keys()):
        visit_manager.handle_track_end(tid, VIDEO_START + timedelta(seconds=elapsed if 'elapsed' in locals() else 0))

    elapsed = time.time() - t_start
    print(f"\n[done] {frame_count} frames processed in {elapsed:.1f}s "
          f"({frame_count/elapsed:.1f} fps avg)")
    print(f"[done] Output: {output_path}")
    print(f"[done] Final -> Covers (Guests): {len(cumulative_guests)} | Staff: {len(cumulative_staff)}")
    print(f"[done] Total unique track IDs ever created: {tracker.next_id - 1}")

    if diag_frames is not None:
        diag_path = f"pipeline_diag_{int(time.time())}.json"
        with open(diag_path, "w") as f:
            json.dump(diag_frames, f, indent=2)
        print(f"[diag] Diagnostics written to {diag_path}")


if __name__ == "__main__":
    main()
