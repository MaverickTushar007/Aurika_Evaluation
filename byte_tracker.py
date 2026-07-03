"""
byte_tracker.py — Clean Sequential Tracker (v6-restored)
=========================================================
Centroid-based multi-object tracker with sequential integer IDs.
Reverted to the v6 architecture that produced correct results,
with targeted improvements:
  - Hungarian (optimal) assignment instead of greedy nearest-neighbour
  - Velocity prediction (EMA) to bridge short occlusion gaps
  - min_hits gating: only count tracks seen >= N frames (suppress ghosts)
  - Confirmed flag for display: tracks shown after >= 3 hits
  - NMS applied before tracking (duplicates suppressed upstream in run_dark_test)
"""

import numpy as np

try:
    from scipy.optimize import linear_sum_assignment
    _HAVE_SCIPY = True
except ImportError:
    _HAVE_SCIPY = False


# ─────────────────────────────────────────────────────────────────────────────
# Low-level helpers
# ─────────────────────────────────────────────────────────────────────────────

def _centroid(bbox):
    x1, y1, x2, y2 = bbox[:4]
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _dist(c1, c2):
    return np.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2)


def _iou(a, b):
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter == 0.0:
        return 0.0
    aa = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    ab = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    return inter / (aa + ab - inter + 1e-9)


def _hungarian_assign(cost, max_cost):
    """Optimal assignment; returns list of (row, col) pairs within budget."""
    if cost.size == 0:
        return []
    if _HAVE_SCIPY:
        rows, cols = linear_sum_assignment(cost)
        if isinstance(max_cost, np.ndarray):
            return [(r, c) for r, c in zip(rows, cols) if cost[r, c] < max_cost[r, c]]
        return [(r, c) for r, c in zip(rows, cols) if cost[r, c] < max_cost]
    # Greedy fallback (no scipy)
    used = set()
    pairs = []
    for r in range(cost.shape[0]):
        row_limit = max_cost if not isinstance(max_cost, np.ndarray) else max_cost[r]
        best_c, best_v = -1, np.inf
        for c in range(cost.shape[1]):
            limit = row_limit if not isinstance(row_limit, np.ndarray) else row_limit[c]
            if c not in used and cost[r, c] < limit and cost[r, c] < best_v:
                best_v, best_c = cost[r, c], c
        if best_c >= 0:
            pairs.append((r, best_c))
            used.add(best_c)
    return pairs


# ─────────────────────────────────────────────────────────────────────────────
# ByteTracker  (clean v6-restored architecture)
# ─────────────────────────────────────────────────────────────────────────────

class ByteTracker:
    """
    Parameters
    ----------
    max_dist_active   : Max centroid distance (px) to match an active track.
    max_dist_lost     : Max centroid distance (px) to re-link a lost track.
    max_missing       : Frames a track may go unseen before deletion.
    min_hits          : Minimum detections before track is shown on screen.
    count_min_hits    : Minimum detections before track counts toward totals.
    active_window     : Frames since last match within which track is 'active'.
    velocity_alpha    : EMA weight for velocity smoothing (0 = no velocity).
    velocity_damp     : Velocity decay per unmatched frame (< 1 fades it out).
    """

    def __init__(
        self,
        max_dist_active=180,
        max_dist_lost=120,
        max_missing=90,          # 90 frames @ 8fps = ~11s gap bridge
        min_hits=3,              # show after 3 confirmed detections
        count_min_hits=6,        # count toward totals after 6 detections (~0.75s)
        active_window=8,         # frames before moving to 'lost'
        velocity_alpha=0.30,     # EMA smoothing for velocity
        velocity_damp=0.80,      # velocity decay when unmatched
        # kept for API compatibility with run_dark_test.py
        high_conf_thresh=0.35,
        iou_thresh_active=0.15,
        iou_thresh_lost=0.10,
        isolation_radius=999,    # disabled – no isolation-based low-conf spawning
        enable_lost_recovery=True,
        enable_velocity_predict=True,
        adaptive_strategy=None,
    ):
        self.max_dist_active   = max_dist_active
        self.max_dist_lost     = max_dist_lost
        self.max_missing       = max_missing
        self.min_hits          = min_hits
        self.count_min_hits    = count_min_hits
        self.active_window     = active_window
        self.velocity_alpha    = velocity_alpha
        self.velocity_damp     = velocity_damp
        self.adaptive_strategy = adaptive_strategy
        self.high_conf_thresh  = high_conf_thresh
        self.iou_thresh_active = iou_thresh_active
        self.iou_thresh_lost   = iou_thresh_lost
        self.enable_lost_recovery = enable_lost_recovery
        self.enable_velocity_predict = enable_velocity_predict

        self.tracks        = {}         # track_id -> track_dict
        self.confirmed_ids = set()      # track_id -> shown on screen
        self.countable_ids = set()      # track_id -> counted in dashboard
        self.next_id       = 1

    # ── Predicted position one step forward ──────────────────────────────────

    def _predict(self, tr):
        if not self.enable_velocity_predict:
            return tr["centroid"], tr["bbox"]
        vx, vy = tr["vx"], tr["vy"]
        cx, cy = tr["centroid"]
        x1, y1, x2, y2 = tr["bbox"]
        return (cx + vx, cy + vy), [x1 + vx, y1 + vy, x2 + vx, y2 + vy]

    # ── Build distance cost matrix ────────────────────────────────────────────

    def _dist_cost(self, det_cents, pred_cents):
        n, m = len(det_cents), len(pred_cents)
        cost = np.full((n, m), np.inf, dtype=np.float64)
        for i, dc in enumerate(det_cents):
            for j, tc in enumerate(pred_cents):
                cost[i, j] = _dist(dc, tc)
        return cost

    # ── Build IoU cost matrix (1 - IoU so lower = better) ────────────────────

    def _iou_cost(self, det_boxes, pred_boxes):
        n, m = len(det_boxes), len(pred_boxes)
        cost = np.ones((n, m), dtype=np.float64)
        for i, db in enumerate(det_boxes):
            for j, pb in enumerate(pred_boxes):
                cost[i, j] = 1.0 - _iou(db, pb)
        return cost

    # ── Match a set of detections to a set of tracks (two-pass: IoU then dist) ─

    def _match(self, all_dets, det_indices, track_ids, pred,
               iou_thresh, dist_thresh):
        """Returns list of (det_original_index, track_id) pairs."""
        if not det_indices or not track_ids:
            return []

        dets      = [all_dets[i] for i in det_indices]
        det_cents = [_centroid(d) for d in dets]
        pred_boxs = [pred[t]["bbox"] for t in track_ids]
        pred_cts  = [pred[t]["centroid"] for t in track_ids]

        matched_di  = set()
        matched_ti  = set()
        pairs       = []

        # Pass 1 – IoU
        iou_c = self._iou_cost(dets, pred_boxs)
        for r, c in _hungarian_assign(iou_c, 1.0 - iou_thresh):
            pairs.append((det_indices[r], track_ids[c]))
            matched_di.add(r)
            matched_ti.add(c)

        # Pass 2 – centroid distance for remaining
        rem_d = [r for r in range(len(dets))    if r not in matched_di]
        rem_t = [c for c in range(len(track_ids)) if c not in matched_ti]
        if rem_d and rem_t:
            dist_c = self._dist_cost(
                [det_cents[r] for r in rem_d],
                [pred_cts[c]  for c in rem_t],
            )
            if self.adaptive_strategy is not None:
                max_cost_m = np.zeros((len(rem_d), len(rem_t)), dtype=np.float64)
                for i, r_idx in enumerate(rem_d):
                    orig_d_idx = det_indices[r_idx]
                    det_box = all_dets[orig_d_idx]
                    for j, c_idx in enumerate(rem_t):
                        tid = track_ids[c_idx]
                        tr = self.tracks[tid]
                        max_cost_m[i, j] = self._compute_adaptive_threshold(tr, det_box, dist_thresh)
            else:
                max_cost_m = dist_thresh

            for r, c in _hungarian_assign(dist_c, max_cost_m):
                pairs.append((det_indices[rem_d[r]], track_ids[rem_t[c]]))

        return pairs

    def _compute_adaptive_threshold(self, tr, det_box, base_thresh):
        strategy = self.adaptive_strategy
        bbox = tr["bbox"]
        h = max(1e-5, bbox[3] - bbox[1])
        
        if strategy == "height":
            thresh = 0.60 * h
            return max(30.0, min(300.0, thresh))
            
        elif strategy == "diagonal":
            w = bbox[2] - bbox[0]
            diag = np.sqrt(w**2 + h**2)
            thresh = 0.54 * diag
            return max(30.0, min(300.0, thresh))
            
        elif strategy == "velocity":
            vx, vy = tr["vx"], tr["vy"]
            v = np.sqrt(vx**2 + vy**2)
            thresh = 60.0 + 6.0 * v
            return max(30.0, min(300.0, thresh))
            
        elif strategy == "hybrid":
            vx, vy = tr["vx"], tr["vy"]
            v = np.sqrt(vx**2 + vy**2)
            t_scale = 0.40 * h
            t_motion = 4.0 * v
            thresh = t_scale + t_motion
            return max(30.0, min(300.0, thresh))
            
        return base_thresh

    # ── Apply matched update to a single track ────────────────────────────────

    def _update_track(self, tid, det, frame_id, ts):
        bbox = list(det[:4])
        conf = float(det[4])
        cx, cy = _centroid(bbox)
        tr = self.tracks[tid]

        elapsed = max(1, frame_id - tr["last_frame"])
        raw_vx  = (cx - tr["centroid"][0]) / elapsed
        raw_vy  = (cy - tr["centroid"][1]) / elapsed
        a = self.velocity_alpha
        tr["vx"] = a * raw_vx + (1 - a) * tr["vx"]
        tr["vy"] = a * raw_vy + (1 - a) * tr["vy"]

        tr["centroid"]   = (cx, cy)
        tr["bbox"]       = bbox
        tr["conf"]       = conf
        tr["last_frame"] = frame_id
        tr["last_ts"]    = ts
        tr["hits"]      += 1
        tr["history"].append((cx, cy))

        if tr["hits"] >= self.min_hits:
            self.confirmed_ids.add(tid)
        if tr["hits"] >= self.count_min_hits:
            self.countable_ids.add(tid)

    # ── Spawn new track ───────────────────────────────────────────────────────

    def _create_track(self, det, frame_id, ts):
        bbox = list(det[:4])
        conf = float(det[4])
        cx, cy = _centroid(bbox)
        tid = self.next_id
        self.next_id += 1
        self.tracks[tid] = {
            "centroid":   (cx, cy),
            "bbox":       bbox,
            "conf":       conf,
            "entry_ts":   ts,
            "last_ts":    ts,
            "last_frame": frame_id,
            "hits":       1,
            "history":    [(cx, cy)],
            "vx":         0.0,
            "vy":         0.0,
        }
        return tid

    # ── Age out inactive tracks, apply velocity decay ─────────────────────────

    def _age_and_prune(self, frame_id):
        for tid in list(self.tracks):
            tr = self.tracks[tid]
            if tr["last_frame"] < frame_id:
                # Decay velocity for missed frames
                tr["vx"] *= self.velocity_damp
                tr["vy"] *= self.velocity_damp
                # Drift centroid & bbox by decayed velocity
                cx, cy = tr["centroid"]
                tr["centroid"] = (cx + tr["vx"], cy + tr["vy"])
                x1, y1, x2, y2 = tr["bbox"]
                tr["bbox"] = [x1 + tr["vx"], y1 + tr["vy"],
                               x2 + tr["vx"], y2 + tr["vy"]]
            if (frame_id - tr["last_frame"]) > self.max_missing:
                del self.tracks[tid]
                self.confirmed_ids.discard(tid)
                self.countable_ids.discard(tid)

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self, detections, frame_id, ts, log_lines=None):
        """
        Parameters
        ----------
        detections : list of [x1, y1, x2, y2, confidence]
        frame_id   : int – monotonically increasing frame counter
        ts         : float – video timestamp in seconds
        log_lines  : optional list; diagnostic strings appended here

        Returns
        -------
        list of (track_id, bbox, confidence, confirmed, countable)
        """
        if not detections:
            self._age_and_prune(frame_id)
            return []

        all_dets = [list(d) for d in detections]

        # ── 1. Predict all tracks one step forward ────────────────────────
        pred = {}
        for tid, tr in self.tracks.items():
            pc, pb = self._predict(tr)
            pred[tid] = {"centroid": pc, "bbox": pb}

        # ── 2. Split tracks: active (seen recently) vs lost (older) ──────
        active_tids   = [t for t in self.tracks
                         if (frame_id - self.tracks[t]["last_frame"]) <= self.active_window]
        lost_tids     = [t for t in self.tracks if t not in active_tids]

        all_det_idx   = list(range(len(all_dets)))

        matched_dets  = set()
        matched_tids  = set()
        all_pairs     = []

        # ── Stage 1: All detections ↔ active tracks ───────────────────────
        pairs_1 = self._match(
            all_dets, all_det_idx, active_tids, pred,
            iou_thresh=self.iou_thresh_active,
            dist_thresh=self.max_dist_active,
        )
        for di, tid in pairs_1:
            matched_dets.add(di)
            matched_tids.add(tid)
            all_pairs.append((di, tid))

        # ── Stage 2: Remaining detections ↔ lost tracks ──────────────────
        rem_det_idx  = [i for i in all_det_idx if i not in matched_dets]
        rem_lost_ids = [t for t in lost_tids   if t not in matched_tids]
        if self.enable_lost_recovery:
            pairs_2 = self._match(
                all_dets, rem_det_idx, rem_lost_ids, pred,
                iou_thresh=self.iou_thresh_lost,
                dist_thresh=self.max_dist_lost,
            )
        else:
            pairs_2 = []
        for di, tid in pairs_2:
            matched_dets.add(di)
            matched_tids.add(tid)
            all_pairs.append((di, tid))

        # ── 3. Update matched tracks ──────────────────────────────────────
        results = []
        for det_idx, tid in all_pairs:
            det = all_dets[det_idx]
            self._update_track(tid, det, frame_id, ts)
            c   = tid in self.confirmed_ids
            ct  = tid in self.countable_ids
            if log_lines is not None:
                tr = self.tracks[tid]
                log_lines.append(
                    f"  [MATCH] tid={tid:3d} hits={tr['hits']:3d} "
                    f"confirmed={c} countable={ct} conf={det[4]:.2f}"
                )
            results.append((tid, list(det[:4]), float(det[4]), c, ct))

        # ── 4. Spawn new tracks for unmatched detections ──────────────────
        # Only spawn for detections that are above conf threshold OR far from
        # any existing track (prevents duplicates at known positions).
        active_cents = [pred[t]["centroid"] for t in self.tracks]
        for di in all_det_idx:
            if di in matched_dets:
                continue
            det    = all_dets[di]
            is_high = float(det[4]) >= self.high_conf_thresh

            if not is_high:
                # Low-confidence: only spawn if not near an existing track
                dc = _centroid(det)
                near = any(_dist(dc, tc) < self.max_dist_active for tc in active_cents)
                if near:
                    if log_lines is not None:
                        log_lines.append(
                            f"  [SKIP ] low-conf det near existing track conf={det[4]:.2f}"
                        )
                    continue

            tid = self._create_track(det, frame_id, ts)
            c   = tid in self.confirmed_ids
            ct  = tid in self.countable_ids
            if log_lines is not None:
                log_lines.append(
                    f"  [SPAWN] tid={tid:3d} "
                    f"{'high' if is_high else 'low-iso'} conf={det[4]:.2f}"
                )
            results.append((tid, list(det[:4]), float(det[4]), c, ct))
            active_cents.append(_centroid(det))  # prevent duplicate spawns this frame

        # ── 5. Age out & prune ────────────────────────────────────────────
        self._age_and_prune(frame_id)

        return results

    # ── Utility ───────────────────────────────────────────────────────────────

    def get_active_count(self):
        return len(self.tracks)

    def get_all_tracks(self):
        return {tid: dict(tr) for tid, tr in self.tracks.items()}

    def flush_all(self, ts=0.0):
        return [(tid, tr["entry_ts"], tr.get("last_ts", ts))
                for tid, tr in self.tracks.items()]
