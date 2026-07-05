# EXPERIMENT YAML TEMPLATE

This defines the standard fields for configuring an experiment.

```yaml
experiment:
  dataset: "restaurant/fine_dining"
  video: "queue_camera_01.mp4"
  output_dir: "experiments/runs"
  evaluation_metrics:
    - HOTA
    - IDF1
    - MOTA
    - DetA
    - AssA
  hardware:
    device: "cuda:0"
    cpu_threads: 8

detector:
  name: "YOLOX"
  confidence_threshold: 0.3
  iou_threshold: 0.7

tracker:
  name: "BoT-SORT"
  frame_rate: 30
  identity_memory: false
  memory_length: 60
  fusion_method: "kalman_only"
```
