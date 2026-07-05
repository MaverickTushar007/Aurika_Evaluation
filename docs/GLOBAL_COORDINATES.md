# Project Aurika: Global World Coordinate System

To reason about guests and operations across multiple rooms and cameras without spatial confusion, Project Aurika standardizes all physical tracking on a canonical **2D Floor Plane Grid** defined in meters (`multi_camera/global_world_coordinates.py`).

---

## 1. Physical Grid Setup & Reference Dimensions

The restaurant layout is modeled on a Euclidean coordinate system spanning **$100.0 \times 100.0$ meters**:
- **Origin $(0.0, 0.0)$**: Front entrance foyer / bottom-left boundary of the facility.
- **$X$-Axis**: Represents horizontal width across the restaurant (East-West direction).
- **$Y$-Axis**: Represents vertical depth into the restaurant (North-South direction).
- **$Z$-Axis**: Height above the floor plane (default $0.0\text{m}$ for ground footprint tracking).

---

## 2. Standardized Operational Zones

`GlobalWorldReference` divides the floor grid into 7 non-overlapping operational bounding polygons:

| Zone Name | Zone Type | Grid Bounds (meters) | Max Capacity |
| :--- | :--- | :--- | :--- |
| **Entrance / Lobby** | `ENTRANCE` | $X \in [0, 20], Y \in [0, 30]$ | 50 guests |
| **Waiting Area / Host Queue** | `QUEUE` | $X \in [20, 40], Y \in [0, 30]$ | 40 guests |
| **Main Dining Room** | `DINING` | $X \in [0, 70], Y \in [30, 80]$ | 120 guests |
| **VIP Dining Section** | `DINING` | $X \in [70, 100], Y \in [30, 80]$ | 40 guests |
| **Cashier / POS Station** | `CASHIER` | $X \in [40, 60], Y \in [0, 30]$ | 20 guests |
| **Exit Corridor** | `ENTRANCE` | $X \in [60, 80], Y \in [0, 30]$ | 30 guests |
| **Back-of-House / Kitchen** | `KITCHEN` | $X \in [0, 100], Y \in [80, 100]$ | 30 staff |

---

## 3. Spatial Velocity & Trajectory Merging

When `WorldCoordinateMapper` projects an image bounding box $(u, v)$ into floor point $(X_t, Y_t)$, `TrajectoryMerger` stitches these points into a continuous `GlobalTrajectory` object per canonical UUID:

- **Instantaneous Velocity**: Computed between consecutive observations over elapsed time $\Delta t$:
  $$V_{mps} = \frac{\sqrt{(X_t - X_{t-1})^2 + (Y_t - Y_{t-1})^2}}{\Delta t}$$
- **Jitter Filtering**: Micro-displacements under $0.05\text{m}$ ($5\text{cm}$) are filtered out to prevent stationary guests from accumulating artificial travel distances due to bounding box pixel oscillation.
- **Zone & Camera Transition Logging**: When a guest crosses a polygon boundary or switches camera streams, `ZoneTransitionEvent` and `CameraTransitionEvent` records are logged and exported to graph databases.
