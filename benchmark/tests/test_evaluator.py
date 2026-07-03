# benchmark/tests/test_evaluator.py
"""
benchmark/tests/test_evaluator.py
---------------------------------
Unit tests verifying the tracking evaluator's calculations.
Tests MOTA, IDF1, ID Switches, Precision, and Recall using simulated cases.
"""

import unittest
from benchmark.evaluator import TrackingEvaluator

class TestTrackingEvaluator(unittest.TestCase):
    def setUp(self):
        self.evaluator = TrackingEvaluator(iou_threshold=0.50)

    def test_perfect_tracking(self):
        """Simulates perfect tracking output: zero switches, 100% precision and recall."""
        # Simple static box over 5 frames
        bbox = [100.0, 100.0, 200.0, 200.0]
        
        # predictions format: Dict[frame_id, List[(track_id, bbox, conf, role)]]
        predictions = {
            i: [(1, bbox, 0.95, "guest")] for i in range(5)
        }
        # ground_truth format: Dict[frame_id, List[{"bbox": [x1,y1,x2,y2], "track_id": int, "class_id": int}]]
        ground_truth = {
            i: [{"bbox": bbox, "track_id": 1, "class_id": 1}] for i in range(5)
        }
        
        metrics = self.evaluator.evaluate_clip(predictions, ground_truth)
        
        self.assertEqual(metrics["id_switches"], 0)
        self.assertAlmostEqual(metrics["mota"], 1.0)
        self.assertAlmostEqual(metrics["idf1"], 1.0)
        self.assertAlmostEqual(metrics["precision"], 1.0)
        self.assertAlmostEqual(metrics["recall"], 1.0)
        self.assertEqual(metrics["gt_unique_guests"], 1)
        self.assertEqual(metrics["pred_unique_guests"], 1)

    def test_id_switch(self):
        """Simulates a tracking ID swap: track 1 transitions to track 2 at frame 3."""
        bbox = [100.0, 100.0, 200.0, 200.0]
        
        predictions = {}
        for i in range(5):
            if i < 3:
                predictions[i] = [(1, bbox, 0.95, "guest")]
            else:
                predictions[i] = [(2, bbox, 0.95, "guest")]  # ID Switch occurs here
                
        ground_truth = {
            i: [{"bbox": bbox, "track_id": 1, "class_id": 1}] for i in range(5)
        }
        
        metrics = self.evaluator.evaluate_clip(predictions, ground_truth)
        
        self.assertEqual(metrics["id_switches"], 1)
        # 5 GT boxes, 1 ID switch. MOTA = 1 - (0 FP + 0 FN + 1 IDSW)/5 = 0.8
        self.assertAlmostEqual(metrics["mota"], 0.80)
        # IDF1 optimal mapping will link GT 1 to the longer predicted track segment (pred 1, length 3)
        # Overlapping frames with pred 1 = 3. Overlapping frames with pred 2 = 2.
        # best_overlap_sum (IDTP) = 3. Total predicted boxes = 5. Total GT boxes = 5.
        # IDF1 = 2 * 3 / (2 * 3 + 2 + 2) = 6 / 10 = 0.60
        self.assertAlmostEqual(metrics["idf1"], 0.60)

    def test_false_positives_and_negatives(self):
        """Simulates missing detections (FN) and spurious detections (FP)."""
        bbox = [100.0, 100.0, 200.0, 200.0]
        
        predictions = {
            0: [(1, bbox, 0.90, "guest")],
            1: [],                         # False Negative (gt 1 missing)
            2: [(1, bbox, 0.90, "guest"), (2, [400.,400.,500.,500.], 0.80, "guest")] # False Positive
        }
        
        ground_truth = {
            0: [{"bbox": bbox, "track_id": 1, "class_id": 1}],
            1: [{"bbox": bbox, "track_id": 1, "class_id": 1}],
            2: [{"bbox": bbox, "track_id": 1, "class_id": 1}]
        }
        
        metrics = self.evaluator.evaluate_clip(predictions, ground_truth)
        
        # GT total = 3. Predictions total = 3.
        # FP = 1 (at frame 2, track 2)
        # FN = 1 (at frame 1, track 1 missing)
        # IDSW = 0
        # MOTA = 1 - (1 + 1 + 0)/3 = 0.333
        self.assertAlmostEqual(metrics["mota"], 1.0/3.0)
        self.assertAlmostEqual(metrics["precision"], 2.0/3.0)  # TP=2, FP=1
        self.assertAlmostEqual(metrics["recall"], 2.0/3.0)     # TP=2, FN=1

if __name__ == "__main__":
    unittest.main()
