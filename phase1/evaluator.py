"""
phase1/evaluator.py
===================
Post-run evaluation and tracking_report.md generator.

Runs all 5 validation loops and produces a machine-readable + human-readable
tracking report. No business logic.
"""

from __future__ import annotations
import csv
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional


class Phase1Evaluator:
    """
    Reads the three output CSVs and produces evaluation metrics + tracking_report.md.
    All validation is data-driven — no hardcoded expected values.
    """

    def __init__(
        self,
        transitions_csv: str,
        frame_history_csv: str,
        person_summary_csv: str,
        output_dir: str,
        video_path: str,
        tracker_name: str,
        tracker_config: str,
        model_path: str,
        video_fps: float,
        video_frames: int,
        video_duration_sec: float,
        id_switch_candidates: List[dict],
    ):
        self.transitions_csv = transitions_csv
        self.frame_history_csv = frame_history_csv
        self.person_summary_csv = person_summary_csv
        self.output_dir = output_dir
        self.video_path = video_path
        self.tracker_name = tracker_name
        self.tracker_config = tracker_config
        self.model_path = model_path
        self.video_fps = video_fps
        self.video_frames = video_frames
        self.video_duration_sec = video_duration_sec
        self.id_switch_candidates = id_switch_candidates

        self._transitions: List[dict] = []
        self._frame_history: List[dict] = []
        self._person_summary: List[dict] = []

    def load_csvs(self):
        """Load all three CSVs into memory for analysis."""
        if os.path.exists(self.transitions_csv):
            with open(self.transitions_csv) as f:
                self._transitions = list(csv.DictReader(f))

        if os.path.exists(self.frame_history_csv):
            with open(self.frame_history_csv) as f:
                self._frame_history = list(csv.DictReader(f))

        if os.path.exists(self.person_summary_csv):
            with open(self.person_summary_csv) as f:
                self._person_summary = list(csv.DictReader(f))

    # ── Loop 1 — Detection ─────────────────────────────────────────────────────

    def loop1_detection(self) -> dict:
        """Verify only persons (class 0) appear. Count raw and person detections."""
        total_rows = len(self._frame_history)
        non_person = sum(1 for r in self._frame_history if r.get("class_id", "0") != "0")
        unique_frames = len(set(r["frame"] for r in self._frame_history))
        return {
            "total_frame_history_rows": total_rows,
            "unique_frames_with_detections": unique_frames,
            "non_person_detections": non_person,
            "passed": non_person == 0,
        }

    # ── Loop 2 — Tracking ─────────────────────────────────────────────────────

    def loop2_tracking(self) -> dict:
        """ID switches, track fragmentation, lost/recovered tracks."""
        person_frames = defaultdict(list)
        for row in self._frame_history:
            person_frames[int(row["person_id"])].append(int(row["frame"]))

        unique_ids = list(person_frames.keys())
        track_lengths = {pid: len(frames) for pid, frames in person_frames.items()}
        avg_len = sum(track_lengths.values()) / len(track_lengths) if track_lengths else 0
        longest = max(track_lengths.values()) if track_lengths else 0
        shortest = min(track_lengths.values()) if track_lengths else 0

        # Fragmentation: count persons with non-contiguous frame sequences
        # (gap > 1 frame means track was lost and recovered or a new ID was created)
        fragmented = 0
        gaps = []
        for pid, frames in person_frames.items():
            fs = sorted(frames)
            for i in range(1, len(fs)):
                gap = fs[i] - fs[i - 1]
                if gap > 1:
                    gaps.append({"person_id": pid, "gap_frames": gap, "at_frame": fs[i]})
            if any(fs[i] - fs[i-1] > 1 for i in range(1, len(fs))):
                fragmented += 1

        return {
            "unique_ids": len(unique_ids),
            "id_switch_candidates": len(self.id_switch_candidates),
            "id_switch_candidate_frames": [c["frame"] for c in self.id_switch_candidates],
            "fragmented_tracks": fragmented,
            "track_gaps": len(gaps),
            "avg_track_length_frames": round(avg_len, 1),
            "longest_track_frames": longest,
            "shortest_track_frames": shortest,
            "id_switches_per_minute": round(len(self.id_switch_candidates) / max(self.video_duration_sec / 60, 1), 2),
            "passed": len(self.id_switch_candidates) < 30,  # < 30 switches for ~10-min video
        }

    # ── Loop 3 — Zone ─────────────────────────────────────────────────────────

    def loop3_zones(self) -> dict:
        """No duplicate transitions. No same-zone transitions."""
        dup_transitions = 0
        same_zone = 0
        prev_per_person: Dict[str, dict] = {}

        for row in self._transitions:
            pid = row["person_id"]
            pz = row["previous_zone"]
            cz = row["current_zone"]

            if pz == cz:
                same_zone += 1

            key = f"{pid}-{pz}-{cz}"
            if key in prev_per_person:
                # Might be legitimate (person returned to same zone), only count true dups
                pass
            prev_per_person[key] = row

        unique_transitions = len(set(
            f"{r['person_id']}-{r['frame']}-{r['previous_zone']}-{r['current_zone']}"
            for r in self._transitions
        ))
        dup_by_frame = len(self._transitions) - unique_transitions

        return {
            "total_transitions": len(self._transitions),
            "same_zone_transitions": same_zone,
            "duplicate_transitions_by_frame": dup_by_frame,
            "zone_breakdown": self._zone_transition_breakdown(),
            "passed": same_zone == 0 and dup_by_frame == 0,
        }

    def _zone_transition_breakdown(self) -> dict:
        counts = defaultdict(int)
        for row in self._transitions:
            key = f"{row['previous_zone']} → {row['current_zone']}"
            counts[key] += 1
        return dict(counts)

    # ── Loop 4 — CSV integrity ─────────────────────────────────────────────────

    def loop4_csv(self) -> dict:
        """Every transition row exists in frame_history. No missing IDs or timestamps."""
        # Index frame_history by (frame, person_id)
        fh_index = set(
            (r["frame"], r["person_id"]) for r in self._frame_history
        )
        missing_in_fh = []
        for row in self._transitions:
            key = (row["frame"], row["person_id"])
            if key not in fh_index:
                missing_in_fh.append(key)

        # Check strictly increasing frames in frame_history
        frames_seq = [int(r["frame"]) for r in self._frame_history]
        non_increasing = sum(1 for i in range(1, len(frames_seq)) if frames_seq[i] < frames_seq[i-1])

        # Check for missing timestamps
        missing_ts = sum(1 for r in self._frame_history if not r.get("timestamp_sec"))

        # Verify person_summary IDs match frame_history IDs
        fh_ids = set(r["person_id"] for r in self._frame_history)
        ps_ids = set(r["person_id"] for r in self._person_summary)
        ids_in_fh_not_ps = fh_ids - ps_ids
        ids_in_ps_not_fh = ps_ids - fh_ids

        return {
            "transitions_missing_in_frame_history": len(missing_in_fh),
            "missing_details": missing_in_fh[:10],  # first 10
            "non_increasing_frame_rows": non_increasing,
            "missing_timestamps": missing_ts,
            "ids_in_frame_history_not_summary": list(ids_in_fh_not_ps),
            "ids_in_summary_not_frame_history": list(ids_in_ps_not_fh),
            "passed": len(missing_in_fh) == 0 and non_increasing == 0 and missing_ts == 0,
        }

    # ── Loop 5 — Visual audit ──────────────────────────────────────────────────

    def loop5_visual(self, audit_dir: str) -> dict:
        """Enumerate audit frame screenshots saved by the pipeline."""
        if not os.path.exists(audit_dir):
            return {"audit_frames_saved": 0, "passed": False}
        frames = [f for f in os.listdir(audit_dir) if f.endswith(".jpg") or f.endswith(".png")]
        return {
            "audit_frames_saved": len(frames),
            "audit_frame_paths": frames,
            "passed": len(frames) >= 5,
        }

    # ── Report generation ──────────────────────────────────────────────────────

    def generate_report(self, elapsed_sec: float, processed_frames: int) -> str:
        """Run all loops and write tracking_report.md. Returns path to report."""
        self.load_csvs()

        l1 = self.loop1_detection()
        l2 = self.loop2_tracking()
        l3 = self.loop3_zones()
        l4 = self.loop4_csv()
        l5 = self.loop5_visual(os.path.join(self.output_dir, "audit_frames"))

        fps_achieved = processed_frames / elapsed_sec if elapsed_sec > 0 else 0

        status = lambda p: "✅ PASS" if p else "❌ FAIL"

        lines = [
            "# Aurika Phase 1 — Tracking Report",
            f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## Video",
            f"- **File**: `{os.path.basename(self.video_path)}`",
            f"- **Duration**: {self.video_duration_sec:.1f}s ({self.video_duration_sec/60:.1f} min)",
            f"- **Resolution**: 1920×1080",
            f"- **FPS (source)**: {self.video_fps:.2f}",
            f"- **Total frames (source)**: {self.video_frames}",
            f"- **Frames processed**: {processed_frames}",
            f"- **Processing speed**: {fps_achieved:.1f} fps",
            "",
            "## Model & Tracker",
            f"- **Detection model**: `{os.path.basename(self.model_path)}`",
            f"- **Tracker**: {self.tracker_name}",
            f"- **Tracker config**: `{os.path.basename(self.tracker_config)}`",
            f"- **Person class ID**: 0",
            f"- **Detection conf threshold**: 0.25",
            "",
            "---",
            "",
            "## Loop 1 — Detection Validation",
            f"**Status**: {status(l1['passed'])}",
            f"- Total frame-history rows: {l1['total_frame_history_rows']}",
            f"- Unique frames with detections: {l1['unique_frames_with_detections']}",
            f"- Non-person detections (should be 0): {l1['non_person_detections']}",
            "",
            "## Loop 2 — Tracking Validation",
            f"**Status**: {status(l2['passed'])}",
            f"- Unique person IDs: {l2['unique_ids']}",
            f"- ID switch candidates: {l2['id_switch_candidates']}",
            f"- ID switches per minute: {l2['id_switches_per_minute']}",
            f"- Fragmented tracks (gaps > 1 frame): {l2['fragmented_tracks']}",
            f"- Total track gaps: {l2['track_gaps']}",
            f"- Avg track length (frames): {l2['avg_track_length_frames']}",
            f"- Longest track (frames): {l2['longest_track_frames']}",
            f"- Shortest track (frames): {l2['shortest_track_frames']}",
        ]

        if l2["id_switch_candidate_frames"]:
            lines.append(f"- Switch candidate frames: {l2['id_switch_candidate_frames'][:20]}")

        lines += [
            "",
            "## Loop 3 — Zone Validation",
            f"**Status**: {status(l3['passed'])}",
            f"- Total transitions recorded: {l3['total_transitions']}",
            f"- Same-zone transitions (should be 0): {l3['same_zone_transitions']}",
            f"- Duplicate transitions by frame (should be 0): {l3['duplicate_transitions_by_frame']}",
            "- Zone transition breakdown:",
        ]
        for pair, cnt in sorted(l3["zone_breakdown"].items()):
            lines.append(f"  - `{pair}`: {cnt}")

        lines += [
            "",
            "## Loop 4 — CSV Integrity",
            f"**Status**: {status(l4['passed'])}",
            f"- Transitions missing in frame_history: {l4['transitions_missing_in_frame_history']}",
            f"- Non-increasing frame rows: {l4['non_increasing_frame_rows']}",
            f"- Missing timestamps: {l4['missing_timestamps']}",
            f"- IDs in frame_history not in summary: {l4['ids_in_frame_history_not_summary']}",
            f"- IDs in summary not in frame_history: {l4['ids_in_summary_not_frame_history']}",
            "",
            "## Loop 5 — Visual Audit",
            f"**Status**: {status(l5['passed'])}",
            f"- Audit frames saved: {l5['audit_frames_saved']}",
        ]
        if l5.get("audit_frame_paths"):
            for f in l5["audit_frame_paths"]:
                lines.append(f"  - `{f}`")

        lines += [
            "",
            "---",
            "",
            "## Overall Status",
        ]
        all_passed = all([l1["passed"], l2["passed"], l3["passed"], l4["passed"], l5["passed"]])
        lines.append(f"**Phase 1 Complete**: {'✅ YES — ready for Phase 2' if all_passed else '❌ NO — iteration required'}")
        lines += [
            f"- Loop 1 Detection: {status(l1['passed'])}",
            f"- Loop 2 Tracking:  {status(l2['passed'])}",
            f"- Loop 3 Zones:     {status(l3['passed'])}",
            f"- Loop 4 CSV:       {status(l4['passed'])}",
            f"- Loop 5 Visual:    {status(l5['passed'])}",
            "",
            "## Recommended Improvements",
        ]
        if not l2["passed"]:
            lines.append(f"- High ID switch rate ({l2['id_switches_per_minute']}/min): consider increasing `track_buffer` or lowering `match_thresh` in botsort_dark.yaml")
        if l2["fragmented_tracks"] > l2["unique_ids"] // 2:
            lines.append("- More than half of all tracks are fragmented: review detector confidence threshold (currently 0.25)")
        if l3["same_zone_transitions"] > 0:
            lines.append("- Same-zone transitions detected: increase `hysteresis` parameter in zone_map.py")
        if l4["transitions_missing_in_frame_history"] > 0:
            lines.append("- Transitions missing from frame_history: possible frame-drop bug in main loop")
        if not l5["passed"]:
            lines.append("- Fewer than 5 audit frames saved: review audit_frames/ output")
        if all_passed:
            lines.append("- No critical issues. Phase 2 (business KPIs) can begin.")

        report = "\n".join(lines)
        report_path = os.path.join(self.output_dir, "tracking_report.md")
        os.makedirs(self.output_dir, exist_ok=True)
        with open(report_path, "w") as f:
            f.write(report)

        print(report)
        return report_path
