# Project Aurika: Surveillance Camera Calibration Guide

Accurate world coordinate mapping requires precise calibration of camera extrinsic homography matrices ($H$). This guide outlines how to perform manual 4-point corner calibration and automated chessboard grid calibration using `multi_camera/camera_calibration.py`.

---

## 1. Planar Homography Theory

In restaurant surveillance, guests move along a planar floor surface ($Z = 0$). The perspective transformation between a 2D camera image plane $(u, v)$ and the 2D floor plane $(X, Y)$ is governed by a non-singular $3 \times 3$ homography matrix $H$:

$$\begin{bmatrix} wX \\ wY \\ w \end{bmatrix} = \begin{bmatrix} H_{00} & H_{01} & H_{02} \\ H_{10} & H_{11} & H_{12} \\ H_{20} & H_{21} & H_{22} \end{bmatrix} \begin{bmatrix} u \\ v \\ 1 \end{bmatrix}$$

To solve for the 8 degrees of freedom in $H$, exactly **4 non-collinear corresponding point pairs** are required between image pixels and known floor physical measurements (in meters).

---

## 2. Manual 4-Point Corner Calibration

Manual calibration is recommended for fixed surveillance cameras pointing at dining rooms, host stands, or lobbies where physical floor landmarks (tiles, table legs, doorways) can be measured with a laser distance meter.

### Workflow:
1. **Identify Floor Anchor Points**: Select 4 widely spaced reference landmarks on the floor (e.g., four corners of a rectangular dining section).
2. **Measure Physical Coordinates**: Establish an origin $(0, 0)$ at the bottom-left corner of the restaurant grid and record $(X, Y)$ measurements in meters for all 4 landmarks.
3. **Record Image Pixel Coordinates**: Extract the pixel coordinates $(u, v)$ for those exact same 4 landmarks from the camera feed.
4. **Execute Calibration Routine**:

```python
from multi_camera.camera_registry import CameraRegistry
from multi_camera.camera_calibration import CameraCalibrator

registry = CameraRegistry()
calibrator = CameraCalibrator(registry)

# Image pixel coordinates (u, v)
img_points = [(150.0, 800.0), (1750.0, 800.0), (1600.0, 300.0), (300.0, 300.0)]
# Known floor coordinates in meters (X, Y)
world_points = [(10.0, 10.0), (30.0, 10.0), (30.0, 40.0), (10.0, 40.0)]

success = calibrator.calibrate_manual_4point(
    camera_id="CAM-03-DIN",
    image_points=img_points,
    world_points=world_points,
    verifier="Admin-Operator"
)
```

5. **Verify Calibration**: Run `calibrator.verify_calibration("CAM-03-DIN", max_reprojection_error=0.15)` to confirm average reprojection error is under 15 centimeters.

---

## 3. Chessboard Grid Calibration

For temporary setups, pop-up events, or rapid installation, automated chessboard calibration maps standard optical grids placed on the floor to canonical grid spacing.

```python
success = calibrator.calibrate_chessboard(
    camera_id="CAM-01-ENT",
    grid_size=(7, 7),
    square_size_meters=0.5,
    mock_detected_corners=detected_corner_list
)
```

---

## 4. Calibration Troubleshooting & Best Practices

- **Avoid Collinear Points**: Ensure all 4 calibration points form a well-conditioned quadrilateral. Never select 3 points on the same straight line or along a single wall.
- **Maximize Area Spread**: Choose points near the outer edges of the camera's field of view. Selecting points too close together will amplify reprojection error at distant edges.
- **Periodic Verification**: Use `CameraHealthMonitor` to check for `CALIBRATION_DRIFT` alerts caused by camera mount vibrations or accidental physical bumps.
