import unittest
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from restaurant_analytics.metrics_engine import MetricsEngine
from restaurant_analytics.visit_manager import VisitManager
from restaurant_analytics.visit_state import GuestState, StaffState
from restaurant_analytics.event_engine import EventEngine
from restaurant_analytics.persistence_adapter import PersistenceAdapter

class TestPersistenceAdapter(PersistenceAdapter):
    def __init__(self):
        super().__init__(db_path=":memory:")
        self.saved_events = []
        
    def save_event(self, event):
        self.saved_events.append(event)
        return super().save_event(event)

class TestMetricsEngine(unittest.TestCase):
    def setUp(self):
        self.mock_persistence = TestPersistenceAdapter()
        self.event_engine = EventEngine(persistence_adapter=self.mock_persistence)
        self.visit_manager = VisitManager(event_engine=self.event_engine)
        self.metrics_engine = MetricsEngine(visit_manager=self.visit_manager)
        self.ts = datetime.utcnow()

    def test_occupancy_and_queue(self):
        self.visit_manager.handle_track_start("t1", self.ts, role="guest")
        self.visit_manager.handle_track_start("t2", self.ts, role="guest")
        
        # Move t1 to waiting
        v1 = self.visit_manager.get_visit("t1")
        self.visit_manager.state_engine.transition(v1, GuestState.WAITING.value, self.ts, "Waiting")
        
        metrics = self.metrics_engine.get_restaurant_metrics()
        self.assertEqual(metrics["current_occupancy"].value, 2)
        self.assertEqual(metrics["queue_length"].value, 1)

    def test_staff_utilization(self):
        self.visit_manager.handle_track_start("s1", self.ts, role="staff")
        self.visit_manager.handle_track_start("s2", self.ts, role="staff")
        
        s1 = self.visit_manager.get_visit("s1")
        s2 = self.visit_manager.get_visit("s2")
        
        # By default staff is IDLE.
        self.assertEqual(s1.current_state, StaffState.IDLE.value)
        metrics = self.metrics_engine.get_staff_metrics()
        self.assertEqual(metrics["staff_utilization_percent"].value, 0.0)
        
        # One staff starts serving
        self.visit_manager.state_engine.transition(s1, StaffState.SERVING.value, self.ts, "Serving")
        metrics = self.metrics_engine.get_staff_metrics()
        self.assertEqual(metrics["staff_utilization_percent"].value, 50.0)

    def test_visit_duration_and_confidence(self):
        v = self.visit_manager.handle_track_start("t1", self.ts, role="guest")
        # Ensure some time passes
        future_ts = self.ts + timedelta(minutes=5)
        
        # Override exit time explicitly to simulate closed visit metrics, though it's removed from active
        # Let's test the active duration instead
        import unittest.mock as mock
        with mock.patch('restaurant_analytics.metrics_engine.datetime') as mock_dt:
            mock_dt.utcnow.return_value = future_ts
            metrics = self.metrics_engine.get_guest_metrics(v.visit_id)
            
            self.assertEqual(metrics["visit_duration_seconds"].value, 300.0)
            
            # Default tracking=0.9, state=1.0, zone=1.0 -> 0.45 + 0.4 + 0.1 = 0.95
            self.assertAlmostEqual(metrics["visit_duration_seconds"].confidence, 0.95)

    def test_wait_time(self):
        v = self.visit_manager.handle_track_start("t1", self.ts, role="guest")
        
        self.visit_manager.state_engine.transition(v, GuestState.WAITING.value, self.ts, "Waiting")
        
        future_ts = self.ts + timedelta(minutes=2)
        import unittest.mock as mock
        with mock.patch('restaurant_analytics.metrics_engine.datetime') as mock_dt:
            mock_dt.utcnow.return_value = future_ts
            metrics = self.metrics_engine.get_guest_metrics(v.visit_id)
            self.assertEqual(metrics["waiting_time_seconds"].value, 120.0)

    def test_zone_dwell(self):
        v = self.visit_manager.handle_track_start("t1", self.ts, role="guest")
        self.visit_manager.update_visit_zone("t1", "Entrance", self.ts)
        
        future_ts = self.ts + timedelta(seconds=45)
        import unittest.mock as mock
        with mock.patch('restaurant_analytics.metrics_engine.datetime') as mock_dt:
            mock_dt.utcnow.return_value = future_ts
            metrics = self.metrics_engine.get_guest_metrics(v.visit_id)
            self.assertEqual(metrics["current_zone_dwell_seconds"].value, 45.0)

    def test_illegal_transition_emits_diagnostic(self):
        v = self.visit_manager.handle_track_start("t1", self.ts, role="guest")
        
        # WAITING -> DINING directly is illegal
        self.visit_manager.state_engine.transition(v, GuestState.WAITING.value, self.ts, "Wait")
        self.visit_manager.state_engine.transition(v, GuestState.DINING.value, self.ts, "Dine")
        
        diagnostics = [e for e in self.mock_persistence.saved_events if type(e).__name__ == 'SystemDiagnosticEvent']
        self.assertGreater(len(diagnostics), 0)
        
        diag = diagnostics[0]
        self.assertEqual(diag.event_type, "IllegalStateTransition")
        self.assertEqual(diag.metadata["attempted_state"], GuestState.DINING.value)

if __name__ == '__main__':
    unittest.main()
