# benchmark/regression.py
"""
benchmark/regression.py
-----------------------
Compares experiment metrics against baseline thresholds.
Determines if an experiment has introduced tracking or counting regressions.
"""

from typing import Dict, List, Tuple

class RegressionChecker:
    def __init__(self, thresholds: Dict[str, float]):
        """
        thresholds: Dict containing target minimums/maximums:
          - min_mota
          - min_idf1
          - max_id_switches
          - min_counting_accuracy
          - min_fps
        """
        self.thresholds = thresholds

    def check_metrics(self, metrics: Dict[str, any], fps_actual: float) -> Tuple[bool, List[str]]:
        """
        Verifies the results against the configured baseline thresholds.
        Returns:
            Tuple[passed: bool, issues: List[str]]
        """
        passed = True
        issues = []

        # ── 1. MOTA Gate ──────────────────────────────────────────────────────
        min_mota = self.thresholds.get("min_mota", 0.70)
        actual_mota = metrics.get("mota", 0.0)
        if actual_mota < min_mota:
            passed = False
            issues.append(f"MOTA regression: {actual_mota:.3f} < threshold {min_mota:.3f}")

        # ── 2. IDF1 Gate ──────────────────────────────────────────────────────
        min_idf1 = self.thresholds.get("min_idf1", 0.75)
        actual_idf1 = metrics.get("idf1", 0.0)
        if actual_idf1 < min_idf1:
            passed = False
            issues.append(f"IDF1 regression: {actual_idf1:.3f} < threshold {min_idf1:.3f}")

        # ── 3. ID Switches Gate ───────────────────────────────────────────────
        max_idsw = self.thresholds.get("max_id_switches", 30)
        actual_idsw = metrics.get("id_switches", 999)
        if actual_idsw > max_idsw:
            passed = False
            issues.append(f"ID Switches exceed threshold: {actual_idsw} > max {max_idsw}")

        # ── 4. Counting Accuracy Gate ─────────────────────────────────────────
        min_acc = self.thresholds.get("min_counting_accuracy", 0.90)
        actual_acc = metrics.get("counting_accuracy", 0.0)
        if actual_acc < min_acc:
            passed = False
            issues.append(f"Counting Accuracy regression: {actual_acc:.3f} < threshold {min_acc:.3f}")

        # ── 5. Throughput FPS Gate ────────────────────────────────────────────
        min_fps = self.thresholds.get("min_fps", 12.0)
        if fps_actual < min_fps:
            passed = False
            issues.append(f"Runtime Throughput regression: {fps_actual:.1f} FPS < threshold {min_fps:.1f} FPS")

        return passed, issues
