# Project Aurika: Cross-Camera Handover Engine

The **Handover Engine** (`multi_camera/handover_engine.py`) provides probabilistic ReID association across surveillance camera boundaries, ensuring that guests walking between rooms maintain a single canonical identity UUID.

---

## 1. Handover Problem Formulation

In a distributed camera network, each camera runs an independent local tracker (e.g., ByteTrack or BoT-SORT) that assigns integer IDs starting from 1. When a guest walks out of Camera A's field of view (Lobby Entrance) and into Camera B's field of view (Host Queue), the system must establish that local track `101` in Camera A and local track `1` in Camera B represent the exact same human entity.

---

## 2. Probabilistic Multi-Evidence Handover Algorithm

When a tracklet disappears from Camera A, `CrossCameraTracker` creates a `CameraExitRecord` containing the guest's canonical ID, exit floor coordinates $(X_{exit}, Y_{exit})$, exit timestamp $T_{exit}$, and visual feature embedding vector $V_{exit}$.

When a new unassigned tracklet appears in Camera B at $(X_{entry}, Y_{entry})$ at time $T_{entry}$ with embedding $V_{entry}$, `HandoverEngine` evaluates candidate exits using a three-factor probabilistic score:

1. **Visual ReID Cosine Similarity ($S_{reid}$)**:
   $$S_{reid} = \frac{V_{exit} \cdot V_{entry}}{\|V_{exit}\| \|V_{entry}\|}$$
   *(Must exceed threshold $\tau = 0.65$)*

2. **Spatial Distance Decay ($S_{spatial}$)**:
   $$S_{spatial} = \max\left(0, 1 - \frac{\Delta \text{dist}}{\text{MaxDist}}\right)$$
   where $\Delta \text{dist} = \sqrt{(X_{entry} - X_{exit})^2 + (Y_{entry} - Y_{exit})^2}$ and $\text{MaxDist} = 15.0\text{m}$.

3. **Temporal Elapsed Decay ($S_{temporal}$)**:
   $$S_{temporal} = \max\left(0, 1 - \frac{\Delta T}{\text{MaxTime}}\right)$$
   where $\Delta T = T_{entry} - T_{exit}$ and $\text{MaxTime} = 30.0\text{s}$.

### Posterior Combined Confidence:
$$C_{total} = 0.50 \cdot S_{reid} + 0.30 \cdot S_{spatial} + 0.20 \cdot S_{temporal}$$

If $C_{total} \ge 0.50$, the match is verified, the pending exit record is consumed, and an explainable audit trace (`HandoverExplanation`) is emitted.

---

## 3. Explainable Handover Audit Trail

Every successful handover generates a human-readable trace logged to the database and viewable in the dashboard:

```json
{
  "canonical_id": "CANON-UUID-1000",
  "source_camera": "CAM-01-ENT",
  "target_camera": "CAM-02-QUE",
  "source_track_id": 101,
  "target_track_id": 102,
  "spatial_distance_meters": 3.61,
  "time_delta_seconds": 5.0,
  "reid_cosine_similarity": 1.0,
  "combined_confidence": 0.875,
  "explanation_text": "Handover verified: Canonical Identity 'CANON-UUID-1000' exited camera 'CAM-01-ENT' (Zone: Entrance / Lobby) and entered target camera 'CAM-02-QUE' after 5.0s traveling 3.6m (ReID Sim: 1.00, Posterior Conf: 0.87)."
}
```
