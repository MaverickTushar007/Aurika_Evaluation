# Dataset Compatibility Matrix

| Dataset | Status | Justification |
|---|---|---|
| **PersonPath22** | **Benchmark Only** | High density tracking is useful for testing occlusion recovery, but angles are not representative of indoor restaurants. |
| **VIRAT** | **Unsupported** | Overhead aerial surveillance angles do not match Aurika's edge-deployed fisheye or wall-mounted angles. |
| **CrowdHuman** | **Fine-tuning** | Excellent for pre-training detectors for dense indoor crowds to reduce false negatives. |
| **AI Smart Restaurant** | **Validation** | Domain-specific footage is ideal for testing the pipeline, but annotation quality must be strictly verified before training. |

**Policy**: Do NOT force unsupported datasets (e.g. VIRAT) into training as they will corrupt the model's spatial priors.
