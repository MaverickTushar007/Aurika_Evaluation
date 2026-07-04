import unittest
import sqlite3
import os
import pandas as pd
from datetime import datetime, timezone, timedelta
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from zone_engine import ZoneEngine

class TestZoneEngine(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_zone_engine.db"
        
        # Setup schema
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS business_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                event_type TEXT,
                timestamp TEXT,
                value REAL,
                zone_id TEXT
            );
        """)
        
        # Insert test data
        now = datetime.utcnow()
        events = [
            # Session 1: Entered Entrance, moved to Reception, then left
            ("s1", "enter_zone", (now - timedelta(minutes=10)).isoformat(), "Entrance"),
            ("s1", "exit_zone", (now - timedelta(minutes=9)).isoformat(), "Entrance"),
            ("s1", "enter_zone", (now - timedelta(minutes=9)).isoformat(), "Reception"),
            
            # Session 2: Entered Entrance, still there
            ("s2", "enter_zone", (now - timedelta(minutes=5)).isoformat(), "Entrance"),
            
            # Session 3: Entered Entrance, Reception, Dining, Exit
            ("s3", "enter_zone", (now - timedelta(minutes=20)).isoformat(), "Entrance"),
            ("s3", "exit_zone", (now - timedelta(minutes=19)).isoformat(), "Entrance"),
            ("s3", "enter_zone", (now - timedelta(minutes=19)).isoformat(), "Reception"),
            ("s3", "exit_zone", (now - timedelta(minutes=15)).isoformat(), "Reception"),
            ("s3", "enter_zone", (now - timedelta(minutes=15)).isoformat(), "Dining"),
            ("s3", "exit_zone", (now - timedelta(minutes=2)).isoformat(), "Dining"),
        ]
        
        cur = conn.cursor()
        for s, ev, ts, z in events:
            cur.execute(
                "INSERT INTO business_events (session_id, event_type, timestamp, zone_id) VALUES (?,?,?,?)",
                (s, ev, ts, z)
            )
        conn.commit()
        conn.close()
        
        self.engine = ZoneEngine(self.db_path)
        self.start_time = (now - timedelta(hours=1)).isoformat()
        self.end_time = (now + timedelta(hours=1)).isoformat()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_live_occupancy(self):
        occ = self.engine.get_all_live_occupancies()
        # s2 is in Entrance
        self.assertEqual(occ.get("Entrance", 0), 1)
        # s1 is in Reception
        self.assertEqual(occ.get("Reception", 0), 1)
        # s3 exited Dining and didn't enter anywhere else in the DB
        self.assertEqual(occ.get("Dining", 0), 0)

    def test_zone_dwell_times(self):
        # Entrance: s1 (1m), s3 (1m). s2 hasn't exited so shouldn't count.
        dwell_ent = self.engine.get_zone_dwell_times("Entrance", self.start_time, self.end_time)
        self.assertEqual(dwell_ent["completed_visits"], 2)
        self.assertEqual(dwell_ent["avg_dwell_seconds"], 60.0)
        
        # Reception: s3 (4m = 240s)
        dwell_rec = self.engine.get_zone_dwell_times("Reception", self.start_time, self.end_time)
        self.assertEqual(dwell_rec["completed_visits"], 1)
        self.assertEqual(dwell_rec["avg_dwell_seconds"], 240.0)
        
        # Dining: s3 (13m = 780s)
        dwell_din = self.engine.get_zone_dwell_times("Dining", self.start_time, self.end_time)
        self.assertEqual(dwell_din["completed_visits"], 1)
        self.assertEqual(dwell_din["avg_dwell_seconds"], 780.0)

    def test_zone_transitions(self):
        trans = self.engine.get_zone_transitions(self.start_time, self.end_time)
        # s1: Entrance -> Reception
        # s3: Entrance -> Reception -> Dining
        self.assertEqual(trans.get("Entrance -> Reception"), 2)
        self.assertEqual(trans.get("Reception -> Dining"), 1)

if __name__ == '__main__':
    unittest.main()
