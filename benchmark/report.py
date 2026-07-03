# benchmark/report.py
"""
benchmark/report.py
-------------------
Generates a markdown performance analysis report.
Compares the metrics of the current run against target baseline configurations,
flagging regressions and recording execution statistics.
"""

import os
from typing import Dict, List

class ReportGenerator:
    @staticmethod
    def generate_report(
        output_path: str,
        config_path: str,
        metrics: Dict[str, any],
        passed: bool,
        issues: List[str],
        fps: float,
        duration: float
    ):
        """Generates a detailed markdown report for the benchmark run."""
        
        status_label = "✅ PASSED" if passed else "❌ FAILED (REGRESSION)"
        
        content = f"""# Benchmark Experiment Report

*   **Status**: {status_label}
*   **Timestamp**: {os.path.basename(os.path.dirname(output_path))}
*   **Config Reference**: `{os.path.basename(config_path)}`
*   **Total Runtime**: {duration:.1f} seconds

## Performance Summary Table

| Metric | Target Baseline Threshold | Actual Score | Status |
| :--- | :---: | :---: | :---: |
| **MOTA** | $\ge$ {metrics.get('target_min_mota', 0.70):.3f} | {metrics.get('mota', 0.0):.3f} | {"✅ Pass" if metrics.get('mota', 0.0) >= metrics.get('target_min_mota', 0.70) else "❌ Fail"} |
| **IDF1** | $\ge$ {metrics.get('target_min_idf1', 0.75):.3f} | {metrics.get('idf1', 0.0):.3f} | {"✅ Pass" if metrics.get('idf1', 0.0) >= metrics.get('target_min_idf1', 0.75) else "❌ Fail"} |
| **ID Switches** | $\le$ {metrics.get('target_max_id_switches', 30)} | {metrics.get('id_switches', 0)} | {"✅ Pass" if metrics.get('id_switches', 0) <= metrics.get('target_max_id_switches', 30) else "❌ Fail"} |
| **Counting Accuracy** | $\ge$ {metrics.get('target_min_counting_accuracy', 0.90):.1f}% | {metrics.get('counting_accuracy', 0.0) * 100:.1f}% | {"✅ Pass" if metrics.get('counting_accuracy', 0.0) >= metrics.get('target_min_counting_accuracy', 0.90) else "❌ Fail"} |
| **Throughput (FPS)** | $\ge$ {metrics.get('target_min_fps', 12.0):.1f} | {fps:.1f} | {"✅ Pass" if fps >= metrics.get('target_min_fps', 12.0) else "❌ Fail"} |

## Complete Execution Diagnostics

*   **Detection Precision**: {metrics.get('precision', 0.0) * 100:.1f}%
*   **Detection Recall**: {metrics.get('recall', 0.0) * 100:.1f}%
*   **F1-Score**: {metrics.get('f1_score', 0.0) * 100:.1f}%
*   **Ground Truth Unique Guests**: {metrics.get('gt_unique_guests', 0)}
*   **Predicted Unique Guests**: {metrics.get('pred_unique_guests', 0)}
*   **Ground Truth Unique Staff**: {metrics.get('gt_unique_staff', 0)}
*   **Predicted Unique Staff**: {metrics.get('pred_unique_staff', 0)}
*   **Ghost Tracks**: {metrics.get('ghost_tracks', 0)}
*   **Total Video Frames Evaluated**: {metrics.get('total_frames', 0)}
"""

        if not passed:
            content += "\n## Regression Failures Identified\n"
            for issue in issues:
                content += f"*   {issue}\n"
        else:
            content += "\n## Regression Verification\nNo regressions identified. All criteria satisfied.\n"

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(content)
        print(f"[report] Markdown evaluation report generated at {output_path}")
