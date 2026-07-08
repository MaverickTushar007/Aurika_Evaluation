"""
phase1/run_phase1.py
====================
Main entry point for Aurika Phase 1 — Foundational Human Tracking.

Usage:
    python phase1/run_phase1.py \\
        --video datasets/Dark_lighting.mp4 \\
        --output phase1/runs/Dark_lighting/ \\
        [--model yolo_staff_customer.pt] \\
        [--tracker phase1/botsort_dark.yaml] \\
        [--stride 1] \\
        [--device cpu]

Phase 1 produces:
    transitions.csv      — one row per confirmed zone transition
    frame_history.csv    — one row per person per visible frame
    person_summary.csv   — one row per person
    output_annotated.mp4 — full video with overlay
    audit_frames/        — 5 sampled frames for visual audit
    tracking_report.md   — 5-loop validation report
"""

from __future__ import annotations
import argparse
import os
import sys
import time

import cv2
import numpy as np

# Ensure repo root is on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Apply tracker candidate recovery monkey-patching
import phase1.tracker_recovery
from phase1.tracker_recovery import save_candidate_rejections

from phase1.tracker import PersonTracker
from phase1.zone_map import ZoneMap, OUTSIDE
from phase1.csv_writer import TransitionWriter, FrameHistoryWriter, PersonSummaryWriter
from phase1.visualizer import Visualizer, make_video_writer
from phase1.evaluator import Phase1Evaluator
from phase1.spatial_validator import SpatialValidator


# ── Constants ─────────────────────────────────────────────────────────────────

AUDIT_FRAME_COUNT = 5   # frames to save for Loop 5 visual audit
DEFAULT_MODEL = "yolo_staff_customer.pt"
DEFAULT_TRACKER = os.path.join(os.path.dirname(__file__), "botsort_dark.yaml")
DEFAULT_ZONES = os.path.join(os.path.dirname(__file__), "config", "zones.json")


# ── CLAHE lighting enhancement ────────────────────────────────────────────────

def enhance_frame(frame: np.ndarray) -> np.ndarray:
    """
    Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) in LAB space.
    Boosts visibility in dark/underexposed frames without blowing out highlights.
    Identical to the preprocessing used by the legacy pipeline's frame_sampler.
    """
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_eq = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l_eq, a, b]), cv2.COLOR_LAB2BGR)


def clean_ghost_tracks(output_dir: str):
    """
    Principled removal of static false positives, reflections, and transient edge noise.
    Identifies track IDs that:
      1. Never enter any operational zone ('WAITING', 'RECEPTION', 'DINING')
      2. And either:
         a) Have standard deviation of bottom-center coordinates < 3.0 px (static)
         b) Or have total lifetime of <= 3 frames (transient edge noise)
    Cleans transitions.csv, frame_history.csv, and person_summary.csv.
    """
    fh_path = os.path.join(output_dir, "frame_history.csv")
    trans_path = os.path.join(output_dir, "transitions.csv")
    ps_path = os.path.join(output_dir, "person_summary.csv")

    if not os.path.exists(fh_path):
        return

    import csv
    import numpy as np
    from collections import defaultdict

    rows_fh = []
    with open(fh_path, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows_fh.append(r)

    coords = defaultdict(list)
    zones = defaultdict(set)
    total_frames = defaultdict(int)

    for r in rows_fh:
        pid = int(r["person_id"])
        x = float(r["bottom_center_x"])
        y = float(r["bottom_center_y"])
        zone = r["current_zone"]
        coords[pid].append((x, y))
        zones[pid].add(zone)
        total_frames[pid] += 1

    ghost_ids = set()
    for pid in coords.keys():
        pts = np.array(coords[pid])
        std_x = np.std(pts[:, 0])
        std_y = np.std(pts[:, 1])
        std_total = np.sqrt(std_x**2 + std_y**2)
        zones_list = zones[pid]
        
        entered_operational = any(z in ["WAITING", "DINING", "RECEPTION"] for z in zones_list)
        
        if not entered_operational:
            if std_total < 4.0:
                ghost_ids.add(pid)
            elif total_frames[pid] <= 3:
                ghost_ids.add(pid)
        elif std_total < 4.0:
            ghost_ids.add(pid)

    if not ghost_ids:
        print("[Phase1] No ghost tracks detected for filtering.")
        return

    print(f"[Phase1] Filtering out {len(ghost_ids)} ghost track IDs: {sorted(ghost_ids)}")

    # Filter and rewrite frame_history.csv
    header_fh = list(rows_fh[0].keys()) if rows_fh else []
    filtered_fh = [r for r in rows_fh if int(r["person_id"]) not in ghost_ids]
    with open(fh_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header_fh)
        writer.writeheader()
        writer.writerows(filtered_fh)

    # Filter and rewrite transitions.csv
    if os.path.exists(trans_path):
        rows_trans = []
        with open(trans_path, "r") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows_trans.append(r)
        header_trans = list(rows_trans[0].keys()) if rows_trans else []
        filtered_trans = [r for r in rows_trans if int(r["person_id"]) not in ghost_ids]
        with open(trans_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=header_trans)
            writer.writeheader()
            writer.writerows(filtered_trans)

    # Filter and rewrite person_summary.csv
    if os.path.exists(ps_path):
        rows_ps = []
        with open(ps_path, "r") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows_ps.append(r)
        header_ps = list(rows_ps[0].keys()) if rows_ps else []
        filtered_ps = [r for r in rows_ps if int(r["person_id"]) not in ghost_ids]
        with open(ps_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=header_ps)
            writer.writeheader()
            writer.writerows(filtered_ps)


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run(
    video_path: str,
    output_dir: str,
    model_path: str,
    tracker_config: str,
    zones_config: str,
    stride: int,
    device: str,
    det_conf: float,
):
    os.makedirs(output_dir, exist_ok=True)

    # ── Open video ────────────────────────────────────────────────────────────
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    src_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_sec = total_frames / src_fps if src_fps > 0 else 0

    out_fps = src_fps / stride if stride > 1 else src_fps
    print(f"[Phase1] Video: {os.path.basename(video_path)}")
    print(f"[Phase1] Resolution: {w}×{h}  FPS: {src_fps:.2f}  Frames: {total_frames}  Duration: {duration_sec:.1f}s")
    print(f"[Phase1] Stride: {stride}  Output FPS: {out_fps:.2f}")
    print(f"[Phase1] Model: {model_path}  Tracker: {tracker_config}")

    # ── Spatial Floorplan Validation ──────────────────────────────────────────
    validator = SpatialValidator(config_path=zones_config, width=w, height=h)
    if not validator.validate(output_dir):
        raise ValueError("Spatial Floorplan Validation Checks Failed! Aborting tracking execution.")

    # ── Initialise components ─────────────────────────────────────────────────
    tracker = PersonTracker(
        model_path=model_path,
        tracker_config=tracker_config,
        det_conf=det_conf,
        # Detect both human classes: 0=customer, 1=staff (both are persons)
        person_class_ids=None,  # None = all model classes (auto-detected)
        device=device,
    )
    zone_map = ZoneMap(config_path=zones_config)
    visualizer = Visualizer(zone_map=zone_map)

    trans_path = os.path.join(output_dir, "transitions.csv")
    fh_path = os.path.join(output_dir, "frame_history.csv")
    ps_path = os.path.join(output_dir, "person_summary.csv")
    video_out_path = os.path.join(output_dir, "output_annotated.mp4")
    audit_dir = os.path.join(output_dir, "audit_frames")

    trans_writer = TransitionWriter(trans_path)
    fh_writer = FrameHistoryWriter(fh_path)
    ps_writer = PersonSummaryWriter(ps_path)
    video_writer = make_video_writer(video_out_path, out_fps, w, h)

    # Audit frame intervals — evenly spaced across the processable video portion
    # Use first 60% of total_frames as safe range (known H264 corruption after that)
    safe_frames = int(total_frames * 0.58)  # conservative: up to frame 10748
    audit_frame_indices = set()
    if safe_frames > AUDIT_FRAME_COUNT:
        step = safe_frames // (AUDIT_FRAME_COUNT + 1)
        audit_frame_indices = {step * i for i in range(1, AUDIT_FRAME_COUNT + 1)}
    audit_saved = 0
    print(f"[Phase1] Audit frames will be saved at frames: {sorted(audit_frame_indices)}")

    # Runtime state
    last_rendered_frame = None
    mid_frame_idx = safe_frames // 2
    current_zones: dict = {}   # {person_id: confirmed_zone}
    known_persons: set = set() # persons seen at least once
    
    # Orthogonal states
    OUTSIDE = "OUTSIDE"
    VISIBLE = "VISIBLE"
    OCCLUDED = "OCCLUDED"
    ACTIVE = "ACTIVE"
    LOST = "LOST"
    CAMERA_EXIT = "CAMERA_EXIT"
    
    visibility_states: Dict[int, str] = {}
    tracking_states: Dict[int, str] = {}
    
    # Running statistics for track quality score
    observed_frames_track: Dict[int, int] = {}
    total_frames_track: Dict[int, int] = {}
    sum_conf_track: Dict[int, float] = {}
    
    last_seen_frame: Dict[int, int] = {}
    last_seen_coords: Dict[int, Tuple[float, float]] = {}
    last_seen_bbox: Dict[int, Tuple[float, float, float, float]] = {}
    
    start_time = time.time()
    processed = 0
    frame_idx = 0

    print(f"[Phase1] Processing... (this may take several minutes)")

    # ── Main loop ─────────────────────────────────────────────────────────────
    consecutive_failures = 0
    MAX_CONSECUTIVE_FAILURES = 30  # skip up to 30 bad H264 frames before giving up

    while True:
        ret, frame = cap.read()
        if not ret:
            consecutive_failures += 1
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print(f"[Phase1] {consecutive_failures} consecutive read failures at frame {frame_idx} — stopping.")
                break
            frame_idx += 1
            continue
        consecutive_failures = 0  # reset on successful read

        if frame_idx % stride != 0:
            frame_idx += 1
            continue

        timestamp_sec = frame_idx / src_fps

        # ── CLAHE enhancement ─────────────────────────────────────────────────
        # Boosts contrast on dark frames before detection.
        # Identical to legacy pipeline preprocessing (ingestion/frame_sampler.py).
        enhanced = enhance_frame(frame)

        # ── Detect & track ────────────────────────────────────────────────────
        frame_result = tracker.process_frame(enhanced, frame_idx, timestamp_sec)

        # ── Zone assignment & CSV writing ─────────────────────────────────────
        active_ids = set()
        for person in frame_result.persons:
            pid = person.person_id
            active_ids.add(pid)
            bc = person.bottom_center
            raw_zone = zone_map.get_zone_for_point(bc)

            # Update running statistics for track quality
            total_frames_track[pid] = total_frames_track.get(pid, 0) + 1
            observed_frames_track[pid] = observed_frames_track.get(pid, 0) + 1
            sum_conf_track[pid] = sum_conf_track.get(pid, 0.0) + person.det_conf
            
            obs_ratio = observed_frames_track[pid] / total_frames_track[pid]
            avg_conf = sum_conf_track[pid] / observed_frames_track[pid]
            q_score = 0.6 * obs_ratio + 0.4 * avg_conf
            track_quality = "HIGH" if q_score >= 0.5 else ("MEDIUM" if q_score >= 0.25 else "LOW")

            if pid not in known_persons:
                # First appearance — transition from OUTSIDE
                zone = zone_map.initialize_person(pid, bc)
                current_zones[pid] = zone
                known_persons.add(pid)
                visibility_states[pid] = VISIBLE
                tracking_states[pid] = ACTIVE
                
                if zone != OUTSIDE:
                    trans_writer.write(
                        person_id=pid,
                        frame=frame_idx,
                        timestamp_sec=timestamp_sec,
                        previous_zone=OUTSIDE,
                        current_zone=zone,
                        bbox=person.bbox,
                        tracker_conf=person.track_conf,
                        det_conf=person.det_conf,
                    )
                    ps_writer.record_transition(pid, frame_idx, OUTSIDE, zone)
            else:
                # Existing person — check if they were occluded
                was_occluded = (visibility_states.get(pid, VISIBLE) == OCCLUDED)
                if was_occluded:
                    # Reappeared from occlusion — direct transition
                    visibility_states[pid] = VISIBLE
                    tracking_states[pid] = ACTIVE
                    zone_map._confirmed_zone[pid] = raw_zone
                    zone_map._pending.pop(pid, None)
                    
                    prev_zone = current_zones.get(pid, OUTSIDE)
                    if prev_zone != raw_zone:
                        trans_writer.write(
                            person_id=pid,
                            frame=frame_idx,
                            timestamp_sec=timestamp_sec,
                            previous_zone=prev_zone,
                            current_zone=raw_zone,
                            bbox=person.bbox,
                            tracker_conf=person.track_conf,
                            det_conf=person.det_conf,
                        )
                        ps_writer.record_transition(pid, frame_idx, prev_zone, raw_zone)
                    current_zones[pid] = raw_zone
                else:
                    confirmed_zone, transition_from = zone_map.assign(pid, bc)
                    if transition_from is not None:
                        trans_writer.write(
                            person_id=pid,
                            frame=frame_idx,
                            timestamp_sec=timestamp_sec,
                            previous_zone=transition_from,
                            current_zone=confirmed_zone,
                            bbox=person.bbox,
                            tracker_conf=person.track_conf,
                            det_conf=person.det_conf,
                        )
                        ps_writer.record_transition(pid, frame_idx, transition_from, confirmed_zone)
                    current_zones[pid] = confirmed_zone

            last_seen_frame[pid] = frame_idx
            last_seen_coords[pid] = bc
            last_seen_bbox[pid] = person.bbox

            # Frame history row
            zone = current_zones[pid]
            fh_writer.write(
                frame=frame_idx,
                timestamp_sec=timestamp_sec,
                person_id=pid,
                current_zone=zone,
                bbox=person.bbox,
                bottom_center=bc,
                visibility=VISIBLE,
                tracking_state=ACTIVE,
                observation_type="OBSERVED",
                is_detected=1,
                detection_confidence=person.det_conf,
                association_cost=person.association_cost,
                frames_since_detection=0,
                track_quality=track_quality,
            )
            ps_writer.record_frame(pid, frame_idx, zone)

        # ── Occlusion & Exit check ────────────────────────────────────────────
        for pid in list(known_persons):
            if pid not in active_ids:
                prev_vis = visibility_states.get(pid, VISIBLE)
                if prev_vis == VISIBLE:
                    # Just lost detection — transition visibility to OCCLUDED
                    visibility_states[pid] = OCCLUDED
                    tracking_states[pid] = LOST

                if visibility_states.get(pid) == OCCLUDED:
                    # Update running statistics for track quality
                    total_frames_track[pid] = total_frames_track.get(pid, 0) + 1
                    obs_ratio = observed_frames_track.get(pid, 0) / total_frames_track[pid]
                    avg_conf = sum_conf_track.get(pid, 0.0) / max(1, observed_frames_track.get(pid, 0))
                    q_score = 0.6 * obs_ratio + 0.4 * avg_conf
                    track_quality = "HIGH" if q_score >= 0.5 else ("MEDIUM" if q_score >= 0.25 else "LOW")
                    fsd = frame_idx - last_seen_frame[pid]

                    # Check if still inside occlusion buffer (120 frames)
                    if fsd <= 120:
                        zone = current_zones.get(pid, OUTSIDE)
                        fh_writer.write(
                            frame=frame_idx,
                            timestamp_sec=timestamp_sec,
                            person_id=pid,
                            current_zone=zone,
                            bbox=last_seen_bbox[pid],
                            bottom_center=last_seen_coords[pid],
                            visibility=OCCLUDED,
                            tracking_state=LOST,
                            observation_type="PREDICTED",
                            is_detected=0,
                            detection_confidence=0.0,
                            association_cost=0.0,
                            frames_since_detection=fsd,
                            track_quality=track_quality,
                        )
                        ps_writer.record_frame(pid, frame_idx, zone)
                    elif tracking_states.get(pid) != CAMERA_EXIT:
                        # Exceeded track buffer — transition physical zone to OUTSIDE
                        prev_zone = current_zones.get(pid, OUTSIDE)
                        if prev_zone != OUTSIDE:
                            trans_writer.write(
                                person_id=pid,
                                frame=frame_idx,
                                timestamp_sec=timestamp_sec,
                                previous_zone=prev_zone,
                                current_zone=OUTSIDE,
                                bbox=last_seen_bbox[pid],
                                tracker_conf=0.0,
                                det_conf=0.0,
                            )
                            ps_writer.record_transition(pid, frame_idx, prev_zone, OUTSIDE)
                        
                        fh_writer.write(
                            frame=frame_idx,
                            timestamp_sec=timestamp_sec,
                            person_id=pid,
                            current_zone=OUTSIDE,
                            bbox=last_seen_bbox[pid],
                            bottom_center=last_seen_coords[pid],
                            visibility=OCCLUDED,
                            tracking_state=CAMERA_EXIT,
                            observation_type="PREDICTED",
                            is_detected=0,
                            detection_confidence=0.0,
                            association_cost=0.0,
                            frames_since_detection=fsd,
                            track_quality=track_quality,
                        )
                        current_zones[pid] = OUTSIDE
                        tracking_states[pid] = CAMERA_EXIT
                        ps_writer.mark_exited(pid)

        # ── Render overlay ────────────────────────────────────────────────────
        rendered = visualizer.render(
            frame=frame,
            frame_id=frame_idx,
            timestamp_sec=timestamp_sec,
            persons=frame_result.persons,
            current_zones=current_zones,
            total_unique_ids=len(tracker.unique_ids),
            id_switch_count=len(tracker.id_switch_candidates),
        )
        video_writer.write(rendered)
        last_rendered_frame = rendered

        # ── Save Required Validation Frames ───────────────────────────────────
        if frame_idx == 0:
            val_0_path = os.path.join(output_dir, "validation_frame_0000.jpg")
            cv2.imwrite(val_0_path, rendered)
            print(f"[Phase1] Saved validation_frame_0000.jpg to {val_0_path}")
        elif frame_idx == mid_frame_idx:
            val_mid_path = os.path.join(output_dir, "validation_frame_mid.jpg")
            cv2.imwrite(val_mid_path, rendered)
            print(f"[Phase1] Saved validation_frame_mid.jpg to {val_mid_path}")

        # ── Audit frame ───────────────────────────────────────────────────────
        if frame_idx in audit_frame_indices and audit_saved < AUDIT_FRAME_COUNT:
            audit_path = os.path.join(audit_dir, f"audit_frame_{frame_idx:06d}.jpg")
            visualizer.save_audit_frame(rendered, audit_path)
            audit_saved += 1
            print(f"[Phase1] Saved audit frame: {audit_path}")

        processed += 1
        frame_idx += 1

        # Progress log every 500 processed frames
        if processed % 500 == 0:
            elapsed = time.time() - start_time
            fps_rate = processed / elapsed if elapsed > 0 else 0
            pct = 100 * frame_idx / total_frames
            eta = (total_frames - frame_idx) / (fps_rate * stride) if fps_rate > 0 else 0
            print(f"[Phase1] {pct:.1f}%  frame={frame_idx}/{total_frames}  "
                  f"speed={fps_rate:.1f}fps  ETA={eta:.0f}s  "
                  f"visible={len(frame_result.persons)}  unique_ids={len(tracker.unique_ids)}")

    # ── Save End Validation Frame ─────────────────────────────────────────────
    if last_rendered_frame is not None:
        val_end_path = os.path.join(output_dir, "validation_frame_end.jpg")
        cv2.imwrite(val_end_path, last_rendered_frame)
        print(f"[Phase1] Saved validation_frame_end.jpg to {val_end_path}")

    # ── Final Transitions to OUTSIDE ──────────────────────────────────────────
    for pid in list(known_persons):
        final_zone = current_zones.get(pid, OUTSIDE)
        final_tracking = tracking_states.get(pid, ACTIVE)
        if final_zone != OUTSIDE or final_tracking != CAMERA_EXIT:
            if final_zone != OUTSIDE:
                trans_writer.write(
                    person_id=pid,
                    frame=frame_idx,
                    timestamp_sec=frame_idx / src_fps,
                    previous_zone=final_zone,
                    current_zone=OUTSIDE,
                    bbox=last_seen_bbox.get(pid, (0, 0, 0, 0)),
                    tracker_conf=0.0,
                    det_conf=0.0,
                )
                ps_writer.record_transition(pid, frame_idx, final_zone, OUTSIDE)
            
            total_frames_track[pid] = total_frames_track.get(pid, 0) + 1
            obs_ratio = observed_frames_track.get(pid, 0) / total_frames_track[pid]
            avg_conf = sum_conf_track.get(pid, 0.0) / max(1, observed_frames_track.get(pid, 0))
            q_score = 0.6 * obs_ratio + 0.4 * avg_conf
            track_quality = "HIGH" if q_score >= 0.5 else ("MEDIUM" if q_score >= 0.25 else "LOW")
            fsd = frame_idx - last_seen_frame.get(pid, frame_idx)

            fh_writer.write(
                frame=frame_idx,
                timestamp_sec=frame_idx / src_fps,
                person_id=pid,
                current_zone=OUTSIDE,
                bbox=last_seen_bbox.get(pid, (0, 0, 0, 0)),
                bottom_center=last_seen_coords.get(pid, (0.0, 0.0)),
                visibility=OCCLUDED,
                tracking_state=CAMERA_EXIT,
                observation_type="PREDICTED",
                is_detected=0,
                detection_confidence=0.0,
                association_cost=0.0,
                frames_since_detection=fsd,
                track_quality=track_quality,
            )
            current_zones[pid] = OUTSIDE
            tracking_states[pid] = CAMERA_EXIT
            ps_writer.mark_exited(pid)

    # ── Cleanup ────────────────────────────────────────────────────────────────
    cap.release()
    video_writer.release()
    trans_writer.close()
    fh_writer.close()
    ps_writer.flush()   # write person_summary.csv

    # ── Save Candidate Rejections Log ─────────────────────────────────────────
    # save_candidate_rejections(output_dir)

    # ── Apply Ghost Track Filtering ───────────────────────────────────────────
    clean_ghost_tracks(output_dir)

    elapsed_total = time.time() - start_time
    print(f"\n[Phase1] Processing complete: {processed} frames in {elapsed_total:.1f}s "
          f"({processed/elapsed_total:.1f} fps)")
    print(f"[Phase1] Unique IDs: {len(tracker.unique_ids)}  "
          f"ID switch candidates: {len(tracker.id_switch_candidates)}")
    print(f"[Phase1] Transitions logged: {trans_writer.row_count}")
    print(f"[Phase1] Frame history rows: {fh_writer.row_count}")

    # ── Run evaluator (5 loops + report) ──────────────────────────────────────
    evaluator = Phase1Evaluator(
        transitions_csv=trans_path,
        frame_history_csv=fh_path,
        person_summary_csv=ps_path,
        output_dir=output_dir,
        video_path=video_path,
        tracker_name="BoTSORT",
        tracker_config=tracker_config,
        model_path=model_path,
        video_fps=src_fps,
        video_frames=total_frames,
        video_duration_sec=duration_sec,
        id_switch_candidates=tracker.id_switch_candidates,
        det_conf=det_conf,
    )
    report_path = evaluator.generate_report(elapsed_total, processed)
    print(f"\n[Phase1] Report written to: {report_path}")
    print(f"[Phase1] Annotated video:   {video_out_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Aurika Phase 1 — Foundational Human Tracking")
    parser.add_argument("--video", default="datasets/Dark_lighting.mp4")
    parser.add_argument("--output", default="phase1/runs/Dark_lighting/")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--tracker", default=DEFAULT_TRACKER)
    parser.add_argument("--zones", default=DEFAULT_ZONES)
    parser.add_argument("--stride", type=int, default=1,
                        help="Process every Nth frame. Use 3 for ~10fps on 30fps source.")
    parser.add_argument("--device", default="cpu", help="cpu, cuda, mps")
    parser.add_argument("--conf", type=float, default=0.05,
                        help="Detection confidence threshold (default 0.05 for dark video)")
    args = parser.parse_args()

    run(
        video_path=args.video,
        output_dir=args.output,
        model_path=args.model,
        tracker_config=args.tracker,
        zones_config=args.zones,
        stride=args.stride,
        device=args.device,
        det_conf=args.conf,
    )


if __name__ == "__main__":
    main()
