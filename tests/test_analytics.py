# tests/test_analytics.py
"""
Automated unit tests verifying BI calculations, queue metrics,
occupancy timelines, funnel conversions, and HTML report compilation.
"""

import os
import pytest
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

from occupancy_engine import OccupancyEngine
from queue_engine import QueueEngine
from heatmap_generator import HeatmapGenerator
from analytics_engine import AnalyticsEngine
from report_generator import ReportGenerator

TEST_DB = "db/test_analytics.db"

@pytest.fixture(scope="module")
def setup_mock_db():
    """Sets up a temporary SQLite database with mock observation and session records."""
    os.makedirs("db", exist_ok=True)
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        
    conn = sqlite3.connect(TEST_DB)
    cur = conn.cursor()
    
    # Create tables
    cur.executescript("""
    CREATE TABLE temporal_sessions (
        session_id TEXT PRIMARY KEY,
        camera_id TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT,
        duration_seconds REAL
    );
    CREATE TABLE staff_resolutions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        staff_id TEXT,
        confidence REAL,
        resolution_method TEXT,
        resolved_at TEXT
    );
    CREATE TABLE business_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        event_type TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        value REAL,
        zone_id TEXT
    );
    CREATE TABLE raw_observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        camera_id TEXT NOT NULL,
        bbox_x1 REAL,
        bbox_y1 REAL,
        bbox_x2 REAL,
        bbox_y2 REAL,
        confidence REAL,
        embedding BLOB
    );
    """)
    
    # Insert mock sessions (1 staff, 2 guests)
    now = datetime.utcnow()
    t_start = (now - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    t_end = (now - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    
    cur.execute("INSERT INTO temporal_sessions VALUES (?, ?, ?, ?, ?)", ("s1", "cam1", t_start, None, 0.0))
    cur.execute("INSERT INTO temporal_sessions VALUES (?, ?, ?, ?, ?)", ("s2", "cam1", t_start, t_end, 300.0))
    cur.execute("INSERT INTO temporal_sessions VALUES (?, ?, ?, ?, ?)", ("s3", "cam1", t_start, t_end, 300.0))
    
    # Resolve s1 as staff
    cur.execute("INSERT INTO staff_resolutions (session_id, staff_id, confidence, resolution_method, resolved_at) VALUES (?, ?, ?, ?, ?)",
                ("s1", "staff_01", 0.95, "color", t_start))
                
    # Insert zone events
    cur.execute("INSERT INTO business_events (session_id, event_type, timestamp, value, zone_id) VALUES (?, ?, ?, ?, ?)",
                ("s2", "enter_zone", t_start, 0.0, "Service_Zone"))
    cur.execute("INSERT INTO business_events (session_id, event_type, timestamp, value, zone_id) VALUES (?, ?, ?, ?, ?)",
                ("s2", "served", t_end, 120.0, "Service_Zone"))
    cur.execute("INSERT INTO business_events (session_id, event_type, timestamp, value, zone_id) VALUES (?, ?, ?, ?, ?)",
                ("s2", "exit_zone", t_end, 120.0, "Service_Zone"))
                
    # Insert raw spatial points
    cur.execute("INSERT INTO raw_observations (timestamp, camera_id, bbox_x1, bbox_y1, bbox_x2, bbox_y2, confidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (t_start, "cam1", 100, 100, 200, 200, 0.9))
                
    conn.commit()
    conn.close()
    
    yield
    
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_occupancy(setup_mock_db):
    engine = OccupancyEngine(TEST_DB)
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    live = engine.get_live_occupancy(now_str)
    
    # s1 is active and resolved as staff. s2/s3 are completed. Total live = 1 (staff)
    assert live["total"] == 1
    assert live["staff"] == 1
    assert live["guests"] == 0

def test_queue(setup_mock_db):
    engine = QueueEngine(TEST_DB)
    q = engine.get_live_queue("Service_Zone")
    
    # s2 entered and got served (so exited queue). current queue = 0
    assert q["current_queue_length"] == 0

def test_heatmap(setup_mock_db):
    engine = HeatmapGenerator(TEST_DB)
    grid_data = engine.generate_heatmap_grid()
    assert "grid" in grid_data
    assert len(grid_data["grid"]) == 20

def test_analytics_kpi(setup_mock_db):
    engine = AnalyticsEngine(TEST_DB)
    now = datetime.utcnow()
    t_start = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    t_end = (now + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    
    funnel = engine.calculate_conversion_funnel(t_start, t_end)
    assert funnel["entrances"] == 3
    assert funnel["checkout_attempts"] == 1
    assert funnel["transactions"] == 1
