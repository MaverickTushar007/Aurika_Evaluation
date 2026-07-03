# benchmark/tests/test_validator.py
"""
benchmark/tests/test_validator.py
---------------------------------
Unit tests for benchmark/validate_annotations.py.
"""

import os
import tempfile
import unittest
from benchmark.validate_annotations import validate_gt_file

class TestAnnotationValidator(unittest.TestCase):
    def setUp(self):
        # Create a temporary file for ground truth simulating text lines
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".txt")
        self.temp_path = self.temp_file.name

    def tearDown(self):
        if os.path.exists(self.temp_path):
            os.remove(self.temp_path)

    def write_gt_lines(self, lines):
        with open(self.temp_path, "w") as f:
            for line in lines:
                f.write(line + "\n")

    def test_valid_gt(self):
        # Valid tracking sequence
        self.write_gt_lines([
            "1, 1, 100.0, 100.0, 50.0, 100.0, 1",
            "2, 1, 105.0, 105.0, 50.0, 100.0, 1",
            "3, 1, 110.0, 110.0, 50.0, 100.0, 1"
        ])
        success = validate_gt_file(self.temp_path)
        self.assertTrue(success)

    def test_class_drift(self):
        # ID 1 drifts from role 1 (guest) to role 2 (staff)
        self.write_gt_lines([
            "1, 1, 100.0, 100.0, 50.0, 100.0, 1",
            "2, 1, 105.0, 105.0, 50.0, 100.0, 2"
        ])
        success = validate_gt_file(self.temp_path)
        self.assertFalse(success)

    def test_large_coordinate_jump(self):
        # ID 1 jumps 300px between consecutive frames
        self.write_gt_lines([
            "1, 1, 100.0, 100.0, 50.0, 100.0, 1",
            "2, 1, 400.0, 400.0, 50.0, 100.0, 1"
        ])
        success = validate_gt_file(self.temp_path, max_jump_pixels=150.0)
        self.assertFalse(success)

    def test_invalid_dimensions(self):
        # Bounding box height too small (< 30px)
        self.write_gt_lines([
            "1, 1, 100.0, 100.0, 50.0, 10.0, 1"
        ])
        success = validate_gt_file(self.temp_path)
        self.assertFalse(success)

if __name__ == "__main__":
    unittest.main()
