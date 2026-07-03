# tests/test_production_candidate.py
"""
Production validation test suite for configurations, trackers, detectors, counters,
loggers, metrics, and regression checkers.
"""

import os
import pytest
import numpy as np

from configs.config_loader import ConfigLoader
from utils.logger import setup_logger
from monitoring.runtime_metrics import RuntimeMetricsCollector
from detection.yolo_detector import PersonDetector
from tracking.tracker_wrapper import TrackerWrapper
from semantic.role_classifier import RoleClassifier
from counting.zone_counter import ZoneCounter

def test_config_loader():
    """Verifies that the configuration profiles load correctly."""
    loader = ConfigLoader()
    config = loader.load_config("benchmark")
    assert config is not None
    assert loader.get("project")["name"] == "Restaurant Analytics (Benchmark)"
    assert loader.get_nested("model", "conf_threshold") == 0.20

def test_json_logger():
    """Verifies logger initializes and outputs structured log logs."""
    logger = setup_logger("test_run", log_dir="runs/test_logs")
    assert logger is not None
    logger.info("Test logging message")
    assert os.path.exists("runs/test_logs")

def test_metrics_collector():
    """Verifies runtime stats accumulator exports files correctly."""
    collector = RuntimeMetricsCollector(output_dir="runs/test_metrics")
    collector.collect(
        frame_id=1, current_guests=5, current_staff=2, total_guests=7,
        ghost_tracks=0, id_switches=1, latency_ms=45.5, fps=22.0
    )
    json_path = collector.export_json("test_metrics.json")
    csv_path = collector.export_csv("test_metrics.csv")
    
    assert os.path.exists(json_path)
    assert os.path.exists(csv_path)

def test_tracker_wrapper():
    """Verifies tracking update outputs formatted states."""
    loader = ConfigLoader()
    loader.load_config("benchmark")
    tracker = TrackerWrapper(loader)
    
    # Send mock detection box
    detections = [[100.0, 150.0, 200.0, 250.0, 0.90]]
    results = tracker.update(detections, frame_id=1, timestamp=0.1)
    assert isinstance(results, list)

def test_role_classifier():
    """Verifies role classifier assigns categories based on history."""
    loader = ConfigLoader()
    loader.load_config("benchmark")
    classifier = RoleClassifier(loader)
    
    mock_frame = np.zeros((300, 300, 3), dtype=np.uint8)
    role = classifier.classify(mock_frame, [10, 10, 50, 50], track_history_len=2)
    assert role == "guest"  # Too short

def test_zone_counter():
    """Verifies zone Counter maps containment polygons."""
    loader = ConfigLoader()
    loader.load_config("benchmark")
    counter = ZoneCounter(loader)
    
    # Outside polygon
    zone = counter.get_zone([0.0, 0.0, 10.0, 10.0])
    assert zone is None

def test_person_detector():
    """Verifies that PersonDetector initializes and runs inference on a mock image."""
    loader = ConfigLoader()
    loader.load_config("benchmark")
    
    # Force use of yolo11n.pt for fast unit testing
    loader.config["paths"]["weights_path"] = "yolo11n.pt"
    
    detector = PersonDetector(loader)
    mock_frame = np.zeros((300, 300, 3), dtype=np.uint8)
    detections = detector.detect(mock_frame)
    assert isinstance(detections, list)

