"""
phase1/tests/test_phase1.py
===========================
Unit tests for Phase 1 — Foundational Human Tracking.

Tests:
  - Zone assignment (inside/outside polygon)
  - Zone assignment with bottom-center point
  - Hysteresis: transition fires only after N consecutive frames
  - Hysteresis: no transition if person returns before threshold
  - No same-zone transitions from TransitionWriter
  - No duplicate transitions within same frame
  - CSV integrity: PersonSummaryWriter entry/exit counts
  - Loop 3: zone transition breakdown correctness
  - Loop 4: CSV cross-reference logic

All tests use mock data — no video files, no model required.
"""

import csv
import os
import tempfile
import pytest
import numpy as np

# ── Ensure repo root is on path ────────────────────────────────────────────────
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from phase1.zone_map import ZoneMap, OUTSIDE, HYSTERESIS_FRAMES
from phase1.csv_writer import TransitionWriter, FrameHistoryWriter, PersonSummaryWriter


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def zones_config(tmp_path):
    """Write a minimal zones_phase1.json with two non-overlapping rectangles."""
    import json
    config = {
        "WAITING": {
            "color": [255, 0, 0],
            "label": "WAITING",
            "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
        },
        "DINING": {
            "color": [0, 255, 0],
            "label": "DINING",
            "polygon": [[200, 0], [300, 0], [300, 100], [200, 100]],
        },
    }
    p = tmp_path / "zones.json"
    p.write_text(json.dumps(config))
    return str(p)


@pytest.fixture
def zone_map(zones_config):
    return ZoneMap(config_path=zones_config, hysteresis=HYSTERESIS_FRAMES)


# ── Zone assignment ────────────────────────────────────────────────────────────

class TestZoneAssignment:

    def test_point_inside_waiting(self, zone_map):
        """Point (50, 50) is inside WAITING polygon."""
        assert zone_map.get_zone_for_point((50, 50)) == "WAITING"

    def test_point_inside_dining(self, zone_map):
        """Point (250, 50) is inside DINING polygon."""
        assert zone_map.get_zone_for_point((250, 50)) == "DINING"

    def test_point_outside_all(self, zone_map):
        """Point (150, 50) is in neither polygon → OUTSIDE."""
        assert zone_map.get_zone_for_point((150, 50)) == OUTSIDE

    def test_point_on_boundary(self, zone_map):
        """Point exactly on polygon edge is considered inside (pointPolygonTest >= 0)."""
        result = zone_map.get_zone_for_point((0, 0))
        assert result == "WAITING"

    def test_initialize_person_immediate(self, zone_map):
        """First appearance sets zone immediately without hysteresis."""
        zone = zone_map.initialize_person(person_id=1, bottom_center=(50, 50))
        assert zone == "WAITING"
        assert zone_map.current_zone(1) == "WAITING"

    def test_initialize_outside(self, zone_map):
        """Person appearing outside all polygons gets OUTSIDE immediately."""
        zone = zone_map.initialize_person(person_id=2, bottom_center=(150, 50))
        assert zone == OUTSIDE


# ── Hysteresis ────────────────────────────────────────────────────────────────

class TestHysteresis:

    def test_no_transition_before_threshold(self, zone_map):
        """Zone transition should NOT fire before HYSTERESIS_FRAMES consecutive frames."""
        zone_map.initialize_person(1, (50, 50))  # WAITING
        # Move to DINING but not enough frames yet
        for i in range(HYSTERESIS_FRAMES - 1):
            confirmed, transition = zone_map.assign(1, (250, 50))  # DINING
            assert confirmed == "WAITING", f"Should still be WAITING at step {i}"
            assert transition is None, f"Should not transition at step {i}"

    def test_transition_fires_at_threshold(self, zone_map):
        """Zone transition fires exactly at HYSTERESIS_FRAMES."""
        zone_map.initialize_person(1, (50, 50))  # WAITING
        confirmed_zone, fired = None, None
        for i in range(HYSTERESIS_FRAMES):
            confirmed_zone, fired = zone_map.assign(1, (250, 50))
        assert confirmed_zone == "DINING"
        assert fired == "WAITING"

    def test_reset_on_return_before_threshold(self, zone_map):
        """If person returns to original zone before threshold, counter resets."""
        zone_map.initialize_person(1, (50, 50))  # WAITING
        # Start moving toward DINING for N-2 frames
        for _ in range(HYSTERESIS_FRAMES - 2):
            zone_map.assign(1, (250, 50))
        # Return to WAITING — counter must reset
        confirmed, transition = zone_map.assign(1, (50, 50))
        assert confirmed == "WAITING"
        assert transition is None
        # Move to DINING again — now needs full N frames again
        for i in range(HYSTERESIS_FRAMES - 1):
            confirmed, transition = zone_map.assign(1, (250, 50))
            assert confirmed == "WAITING"

    def test_transition_outside_to_zone(self, zone_map):
        """Person starting OUTSIDE transitions to WAITING after N frames there."""
        zone_map.initialize_person(1, (150, 50))  # OUTSIDE
        confirmed, fired = None, None
        for _ in range(HYSTERESIS_FRAMES):
            confirmed, fired = zone_map.assign(1, (50, 50))
        assert confirmed == "WAITING"
        assert fired == OUTSIDE

    def test_multiple_persons_independent(self, zone_map):
        """Hysteresis state is independent per person."""
        zone_map.initialize_person(1, (50, 50))   # WAITING
        zone_map.initialize_person(2, (250, 50))  # DINING

        # Move person 1 toward DINING for 3 frames
        for _ in range(3):
            zone_map.assign(1, (250, 50))

        # Person 2's state should be unaffected
        assert zone_map.current_zone(2) == "DINING"
        confirmed_1, _ = zone_map.assign(1, (50, 50))  # return to WAITING
        assert confirmed_1 == "WAITING"  # still WAITING (below threshold)

    def test_remove_person_clears_state(self, zone_map):
        """Removing a person clears all their hysteresis state."""
        zone_map.initialize_person(1, (50, 50))
        zone_map.assign(1, (250, 50))  # start pending
        zone_map.remove_person(1)
        assert zone_map.current_zone(1) == OUTSIDE


# ── TransitionWriter ──────────────────────────────────────────────────────────

class TestTransitionWriter:

    def test_no_same_zone_row(self, tmp_path):
        """TransitionWriter must not write a row when prev == curr zone."""
        path = str(tmp_path / "t.csv")
        tw = TransitionWriter(path)
        tw.write(1, 10, 0.5, "WAITING", "WAITING", (0,0,100,100), 0.9, 0.8)
        tw.close()
        with open(path) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 0

    def test_valid_transition_written(self, tmp_path):
        """A valid (prev != curr) transition is written correctly."""
        path = str(tmp_path / "t.csv")
        tw = TransitionWriter(path)
        tw.write(1, 10, 0.5, "OUTSIDE", "WAITING", (10,20,110,120), 0.88, 0.75)
        tw.close()
        with open(path) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["previous_zone"] == "OUTSIDE"
        assert rows[0]["current_zone"] == "WAITING"
        assert rows[0]["person_id"] == "1"
        assert rows[0]["frame"] == "10"

    def test_row_count(self, tmp_path):
        path = str(tmp_path / "t.csv")
        tw = TransitionWriter(path)
        tw.write(1, 10, 0.1, "OUTSIDE", "WAITING", (0,0,50,50), 0.9, 0.9)
        tw.write(1, 50, 0.5, "WAITING", "DINING", (0,0,50,50), 0.9, 0.9)
        tw.write(1, 50, 0.5, "DINING", "DINING", (0,0,50,50), 0.9, 0.9)  # same-zone, not written
        tw.close()
        assert tw.row_count == 2


# ── FrameHistoryWriter ────────────────────────────────────────────────────────

class TestFrameHistoryWriter:

    def test_writes_rows(self, tmp_path):
        path = str(tmp_path / "fh.csv")
        fh = FrameHistoryWriter(path)
        fh.write(frame=1, timestamp_sec=0.03, person_id=1, current_zone="WAITING",
                 bbox=(10, 20, 110, 120), bottom_center=(60, 120))
        fh.write(frame=2, timestamp_sec=0.07, person_id=1, current_zone="WAITING",
                 bbox=(11, 21, 111, 121), bottom_center=(61, 121))
        fh.close()
        with open(path) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2

    def test_track_age_increments(self, tmp_path):
        path = str(tmp_path / "fh.csv")
        fh = FrameHistoryWriter(path)
        fh.write(frame=5, timestamp_sec=0.1, person_id=1, current_zone="WAITING",
                 bbox=(0, 0, 100, 100), bottom_center=(50, 100))
        fh.write(frame=10, timestamp_sec=0.3, person_id=1, current_zone="DINING",
                 bbox=(0, 0, 100, 100), bottom_center=(50, 100))
        fh.close()
        with open(path) as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["track_age"] == "0"
        assert rows[1]["track_age"] == "5"


# ── PersonSummaryWriter ────────────────────────────────────────────────────────

class TestPersonSummaryWriter:

    def test_entry_exit_counts(self, tmp_path):
        path = str(tmp_path / "ps.csv")
        ps = PersonSummaryWriter(path)
        ps.record_frame(1, 1, "WAITING")
        ps.record_transition(1, 5, "OUTSIDE", "WAITING")   # waiting entry
        ps.record_transition(1, 20, "WAITING", "DINING")   # waiting exit, dining entry
        ps.flush()
        with open(path) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        r = rows[0]
        assert r["waiting_entries"] == "1"
        assert r["waiting_exits"] == "1"
        assert r["dining_entries"] == "1"
        assert r["dining_exits"] == "0"

    def test_mark_exited(self, tmp_path):
        path = str(tmp_path / "ps.csv")
        ps = PersonSummaryWriter(path)
        ps.record_frame(1, 1, "WAITING")
        ps.mark_exited(1)
        ps.flush()
        with open(path) as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["status"] == "exited"


# ── Integration: zone + CSV pipeline ──────────────────────────────────────────

class TestZoneCSVIntegration:
    """Full mini-pipeline: zone transitions → CSV → cross-reference check."""

    def test_transition_in_frame_history(self, zones_config, tmp_path):
        """Every written transition frame+person must appear in frame_history."""
        zm = ZoneMap(config_path=zones_config, hysteresis=2)  # shorter for test
        trans_path = str(tmp_path / "transitions.csv")
        fh_path = str(tmp_path / "frame_history.csv")

        tw = TransitionWriter(trans_path)
        fh = FrameHistoryWriter(fh_path)

        pid = 1
        zm.initialize_person(pid, (50, 50))  # WAITING

        # Simulate 3 frames in DINING (threshold=2 → fires at frame 3)
        for frame_id in range(1, 4):
            bc = (250, 50)
            bbox = (200, 0, 300, 100)
            confirmed, transition_from = zm.assign(pid, bc)
            if transition_from is not None:
                tw.write(pid, frame_id, frame_id * 0.033, transition_from, confirmed,
                         bbox, 0.9, 0.8)
            fh.write(frame_id, frame_id * 0.033, pid, confirmed, bbox, bc)

        tw.close()
        fh.close()

        # Cross-reference
        with open(trans_path) as f:
            trans_rows = list(csv.DictReader(f))
        with open(fh_path) as f:
            fh_rows = list(csv.DictReader(f))

        fh_index = {(r["frame"], r["person_id"]) for r in fh_rows}
        for row in trans_rows:
            assert (row["frame"], row["person_id"]) in fh_index, \
                f"Transition at frame {row['frame']} not in frame_history"

        assert len(trans_rows) == 1, "Should have exactly one transition (WAITING → DINING)"
        assert trans_rows[0]["previous_zone"] == "WAITING"
        assert trans_rows[0]["current_zone"] == "DINING"


# ── SpatialValidator ──────────────────────────────────────────────────────────

class TestSpatialValidator:

    def test_validator_passes_valid_zones(self, zones_config, tmp_path):
        from phase1.spatial_validator import SpatialValidator
        validator = SpatialValidator(zones_config, width=500, height=500)
        assert validator.validate(str(tmp_path)) is True
        report_path = tmp_path / "zone_validation.md"
        assert report_path.exists()
        content = report_path.read_text()
        assert "Status: **PASS**" in content
        assert "WAITING" in content
        assert "DINING" in content

    def test_validator_fails_self_intersection(self, tmp_path):
        import json
        from phase1.spatial_validator import SpatialValidator
        # Self-intersecting polygon (hourglass shape)
        config = {
            "WAITING": {
                "color": [255, 0, 0],
                "label": "WAITING",
                "polygon": [[0, 0], [100, 100], [100, 0], [0, 100]]
            }
        }
        p = tmp_path / "zones_self_intersect.json"
        p.write_text(json.dumps(config))

        validator = SpatialValidator(str(p), width=500, height=500)
        assert validator.validate(str(tmp_path)) is False
        report_path = tmp_path / "zone_validation.md"
        assert "Status: **FAIL**" in report_path.read_text()

    def test_validator_fails_overlap(self, tmp_path):
        import json
        from phase1.spatial_validator import SpatialValidator
        # Overlapping polygons
        config = {
            "ZONE_A": {
                "color": [255, 0, 0],
                "label": "ZONE_A",
                "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]]
            },
            "ZONE_B": {
                "color": [0, 255, 0],
                "label": "ZONE_B",
                "polygon": [[50, 50], [150, 50], [150, 150], [50, 150]]
            }
        }
        p = tmp_path / "zones_overlap.json"
        p.write_text(json.dumps(config))

        validator = SpatialValidator(str(p), width=500, height=500)
        assert validator.validate(str(tmp_path)) is False
        report_path = tmp_path / "zone_validation.md"
        assert "Status: **FAIL**" in report_path.read_text()

    def test_validator_fails_outside_canvas(self, tmp_path):
        import json
        from phase1.spatial_validator import SpatialValidator
        # Vertex outside canvas width/height
        config = {
            "WAITING": {
                "color": [255, 0, 0],
                "label": "WAITING",
                "polygon": [[0, 0], [1000, 0], [1000, 1000], [0, 1000]]
            }
        }
        p = tmp_path / "zones_outside.json"
        p.write_text(json.dumps(config))

        validator = SpatialValidator(str(p), width=500, height=500)  # canvas size is 500x500
        assert validator.validate(str(tmp_path)) is False
        report_path = tmp_path / "zone_validation.md"
        assert "Status: **FAIL**" in report_path.read_text()

