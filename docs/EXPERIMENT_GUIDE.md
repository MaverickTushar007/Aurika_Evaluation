# EXPERIMENT GUIDE

This guide explains the architecture of the Aurika Scientific Benchmarking System.

## Principles
1. **Reproducibility**: Every run produces a unique, immutable directory containing configuration, runtime metadata, logs, and outputs.
2. **Configurability**: All parameters (dataset, thresholds, tracker) are defined via YAML.
3. **Traceability**: All output JSONs contain system stats and the Git hash of the code at runtime.

## Directory Structure
- `configs/`: YAML definition files.
- `runs/`: Generated isolated run directories containing results.
- `comparisons/`: Output from `compare.py`.
- `metrics/`: Submodules for metric extraction.
- `visualizations/`: Submodules for plotting.

## Leaderboard
The `leaderboard.csv` file inside `experiments/` automatically tracks all runs to historically trace architectural improvements.
