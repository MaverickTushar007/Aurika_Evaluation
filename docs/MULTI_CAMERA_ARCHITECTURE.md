# Project Aurika: Multi-Camera Intelligence Architecture

The **Multi-Camera Intelligence Engine** (`multi_camera/`) upgrades Project Aurika from a single-camera perception pipeline into an enterprise-scale, multi-camera spatial reasoning platform. It treats multiple surveillance IP camera feeds as one unified environment by projecting 2D bounding boxes into canonical floor world coordinates.

---

## 1. Architectural Philosophy & Zero-Rewrite Principle

To maintain stability across Aurika's extensive backend suite, the multi-camera engine adheres strictly to the **Zero-Rewrite Principle**:
- **No Upstream Perception Rewrites**: Exists downstream of single-camera tracking models (ByteTrack / BoT-SORT). It consumes standard 2D detection bounding boxes `(x1, y1, x2, y2)` and visual feature embeddings without altering inference routines.
- **No Downstream Reasoning Rewrites**: The Identity Memory Engine (IME), Multi-Evidence Fusion Engine (MFE), Restaurant Digital Twin (RDT), Global Identity Graph (GIG), and Decision & Optimization Engine (DOE) remain architecturally intact. Clean adapter wrappers (`adapters.py`) translate multi-camera global trajectories into downstream schemas.

```
+-------------------+      +-------------------+      +-------------------+
|  Camera 01 Stream |      |  Camera 02 Stream |      |  Camera 03 Stream |
|  (ByteTrack/ReID) |      |  (ByteTrack/ReID) |      |  (ByteTrack/ReID) |
+---------+---------+      +---------+---------+      +---------+---------+
          |                          |                          |
          v                          v                          v
+-------------------------------------------------------------------------+
|                  Temporal Synchronization Buffer                        |
|                  (camera_sync.py • Jitter < 60ms)                       |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                 Homography & World Coordinate Mapper                    |
|             (coordinate_mapper.py • 3x3 Planar Homography)               |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                 Cross-Camera Tracker & Handover Engine                  |
|          (cross_camera_tracker.py • ReID Cosine Sim Matching)           |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                      Trajectory Merger & Exporter                       |
|                 (trajectory_merger.py • exporter.py)                    |
+-----------------+------------------+------------------+-----------------+
                  |                  |                  |
                  v                  v                  v
        +------------------+ +---------------+ +----------------+
        | Digital Twin RDT | | Graph GIG     | | Decision DOE   |
        | Adapter          | | Adapter       | | Adapter        |
        +------------------+ +---------------+ +----------------+
```

---

## 2. Core Modules & Component Architecture

| Module | Filename | Description |
| :--- | :--- | :--- |
| **Camera Registry** | `camera_registry.py` | Dynamic catalog storing intrinsic matrices $K$, extrinsic homography matrices $H$, resolution, FPS, and zone metadata. |
| **Camera Manager** | `camera_manager.py` | Central orchestration daemon binding registration, health watchdog supervision, and frame synchronization. |
| **Homography Engine** | `homography.py` | Performs projective $3 \times 3$ matrix math mapping image plane coordinates to canonical floor plane coordinates. |
| **Calibration Suite** | `camera_calibration.py` | Provides manual 4-point corner calibration and simulated chessboard grid routines. |
| **Coordinate Mapper** | `coordinate_mapper.py` | Converts bounding box foot-points to standardized world coordinates and restaurant operational zones. |
| **Frame Synchronizer** | `camera_sync.py` | Temporal alignment buffer aligning asynchronous multi-view streams within a bounded jitter window. |
| **Health Watchdog** | `camera_health.py` | Monitors FPS degradation, dropped frames, offline timeouts, and calibration drift, dispatching alerts. |
| **Cross-Camera Tracker** | `cross_camera_tracker.py` | Consumes single-camera tracklets, detects zone exits/entries, and assigns global canonical UUIDs. |
| **Handover Engine** | `handover_engine.py` | Evaluates exit/entry pairs using ReID cosine similarity, spatial Euclidean decay, and temporal decay. |
| **Trajectory Merger** | `trajectory_merger.py` | Stitches fragmented tracklets into continuous global paths, travel distances, and transit durations. |
| **Visibility & Coverage** | `visibility_engine.py` / `coverage_engine.py` | Identifies overlapping FOVs, blind spots, and computes exact floor grid coverage percentages. |
| **Simulation Suite** | `simulation.py` | Simulates a VIP guest walking across 5 camera zones sequentially to test continuity and handovers. |
| **Multi-Format Exporter** | `exporter.py` | Serializes trajectories and handover graphs to JSON, CSV, Apache Parquet, and GraphML. |
| **Downstream Adapters** | `adapters.py` | Non-invasive wrappers feeding global data into existing RDT, GIG, and DOE services. |

---

## 3. Operational Workflow

1. **Ingestion & Synchronization**: Asynchronous IP camera feeds emit detection frames. `CameraSynchronizer` aligns timestamps across feeds within a 60ms jitter window.
2. **Spatial Projection**: For each detection bbox, `WorldCoordinateMapper` extracts the bottom center foot-point $(u, v)$ and applies the camera's registered $3 \times 3$ homography matrix $H$ to obtain $(X, Y)$ floor coordinates.
3. **Cross-Camera Association**: When a tracklet disappears from Camera A, an exit event is logged. When a new tracklet appears in Camera B within 30 seconds and 15 meters, `HandoverEngine` calculates ReID cosine similarity and probabilistic confidence, assigning the existing canonical UUID.
4. **Trajectory Stitching**: `TrajectoryMerger` updates the guest's `GlobalTrajectory`, accumulating travel distance and logging zone transition events.
