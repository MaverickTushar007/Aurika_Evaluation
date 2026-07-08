import numpy as np
import csv
import os
from ultralytics.trackers.byte_tracker import BYTETracker, STrack
from ultralytics.trackers.basetrack import TrackState
from ultralytics.trackers.utils import matching

# Global list to store rejected candidate logs
REJECTED_CANDIDATES = []

# Save original methods
original_update = BYTETracker.update

def custom_update(self, results, img=None, feats=None, **kwargs):
    """Clear and initialize match costs dictionary at the start of each frame."""
    self.match_costs = {}
    return original_update(self, results, img, feats, **kwargs)

def custom_first_association(self, strack_pool, detections, activated, refind):
    """Perform first association and record matching costs."""
    dists = self.get_dists(strack_pool, detections)
    matches, u_track, u_detection = matching.linear_assignment(dists, thresh=self.args.match_thresh)
    
    if not hasattr(self, 'match_costs'):
        self.match_costs = {}
    for itracked, idet in matches:
        track = strack_pool[itracked]
        self.match_costs[track.track_id] = float(dists[itracked, idet])
        
    self._apply_matches(matches, strack_pool, detections, activated, refind)
    return u_track, u_detection

def custom_second_association(self, strack_pool, u_track, detections_second, activated, refind, lost):
    """Intercept second association, capture low-score detections, and record matching costs."""
    self.detections_second = detections_second
    r_tracked_stracks = [strack_pool[i] for i in u_track if strack_pool[i].state == TrackState.Tracked]
    
    if not hasattr(self, 'match_costs'):
        self.match_costs = {}
        
    if r_tracked_stracks and detections_second:
        dists = matching.iou_distance(r_tracked_stracks, detections_second)
        if self.args.fuse_score:
            dists = matching.fuse_score(dists, detections_second)
        matches, u_track_matches, _ = matching.linear_assignment(dists, thresh=0.5)
        
        for itracked, idet in matches:
            track = r_tracked_stracks[itracked]
            self.match_costs[track.track_id] = float(dists[itracked, idet])
            
        self._apply_matches(matches, r_tracked_stracks, detections_second, activated, refind)
        u_track = u_track_matches
    else:
        u_track = list(range(len(r_tracked_stracks)))

    for it in u_track:
        track = r_tracked_stracks[it]
        if track.state != TrackState.Lost:
            track.mark_lost()
            lost.append(track)

def custom_unconfirmed_association(
    self,
    unconfirmed: list[STrack],
    u_detection: list[int],
    detections: list[STrack],
    activated: list[STrack],
    removed: list[STrack],
) -> tuple[list[int], list[STrack]]:
    """
    Candidate-recovery association for unconfirmed tracks with balanced motion constraints.
    Matches against both unmatched high-score detections and Captured low-score detections,
    debounces them, and applies motion validation checks before promoting.
    """
    # Slice detections list to only unmatched high-score detections (as per default byte_tracker)
    high_dets = [detections[i] for i in u_detection]
    low_dets = getattr(self, 'detections_second', [])
    combined_dets = high_dets + low_dets

    if not unconfirmed or not combined_dets:
        # Return default unmatched indices into high_dets and high_dets itself
        return list(range(len(high_dets))), high_dets

    # Compute distances between unconfirmed tracks and all combined detections
    dists = self.get_dists(unconfirmed, combined_dets)
    matches, u_unconfirmed_idx, u_combined_idx = matching.linear_assignment(dists, thresh=0.7)

    matched_high_indices = set()
    rejected_reasons = {}

    for itracked, idet in matches:
        track = unconfirmed[itracked]
        det = combined_dets[idet]

        # Motion Validation check
        is_valid = True
        reason = ""

        # Calculate displacement and scale change
        curr_center = (det.tlwh[0] + det.tlwh[2] / 2.0, det.tlwh[1] + det.tlwh[3] / 2.0)
        prev_center = (track.tlwh[0] + track.tlwh[2] / 2.0, track.tlwh[1] + track.tlwh[3] / 2.0)
        disp = np.sqrt((curr_center[0] - prev_center[0])**2 + (curr_center[1] - prev_center[1])**2)

        curr_area = det.tlwh[2] * det.tlwh[3]
        prev_area = track.tlwh[2] * track.tlwh[3]
        area_ratio = max(curr_area / max(1e-5, prev_area), prev_area / max(1e-5, curr_area))

        # Check balanced motion plausibility (displacement <= 100px, area_ratio <= 1.6)
        if disp > 100.0:
            is_valid = False
            reason = f"Displacement too high ({disp:.1f}px > 100px)"
        elif area_ratio > 1.6:
            is_valid = False
            reason = f"Scale change too fast (ratio={area_ratio:.2f} > 1.6)"

        if is_valid:
            # Promote candidate track to confirmed
            track.update(det, self.frame_id)
            track.is_activated = True
            track.missed_count = 0
            track.consecutive_detections = getattr(track, 'consecutive_detections', 1) + 1
            activated.append(track)
            
            # Record cost
            if not hasattr(self, 'match_costs'):
                self.match_costs = {}
            self.match_costs[track.track_id] = float(dists[itracked, idet])
            
            # If it matched a high-score detection, remove its index from high_dets pool
            if idet < len(high_dets):
                matched_high_indices.add(idet)
        else:
            u_unconfirmed_idx.append(itracked)
            rejected_reasons[track.track_id] = reason

    # Retain unmatched unconfirmed candidate tracks for up to 5 frames
    for it in u_unconfirmed_idx:
        track = unconfirmed[it]
        track.missed_count = getattr(track, 'missed_count', 0) + 1
        
        if track.missed_count <= 5:
            track.predict()
        else:
            track.mark_removed()
            removed.append(track)
            
            # Log candidate rejection details
            reason = rejected_reasons.get(track.track_id, "Missed count exceeded (5 frames)")
            REJECTED_CANDIDATES.append({
                "Frame": self.frame_id,
                "Detection confidence": float(track.score),
                "Bounding box": [float(x) for x in track.tlwh],
                "Number of consecutive detections": getattr(track, 'consecutive_detections', 1),
                "Reason rejected": reason,
                "Tracker state": "Removed",
                "Lifetime before deletion": self.frame_id - track.start_frame
            })

    # Return unmatched indices relative to high_dets
    remaining_u_detection = [i for i in range(len(high_dets)) if i not in matched_high_indices]

    return remaining_u_detection, high_dets


def save_candidate_rejections(output_dir: str):
    """Save all logged rejected candidates to candidate_rejections.csv."""
    path = os.path.join(output_dir, "candidate_rejections.csv")
    os.makedirs(output_dir, exist_ok=True)
    
    fields = [
        "Frame", "Detection confidence", "Bounding box",
        "Number of consecutive detections", "Reason rejected",
        "Tracker state", "Lifetime before deletion"
    ]
    
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in REJECTED_CANDIDATES:
            writer.writerow({
                "Frame": r["Frame"],
                "Detection confidence": f"{r['Detection confidence']:.4f}",
                "Bounding box": str(r["Bounding box"]),
                "Number of consecutive detections": r["Number of consecutive detections"],
                "Reason rejected": r["Reason rejected"],
                "Tracker state": r["Tracker state"],
                "Lifetime before deletion": r["Lifetime before deletion"]
            })
            
    print(f"[Recovery] Wrote {len(REJECTED_CANDIDATES)} candidate rejections to {path}")


# Apply the monkey patches
BYTETracker.update = custom_update
BYTETracker._first_association = custom_first_association
BYTETracker._second_association = custom_second_association
BYTETracker._unconfirmed_association = custom_unconfirmed_association
print("[Recovery] Successfully monkey-patched BYTETracker association methods with cost logging")
