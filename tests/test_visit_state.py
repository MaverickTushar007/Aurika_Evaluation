import unittest
import os
import sys
from datetime import datetime, timedelta
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from restaurant_analytics.visit_state import StateEngine, GuestState, StaffState
from restaurant_analytics.visit_manager import VisitManager
from restaurant_analytics.event_engine import BusinessEvent, EventType

class TestVisitStateEngine(unittest.TestCase):
    def setUp(self):
        self.state_engine = StateEngine()
        self.visit_manager = VisitManager(state_engine=self.state_engine)
        self.ts = datetime.utcnow()

    def test_visit_creation_default_state(self):
        visit = self.visit_manager.handle_track_start("t1", self.ts, role="guest")
        self.assertEqual(visit.current_state, GuestState.ENTERING.value)
        self.assertEqual(visit.previous_state, GuestState.UNKNOWN.value)
        self.assertEqual(len(visit.state_history), 1)
        self.assertEqual(visit.state_history[0].new_state, GuestState.ENTERING.value)

    def test_legal_transitions(self):
        visit = self.visit_manager.handle_track_start("t1", self.ts, role="guest")
        
        # ENTERING -> GREETING
        result = self.state_engine.transition(visit, GuestState.GREETING.value, self.ts, "Host approach")
        self.assertTrue(result)
        self.assertEqual(visit.current_state, GuestState.GREETING.value)
        self.assertEqual(visit.previous_state, GuestState.ENTERING.value)
        
        # GREETING -> WAITING
        result = self.state_engine.transition(visit, GuestState.WAITING.value, self.ts, "Asked to wait")
        self.assertTrue(result)
        self.assertEqual(visit.current_state, GuestState.WAITING.value)
        
        # WAITING -> ESCORTED
        result = self.state_engine.transition(visit, GuestState.ESCORTED.value, self.ts, "Host escorting")
        self.assertTrue(result)
        self.assertEqual(visit.current_state, GuestState.ESCORTED.value)

    def test_illegal_transitions_rejected(self):
        visit = self.visit_manager.handle_track_start("t1", self.ts, role="guest")
        
        # Transition ENTERING -> WAITING is allowed. Let's get to WAITING.
        self.state_engine.transition(visit, GuestState.WAITING.value, self.ts, "Waiting")
        
        # WAITING -> DINING directly is illegal according to our rules
        result = self.state_engine.transition(visit, GuestState.DINING.value, self.ts, "Started eating")
        self.assertFalse(result)
        
        # Verify state is unchanged
        self.assertEqual(visit.current_state, GuestState.WAITING.value)
        # History should only contain ENTERING and WAITING (2 items)
        self.assertEqual(len(visit.state_history), 2)

    def test_repeated_transitions_ignored(self):
        visit = self.visit_manager.handle_track_start("t1", self.ts, role="guest")
        
        self.state_engine.transition(visit, GuestState.GREETING.value, self.ts, "Greeting")
        self.assertEqual(len(visit.state_history), 2)
        
        # Repeat transition to same state
        result = self.state_engine.transition(visit, GuestState.GREETING.value, self.ts, "Still Greeting")
        self.assertFalse(result)
        self.assertEqual(len(visit.state_history), 2)

    def test_exit_transitions(self):
        visit = self.visit_manager.handle_track_start("t1", self.ts, role="guest")
        self.visit_manager.update_visit_zone("t1", "Exit_Door", self.ts)
        
        # update_visit_zone fires EventEngine which calls StateEngine process_event
        # "exit" in zone should trigger EXITING
        self.assertEqual(visit.current_state, GuestState.EXITING.value)
        
        self.visit_manager.handle_track_end("t1", self.ts)
        # handle_track_end fires publish_visit_closed -> GuestExited -> EXITED
        self.assertEqual(visit.current_state, GuestState.EXITED.value)

    def test_confidence_propagation(self):
        visit = self.visit_manager.handle_track_start("t1", self.ts, role="guest")
        self.state_engine.transition(visit, GuestState.SEATED.value, self.ts, "Seated", confidence=0.85)
        self.assertEqual(visit.state_confidence, 0.85)
        self.assertEqual(visit.state_history[-1].confidence, 0.85)

    def test_temporal_rules(self):
        visit = self.visit_manager.handle_track_start("t1", self.ts, role="guest")
        
        # Manually set zone without firing event for testing
        visit.current_zone = "Waiting_Area"
        visit.zone_entry_time = self.ts
        
        # 10 seconds later, evaluate -> should remain ENTERING (not enough time)
        self.state_engine.evaluate_temporal_state(visit, self.ts + timedelta(seconds=10))
        self.assertEqual(visit.current_state, GuestState.ENTERING.value)
        
        # 31 seconds later, evaluate -> should transition to WAITING
        self.state_engine.evaluate_temporal_state(visit, self.ts + timedelta(seconds=31))
        self.assertEqual(visit.current_state, GuestState.WAITING.value)
        self.assertEqual(visit.state_history[-1].reason, "Dwelled in waiting zone for 31.0s")

if __name__ == '__main__':
    unittest.main()
