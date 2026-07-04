import unittest
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from restaurant_analytics.operational_intelligence import OperationalIntelligenceLayer, OperationalDecision
from restaurant_analytics.restaurant_state import RestaurantSnapshot

class TestOperationalIntelligence(unittest.TestCase):
    def setUp(self):
        # Point to the actual rules config
        self.rules_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "rules.json")
        self.intel_layer = OperationalIntelligenceLayer(rules_path=self.rules_path)

    def test_success_criteria_snapshot(self):
        """
        Occupancy: 91% (Wait, occupancy in rules is based on integer active_guests or occupancy metric. 
        Let's pass current_occupancy=91 for test)
        Queue Length: 8
        Average Wait: 12 min (720s)
        Host Utilization: 99%
        System Confidence: 96%
        """
        snapshot = RestaurantSnapshot(
            timestamp=datetime.utcnow(),
            restaurant_status="BUSY",
            current_occupancy=91,
            current_queue_length=8,
            average_wait_time=720.0,
            active_guests=91,
            active_staff=5,
            staff_utilization=99.0,
            zone_status={},
            table_status={},
            host_status={},
            kitchen_status={},
            diagnostic_summary={},
            current_alerts=[],
            health_score=40.0,
            overall_confidence=0.96,
            system_status="DEGRADED"
        )
        
        decisions = self.intel_layer.evaluate_snapshot(snapshot)
        
        # We expect at least: QUEUE_SLA_BREACH, QUEUE_THRESHOLD_EXCEEDED, HOST_OVERLOADED, HIGH_OCCUPANCY
        self.assertGreaterEqual(len(decisions), 4)
        
        rule_ids = [d.title for d in decisions]
        self.assertIn("Guest waiting longer than SLA", rule_ids)
        self.assertIn("Queue exceeds threshold", rule_ids)
        self.assertIn("Restaurant occupancy exceeds configured percentage", rule_ids)
        self.assertIn("Host overloaded", rule_ids)
        
        # Check Priority ordering
        self.assertTrue(decisions[0].priority <= decisions[1].priority)
        
        # Check Explainability
        top_decision = decisions[0]
        self.assertIn("average_wait_time", top_decision.supporting_metrics)
        self.assertEqual(top_decision.supporting_metrics["average_wait_time"], 720.0)

    def test_disabled_rules_are_ignored(self):
        # We temporarily mock the rules to have a disabled one
        self.intel_layer.rules = [
            {
                "rule_id": "TEST_DISABLED",
                "name": "Disabled Rule",
                "description": "Should not fire.",
                "enabled": False,
                "severity": "INFO",
                "priority": 10,
                "conditions": {
                    "metric": "current_occupancy",
                    "operator": ">",
                    "threshold": 0
                },
                "recommendation_template": {
                    "action": "Nothing",
                    "impact": "None"
                }
            }
        ]
        
        snapshot = RestaurantSnapshot(
            timestamp=datetime.utcnow(),
            restaurant_status="OPEN",
            current_occupancy=10,
            current_queue_length=0,
            average_wait_time=0.0,
            active_guests=10,
            active_staff=2,
            staff_utilization=50.0,
            zone_status={},
            table_status={},
            host_status={},
            kitchen_status={},
            diagnostic_summary={},
            current_alerts=[],
            health_score=100.0,
            overall_confidence=1.0,
            system_status="HEALTHY"
        )
        
        decisions = self.intel_layer.evaluate_snapshot(snapshot)
        self.assertEqual(len(decisions), 0)

if __name__ == '__main__':
    unittest.main()
