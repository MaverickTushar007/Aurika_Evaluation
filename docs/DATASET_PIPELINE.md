# Multi-Format Dataset Builder & Pipeline

The Dataset Builder (`continuous_learning/dataset_builder/`) converts curated high-value samples from active learning and operator manual corrections into standardized training datasets across computer vision and tabular forecasting domains.

## Supported Export Formats
1. **YOLO Detection Labels (`YOLO`)**:
   - Generates `labels.txt` formatted as `<class_id> <x_center> <y_center> <width> <height>` normalized to $[0, 1]$.
2. **COCO JSON Annotations (`COCO`)**:
   - Serializes standard COCO structure (`images`, `annotations`, `categories`) with exact bounding box coordinates and model confidence scores.
3. **MOT Challenge Format (`MOT`)**:
   - Generates `gt.txt` formatted as `<frame>, <id>, <bb_left>, <bb_top>, <bb_width>, <bb_height>, <conf>, -1, -1, -1` for tracking model retraining.
4. **ReID Crop Manifests (`REID`)**:
   - Indexes person ID crops, camera IDs, timestamps, and uncertainty scores in `reid_manifest.json` for embedding fine-tuning.
5. **Tabular CSV (`CSV`)**:
   - Exports structured tabular failures, wait time overrides, and queue forecasting errors.
6. **Apache Parquet (`PARQUET`)**:
   - Generates column-oriented compressed data archives via `pandas`/`pyarrow` (with binary header fallback for edge container compatibility) for high-performance tabular ML training.

## Automated Manifest Cataloging
Every generated dataset produces an immutable `DatasetManifest` tracking:
- Unique ID (`DS-<TYPE>-<HASH>`)
- Sample Count
- Format Category
- File System Output Path
- Creation Timestamp & Metadata
These manifests are directly linkable to model versions in the enterprise Model Registry.
