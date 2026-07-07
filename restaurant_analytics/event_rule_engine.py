import os
import json
from typing import Dict, List, Optional, Tuple, Any

class EventRuleEngine:
    _rules = []
    last_eval_time_ms = 0.0

    @classmethod
    def load_rules(cls, config_path: str = "configs/event_rules.json"):
        if not os.path.exists(config_path):
            cls._rules = []
            return
        try:
            with open(config_path, "r") as f:
                data = json.load(f)
                cls._rules = data.get("rules", [])
        except Exception as e:
            print(f"Error loading event rules: {e}")
            cls._rules = []

    @classmethod
    def evaluate(cls, transition: Any, camera_role: str, metadata: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        import time
        t_start = time.time()
        res = cls._evaluate_internal(transition, camera_role, metadata)
        cls.last_eval_time_ms = (time.time() - t_start) * 1000.0
        return res

    @classmethod
    def _evaluate_internal(cls, transition: Any, camera_role: str, metadata: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        if not cls._rules:
            cls.load_rules()

        prev = transition.previous_zone or "OUTSIDE"
        curr = transition.current_zone or "OUTSIDE"
        journey_state = metadata.get("journey_state", "UNKNOWN")
        
        # Check transition validity
        # E.g. Reject Table -> Entrance directly, Queue -> Reception directly
        if prev == "Table 101" and curr == "Entrance":
            print(f"RULE REJECTED: Impossible direct transition {prev} -> {curr}")
            return None, None
        if prev == "Queue" and curr == "Reception":
            print(f"RULE REJECTED: Impossible direct transition {prev} -> {curr}")
            return None, None
        if prev == "Dining" and curr == "OUTSIDE" and "Exit" not in metadata.get("zone_history", []):
            print(f"RULE REJECTED: Dining -> OUTSIDE without Exit gate transition")
            return None, None

        matching_rules = []
        for r in cls._rules:
            if not r.get("enabled", True):
                continue
            if camera_role not in r.get("camera_roles", []):
                continue
            
            # Match zones
            rule_from = r.get("from")
            rule_to = r.get("to")
            rule_state = r.get("journey_state", "*")
            
            from_matches = (rule_from == "*" or rule_from.lower() == prev.lower() or 
                            (rule_from.lower() in prev.lower()) or
                            (prev.lower() in rule_from.lower()))
            to_matches = (rule_to == "*" or rule_to.lower() == curr.lower() or 
                          (rule_to.lower() in curr.lower()) or
                          (curr.lower() in rule_to.lower()))
            state_matches = (rule_state == "*" or rule_state.lower() == "any" or rule_state.lower() == journey_state.lower())
            
            if from_matches and to_matches and state_matches:
                matching_rules.append(r)

        if not matching_rules:
            return None, None

        # Sort by priority desc
        matching_rules.sort(key=lambda x: x.get("priority", 0), reverse=True)

        for r in matching_rules:
            # Check conditions
            conds = r.get("conditions", {})
            passed = True
            
            if "minimum_confidence" in conds:
                if metadata.get("confidence", 1.0) < conds["minimum_confidence"]:
                    passed = False
            if "minimum_track_age" in conds:
                if metadata.get("track_age", 0) < conds["minimum_track_age"]:
                    passed = False
                    
            if passed:
                return r["emit"], r["id"]

        return None, None
