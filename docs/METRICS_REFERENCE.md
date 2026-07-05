# METRICS REFERENCE

Aurika's automated benchmark system collects the following core tracking and performance metrics:

## Primary Tracking Metrics (TrackEval)
- **HOTA** (Higher Order Tracking Accuracy): The main metric evaluating both detection and association simultaneously.
- **MOTA** (Multiple Object Tracking Accuracy): Heavily influenced by detection performance (FPs and FNs).
- **IDF1** (ID F1-Score): Ratio of correctly identified detections over the average number of ground truth and computed detections. Focuses on identity preservation.
- **DetA** (Detection Accuracy): Localized detection performance.
- **AssA** (Association Accuracy): Localized association/identity performance.

## Error Metrics
- **FP** (False Positives): Non-existent bounding boxes.
- **FN** (False Negatives): Missed true bounding boxes.
- **IDs** (Identity Switches): Trajectories incorrectly assigned to a different identity.
- **Frag** (Fragmentations): Trajectories interrupted and resumed as the same ID.

## Run-Time Performance Metrics
- **Runtime_sec**: Total evaluation time.
- **Average_FPS**: Frames processed per second on average.
- **Peak_FPS**: Maximum frames processed per second (without bottlenecks).
- **Average_Latency_ms**: Time from frame ingest to final tracks output.
- **GPU_Utilization_pct**: Measured hardware strain.
- **RAM_Usage_MB**: Peak memory footprint.
