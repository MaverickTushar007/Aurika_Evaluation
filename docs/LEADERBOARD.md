# LEADERBOARD

This document serves as the historical index of experiment performance on the Aurika Scientific Benchmarking System.

**Note**: The actual data is dynamically recorded in `experiments/leaderboard.csv` upon each successful execution of `experiments/run.py`.

## Ranking Criteria
1. **Primary**: `HOTA` (Higher Order Tracking Accuracy)
2. **Secondary**: `IDF1` (Identity F1-Score)
3. **Third**: `MOTA` (Multiple Object Tracking Accuracy)
4. **Fourth**: `Runtime` (Total evaluation time)
5. **Fifth**: `FPS` (Average processing frames per second)

You can analyze `experiments/leaderboard.csv` using Pandas or Excel to historically trace improvements over baseline configurations.
