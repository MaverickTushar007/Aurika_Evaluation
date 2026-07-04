import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from restaurant_analytics.restaurant_state import RestaurantSnapshot

@dataclass(frozen=True)
class OperationalDecision:
    decision_id: str
    title: str
    description: str
    severity: str
    priority: int
    confidence: float
    reason: str
    supporting_metrics: Dict[str, Any]
    supporting_events: List[str]
    recommended_action: str
    estimated_impact: str
    generated_timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['generated_timestamp'] = self.generated_timestamp.isoformat()
        return d

class OperationalIntelligenceLayer:
    """
    Consumes RestaurantSnapshots to evaluate declarative rules, 
    generating actionable OperationalDecisions.
    """
    def __init__(self, rules_path: str = "configs/rules.json"):
        self.rules_path = rules_path
        self.rules = self._load_rules()
        self.active_decisions: List[OperationalDecision] = []
        
    def _load_rules(self) -> List[Dict[str, Any]]:
        try:
            with open(self.rules_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[OperationalIntelligenceLayer] Error loading rules: {e}")
            return []
            
    def _evaluate_condition(self, condition: Dict[str, Any], snapshot: RestaurantSnapshot) -> bool:
        metric = condition.get("metric")
        operator = condition.get("operator")
        threshold = condition.get("threshold")
        
        # Helper to safely extract metric from snapshot
        def get_metric_value(metric_name: str) -> float:
            if hasattr(snapshot, metric_name):
                return getattr(snapshot, metric_name)
            if metric_name == "diagnostic_count":
                return sum(snapshot.diagnostic_summary.values())
            return 0.0
            
        val = get_metric_value(metric)
        if operator == ">":
            return val > threshold
        elif operator == "<":
            return val < threshold
        elif operator == "==":
            return val == threshold
            
        return False
        
    def _evaluate_rule(self, rule: Dict[str, Any], snapshot: RestaurantSnapshot) -> Optional[OperationalDecision]:
        if not rule.get("enabled", True):
            return None
            
        cond = rule.get("conditions", {})
        if not cond:
            return None
            
        triggered = self._evaluate_condition(cond, snapshot)
        
        # Check secondary condition if exists
        if triggered and "secondary_metric" in cond:
            sec_cond = {
                "metric": cond["secondary_metric"],
                "operator": cond["secondary_operator"],
                "threshold": cond["secondary_threshold"]
            }
            triggered = self._evaluate_condition(sec_cond, snapshot)
            
        if triggered:
            # Build decision
            support_metrics = {
                cond["metric"]: getattr(snapshot, cond["metric"], 0) if hasattr(snapshot, cond["metric"]) else None
            }
            if "secondary_metric" in cond:
                support_metrics[cond["secondary_metric"]] = getattr(snapshot, cond["secondary_metric"], 0) if hasattr(snapshot, cond["secondary_metric"]) else None
                
            return OperationalDecision(
                decision_id=str(uuid.uuid4()),
                title=rule["name"],
                description=rule["description"],
                severity=rule["severity"],
                priority=rule["priority"],
                confidence=snapshot.overall_confidence,
                reason=f"Rule {rule['rule_id']} triggered by {cond['metric']} matching condition.",
                supporting_metrics=support_metrics,
                supporting_events=snapshot.current_alerts, # Bundle active alerts as supporting events
                recommended_action=rule["recommendation_template"]["action"],
                estimated_impact=rule["recommendation_template"]["impact"],
                generated_timestamp=datetime.now(timezone.utc)
            )
        return None

    def evaluate_snapshot(self, snapshot: RestaurantSnapshot) -> List[OperationalDecision]:
        decisions = []
        for rule in self.rules:
            decision = self._evaluate_rule(rule, snapshot)
            if decision:
                decisions.append(decision)
                
        # Priority Engine: Rank recommendations
        # Lower priority integer = higher priority ranking (1 is top)
        decisions.sort(key=lambda d: d.priority)
        
        self.active_decisions = decisions
        return decisions
        
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        # Alerts are just decisions stripped down to the alert portion
        return [{"title": d.title, "severity": d.severity, "reason": d.reason} for d in self.active_decisions]
        
    def get_recommendations(self) -> List[Dict[str, str]]:
        return [{"action": d.recommended_action, "impact": d.estimated_impact} for d in self.active_decisions]
        
    def get_prioritized_decisions(self) -> List[OperationalDecision]:
        return self.active_decisions
        
    def get_operational_summary(self) -> Dict[str, Any]:
        return {
            "total_decisions": len(self.active_decisions),
            "critical_alerts": len([d for d in self.active_decisions if d.severity == "CRITICAL"]),
            "top_recommendation": self.active_decisions[0].recommended_action if self.active_decisions else None
        }
