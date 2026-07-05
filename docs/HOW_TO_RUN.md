# HOW TO RUN

## Running a Single Experiment
Execute the runner by passing a YAML configuration file. The runner will handle evaluation, parsing, and report generation automatically.

```bash
python experiments/run.py --config experiments/configs/bytetrack_default.yaml
```

To just verify scaffolding (no execution):
```bash
python experiments/run.py --config experiments/configs/bytetrack_default.yaml --dry-run
```

## Comparing Experiments
To compare two historical runs and determine the best approach:

```bash
python experiments/compare.py <run_id_a> <run_id_b>
```
Example:
```bash
python experiments/compare.py 20260704_120000_abc123 20260704_121500_def456
```
This generates a markdown comparison report and plots inside `experiments/comparisons/`.
