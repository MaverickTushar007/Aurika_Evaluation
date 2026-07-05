# Universal Benchmark Runner Architecture

## Universal Dataset Loader Abstraction
To ensure no production code breaks due to dataset format changes, all datasets must interface through the following abstract base class:

```python
class UniversalDatasetLoader:
    def load(self, path: str):
        pass
    def frames(self) -> Iterator[np.ndarray]:
        pass
    def annotations(self) -> Dict:
        pass
    def tracks(self) -> List[Track]:
        pass
    def metadata(self) -> Dict:
        pass
    def ground_truth(self) -> pd.DataFrame:
        pass
```

## Benchmark Execution Pipeline
1. **Ingest**: Runner maps the target dataset via the `UniversalDatasetLoader`.
2. **Execute**: Feeds frames to the Aurika edge pipeline (isolated from production).
3. **Capture**: Dumps tracker outputs (JSON/CSV) to a temporary sink.
4. **Compare**: Uses `TrackEval` library to compute HOTA, MOTA, and custom KPI metrics against `ground_truth()`.
5. **Persist**: Writes results to `leaderboard.csv`.
