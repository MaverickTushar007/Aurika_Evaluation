# Aurika Architectural Risks & Vulnerabilities

## 1. Pre-trained ImageNet Model for Person ReID
- **Risk:** In `tracking/deep_tracker.py`, the ReID embedding feature extractor uses standard `torchvision.models.resnet18(pretrained=True)` with the classification head removed.
- **Analysis:** ImageNet classes correspond to dogs, cars, and fruits—not human faces, clothes, or identifiers. Using an ImageNet ResNet-18 as a ReID model yields poor feature differentiation, leading to high identity switch rates under occlusions.

## 2. Weak Coordinate Mapping & Homography Projection
- **Risk:** `multi_camera/homography.py` estimates the homography matrix using standard 4-point direct linear transform (DLT). 
- **Analysis:** If numpy is missing, the code falls back to an identity matrix. An identity transformation mapping camera coordinates to world space is functionally useless and breaks Digital Twin table seating matches.

## 3. Centroid Tracking without Kalman Filter
- **Risk:** `PositionTracker` uses simple Euclidean distance mapping of bounding box centroids across frames.
- **Analysis:** Centroid distance matching breaks down when guests stand close, walk in groups, or cross paths, causing frequent ID switches. Modern pipelines use Kalman filters (like ByteTrack or DeepSORT) to model velocity vectors.

## 4. Erlang C Queue Assumptions vs. Real-World Group Behavior
- **Risk:** `QueuePredictionEngine` models wait times using Erlang C formulas assuming Poisson arrival rates.
- **Analysis:** In restaurants, customers do not arrive as independent Poisson processes; they arrive in groups, families, and tour buses. Under group surges, the M/M/c queuing model breaks down, producing incorrect expected wait times.
