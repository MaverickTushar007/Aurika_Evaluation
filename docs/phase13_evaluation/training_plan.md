# Model Training & Fine-Tuning Plan

## Current Assessment
Based on Phase 6 validation, **is training worthwhile?**
**Decision**: YES, but highly constrained.

## Target Fine-Tuning
- **Dataset**: `AI Smart Restaurant Surveillance`
- **Annotations**: Bounding Boxes (Customers, Staff, Trays).
- **Model**: YOLOv11 Edge.
- **Layers**: Freeze backbone, unfreeze final 3 layers (prediction heads).
- **Hyperparameters**: LR 1e-4, AdamW, Cosine Annealing, 50 epochs.
- **Augmentation**: Heavy mosaic, random perspective, low-light simulation.

## Tracker Optimization (No Weights Overwritten)
- Grid search `track_high_thresh` and `track_low_thresh` for ByteTrack using PersonPath22 evaluation loop.

**Expected Improvement**: Reduces false negatives in dim restaurant lighting by 15% (estimated, pending empirical proof).
