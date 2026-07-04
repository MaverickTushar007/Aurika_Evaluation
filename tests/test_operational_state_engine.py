import unittest
import os
import sys
from datetime import datetime, timedelta
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from restaurant_analytics.operational_state_engine import OperationalStateEngine
from restaurant_analytics.metrics_engine import MetricsEngine
from restaurant_analytics.visit_manager import VisitManager
from restaurant_analytics.event_engine import EventEngine
from restaurant_analytics.visit_state import GuestState, StaffState
from restaurant_analytics.persistence_adapter import PersistenceAdapter

class TestPersistenceAdapter(PersistenceAdapter):
    def __init__(self):
        super().__init__(db_path=":memory:")
        self.saved_events = []
        
    def save_event(self, event):
        self.saved_events.append(event)
        return super().save_event(event)
        
    def get_recent_diagnostics(self, limit=50):
        # Return mock diagnostic dicts
        return [
            {
                "event_type": type(e).__name__, 
                "reason": getattr(e, "reason", "Test Reason"),
                "timestamp": getattr(e, "timestamp", datetime.utcnow()).isoformat()
            }
            for e in self.saved_events if type(e).__name__ == 'SystemDiagnosticEvent'
        ]

class TestOperationalStateEngine(unittest.TestCase):
    def setUp(self):
        self.mock_persistence = TestPersistenceAdapter()
        self.event_engine = EventEngine(persistence_adapter=self.mock_persistence)
        self.visit_manager = VisitManager(event_engine=self.event_engine)
        self.metrics_engine = MetricsEngine(visit_manager=self.visit_manager)
        self.rose = OperationalStateEngine(metrics_engine=self.metrics_engine, persistence_adapter=self.mock_persistence)
        self.ts = datetime.utcnow()

    def test_snapshot_creation_and_serialization(self):
        self.visit_manager.handle_track_start("t1", self.ts, role="guest")
        snapshot = self.rose.get_current_snapshot()
        
        self.assertEqual(snapshot.restaurant_status, "OPEN")
        self.assertEqual(snapshot.active_guests, 1)
        self.assertEqual(snapshot.current_queue_length, 0)
        
        # Serialization
        data = snapshot.to_dict()
        self.assertIn("timestamp", data)
        self.assertEqual(data["restaurant_status"], "OPEN")
        # Ensure it's JSON serializable
        json.dumps(data)

    def test_health_score_degradation(self):
        # 1. Base healthy
        snap = self.rose.get_current_snapshot()
        self.assertEqual(snap.health_score, 100.0)
        self.assertEqual(snap.system_status, "HEALTHY")
        
        # 2. Add long queue (e.g. 5 waiting guests)
        for i in range(5):
            v = self.visit_manager.handle_track_start(f"wait_{i}", self.ts, role="guest")
            self.visit_manager.state_engine.transition(v, GuestState.WAITING.value, self.ts, "Waiting")
            
        snap_queue = self.rose.get_current_snapshot()
        # queue penalty = min(5 * 5, 30) = 25. score = 75
        self.assertEqual(snap_queue.health_score, 75.0)
        
        # 3. Add diagnostics (force illegal transition)
        v = self.visit_manager.get_visit("wait_0")
        self.visit_manager.state_engine.transition(v, GuestState.DINING.value, self.ts, "Illegal")
        
        snap_diag = self.rose.get_current_snapshot()
        # 1 alert = penalty 5. score = 70
        self.assertEqual(snap_diag.health_score, 70.0)
        self.assertEqual(len(snap_diag.current_alerts), 1)

    def test_zone_congestion(self):
        # Put 6 guests in Entrance
        for i in range(6):
            self.visit_manager.handle_track_start(f"g_{i}", self.ts, role="guest")
            self.visit_manager.update_visit_zone(f"g_{i}", "Entrance", self.ts)
            
        snap = self.rose.get_current_snapshot()
        entrance_status = snap.zone_status.get("Entrance")
        self.assertIsNotNone(entrance_status)
        self.assertEqual(entrance_status.current_guests, 6)
        # > 5 is MODERATE
        self.assertEqual(entrance_status.congestion_level, "MODERATE")

if __name__ == '__main__':
    unittest.main()
