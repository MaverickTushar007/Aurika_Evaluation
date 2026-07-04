import unittest
import sqlite3
import os
from datetime import datetime, timezone, timedelta
import sys

# Ensure restaurant_analytics can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from restaurant_analytics.event_engine import EventEngine, EventType, BusinessEvent
from restaurant_analytics.persistence_adapter import PersistenceAdapter
from restaurant_analytics.visit_manager import VisitManager

class TestPersistenceAdapter(PersistenceAdapter):
    """Mock persistence adapter to inspect saved events in memory without writing to DB."""
    def __init__(self):
        super().__init__(db_path=":memory:")
        self.saved_events = []
        
    def save_event(self, event):
        self.saved_events.append(event)
        # Also run real SQL test against memory DB
        super().save_event(event)

class TestEventEngine(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_events.db"
        
        # Setup schema for legacy DB test
        self.conn = sqlite3.connect(self.db_path)
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS business_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                event_type TEXT,
                timestamp TEXT,
                value REAL,
                zone_id TEXT
            );
        """)
        self.conn.close()
        
        self.persistence = PersistenceAdapter(db_path=self.db_path)
        self.mock_persistence = TestPersistenceAdapter()
        self.mock_persistence.db_path = self.db_path
        self.engine = EventEngine(persistence_adapter=self.mock_persistence)
        self.visit_manager = VisitManager(event_engine=self.engine)
        self.ts = datetime.utcnow()
        
    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_visit_created_generates_guest_entered(self):
        visit = self.visit_manager.handle_track_start("t1", self.ts, role="guest")
        events = self.mock_persistence.saved_events
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, EventType.GuestEntered)
        self.assertEqual(events[0].person_id, "t1")

    def test_zone_change_generates_enter_and_exit(self):
        visit = self.visit_manager.handle_track_start("t1", self.ts)
        self.mock_persistence.saved_events.clear()
        
        # First zone entry
        self.visit_manager.update_visit_zone("t1", "Entrance", self.ts)
        events = self.mock_persistence.saved_events
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, EventType.ZoneEntered)
        self.assertEqual(events[0].zone, "Entrance")
        
        self.mock_persistence.saved_events.clear()
        
        # Zone change
        self.visit_manager.update_visit_zone("t1", "Reception", self.ts)
        events = self.mock_persistence.saved_events
        self.assertEqual(len(events), 2)
        # Should have ZoneExited for Entrance and ZoneEntered for Reception
        types = {e.event_type for e in events}
        zones = {e.zone for e in events}
        self.assertIn(EventType.ZoneExited, types)
        self.assertIn(EventType.ZoneEntered, types)
        self.assertIn("Entrance", zones)
        self.assertIn("Reception", zones)

    def test_duplicate_updates_ignored(self):
        self.visit_manager.handle_track_start("t1", self.ts)
        self.visit_manager.update_visit_zone("t1", "Entrance", self.ts)
        self.mock_persistence.saved_events.clear()
        
        # Duplicate update
        self.visit_manager.update_visit_zone("t1", "Entrance", self.ts)
        self.assertEqual(len(self.mock_persistence.saved_events), 0)

    def test_visit_closed_generates_exit_events(self):
        visit = self.visit_manager.handle_track_start("t1", self.ts, role="guest")
        self.visit_manager.update_visit_zone("t1", "Dining", self.ts)
        self.mock_persistence.saved_events.clear()
        
        # End visit
        visit.metrics["served"] = True
        self.visit_manager.handle_track_end("t1", self.ts + timedelta(minutes=10))
        
        events = self.mock_persistence.saved_events
        types = [e.event_type for e in events]
        
        # Should emit ZoneExited, Served, and GuestExited
        self.assertIn(EventType.ZoneExited, types)
        self.assertIn(EventType.Served, types)
        self.assertIn(EventType.GuestExited, types)
        
    def test_persistence_adapter_writes_correctly(self):
        # We test the real persistence adapter with SQLite
        engine = EventEngine(persistence_adapter=self.persistence)
        manager = VisitManager(event_engine=engine)
        
        manager.handle_track_start("t1", self.ts, role="guest")
        manager.update_visit_zone("t1", "Kitchen", self.ts)
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT session_id, event_type, zone_id FROM business_events WHERE event_type='enter_zone'")
        rows = cur.fetchall()
        conn.close()
        
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "t1")
        self.assertEqual(rows[0][2], "Kitchen")

if __name__ == '__main__':
    unittest.main()
