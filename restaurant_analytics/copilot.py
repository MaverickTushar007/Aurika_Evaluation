from typing import List, Dict, Any, Optional
from restaurant_analytics.restaurant_state import RestaurantSnapshot
from restaurant_analytics.operational_intelligence import OperationalDecision

class AICopilot:
    """
    AI Copilot Explanation Engine.
    Provides natural language explanations strictly grounded in Snapshot and Decision evidence.
    Never hallucinates or computes its own logic.
    """
    def __init__(self, snapshot: RestaurantSnapshot, decisions: List[OperationalDecision]):
        self.snapshot = snapshot
        self.decisions = decisions
        
    def answer(self, question_type: str, context: Optional[str] = None) -> str:
        """
        Provides a deterministic explanation based on the question type.
        """
        if question_type == "waiting_count":
            return f"There are currently {self.snapshot.current_queue_length} guests waiting, with an average wait time of {self.snapshot.average_wait_time/60:.1f} minutes."
            
        elif question_type == "health_status":
            issues = []
            if self.snapshot.current_queue_length > 5:
                issues.append("a long queue")
            if self.snapshot.average_wait_time > 300:
                issues.append("extended wait times")
            if len(self.snapshot.current_alerts) > 0:
                issues.append(f"{len(self.snapshot.current_alerts)} active system alerts")
                
            reason = " and ".join(issues) if issues else "normal operating conditions"
            return f"The restaurant health is {self.snapshot.health_score}/100. This is primarily driven by {reason}."
            
        elif question_type == "top_recommendation":
            if not self.decisions:
                return "There are currently no active recommendations."
            top = self.decisions[0]
            return f"The highest priority recommendation is to: '{top.recommended_action}'. This is expected to {top.estimated_impact.lower()}."
            
        elif question_type == "recommendation_reason":
            if not self.decisions:
                return "No recommendations available."
            # If context is passed (e.g. decision ID), explain that one. Otherwise explain top.
            decision = next((d for d in self.decisions if d.decision_id == context), self.decisions[0])
            
            metrics_str = ", ".join([f"{k} = {v}" for k, v in decision.supporting_metrics.items()])
            return (f"This recommendation was generated because: {decision.reason} "
                    f"The supporting evidence is {metrics_str}, with a system confidence of {decision.confidence*100:.1f}%.")
                    
        elif question_type == "busiest_zone":
            if not self.snapshot.zone_status:
                return "Zone data is currently unavailable."
            busiest = max(self.snapshot.zone_status.values(), key=lambda z: z.current_guests)
            return (f"The busiest zone is '{busiest.zone_name}' with {busiest.current_guests} guests. "
                    f"The congestion level is evaluated as {busiest.congestion_level}.")
                    
        elif question_type == "system_confidence":
            return f"The overall system confidence is {self.snapshot.overall_confidence*100:.1f}%. This is a weighted average of tracking, zone stability, and state evaluations."
            
        return "I can only provide explanations grounded in the current Operational Snapshot."
