from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from restaurant_analytics.visit_manager import Visit, VisitManager
from restaurant_analytics.visit_state import GuestState, StaffState
import json

def load_system_config():
    try:
        with open("configs/system.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"metric_smoothing": 0.2}

CONFIG = load_system_config()

@dataclass
class MetricValue:
    metric_name: str
    value: Any
    confidence: float
    last_updated: datetime
    source_events: List[str]

class MetricsEngine:
    """
    Business Intelligence Layer.
    Computes real-time operational KPIs strictly from Visit, State, and Events.
    Does NOT interact with the perception layer.
    """
    def __init__(self, visit_manager: VisitManager):
        self.visit_manager = visit_manager
        self.smoothed_metrics = {}
        self.alpha = CONFIG.get("metric_smoothing", 0.2)
        
    def _apply_ema(self, metric_key: str, current_value: float) -> float:
        if metric_key not in self.smoothed_metrics:
            self.smoothed_metrics[metric_key] = current_value
        else:
            self.smoothed_metrics[metric_key] = (self.alpha * current_value) + ((1 - self.alpha) * self.smoothed_metrics[metric_key])
        return self.smoothed_metrics[metric_key]
        
    def get_guest_metrics(self, visit_id: str) -> Dict[str, MetricValue]:
        visit = self._find_visit_by_id(visit_id)
        if not visit:
            return {}
            
        metrics = {}
        ts = datetime.now(timezone.utc)
        
        # Visit Duration
        duration = (visit.exit_time or ts) - visit.entry_time
        metrics["visit_duration_seconds"] = MetricValue(
            metric_name="Visit Duration",
            value=duration.total_seconds(),
            confidence=visit.overall_confidence,
            last_updated=ts,
            source_events=[e.event_id for e in visit.events]
        )
        
        # Wait Time
        wait_time = 0.0
        wait_start = None
        for state in visit.state_history:
            if state.new_state == GuestState.WAITING.value:
                wait_start = state.timestamp
            elif wait_start and state.previous_state == GuestState.WAITING.value:
                wait_time += (state.timestamp - wait_start).total_seconds()
                wait_start = None
                
        if wait_start and visit.current_state == GuestState.WAITING.value:
            wait_time += (ts - wait_start).total_seconds()
            
        metrics["waiting_time_seconds"] = MetricValue(
            metric_name="Waiting Time",
            value=wait_time,
            confidence=visit.overall_confidence,
            last_updated=ts,
            source_events=[s.transition_id for s in visit.state_history if s.new_state == GuestState.WAITING.value]
        )
        
        # Zone Dwell Time
        if visit.current_zone and visit.zone_entry_time:
            current_dwell = (ts - visit.zone_entry_time).total_seconds()
            metrics["current_zone_dwell_seconds"] = MetricValue(
                metric_name="Current Zone Dwell",
                value=current_dwell,
                confidence=visit.overall_confidence,
                last_updated=ts,
                source_events=[]
            )
            
        return metrics

    def get_restaurant_metrics(self) -> Dict[str, MetricValue]:
        ts = datetime.now(timezone.utc)
        active_guests = [v for v in self.visit_manager.active_visits.values() if v.role == "guest"]
        
        occupancy = len(active_guests)
        waiting_guests = [v for v in active_guests if v.current_state == GuestState.WAITING.value]
        queue_length = len(waiting_guests)
        
        # Apply anti-flicker smoothing
        smooth_occ = self._apply_ema("current_occupancy", occupancy)
        smooth_queue = self._apply_ema("queue_length", queue_length)
        
        avg_conf = sum(v.overall_confidence for v in active_guests) / occupancy if occupancy > 0 else 1.0
        
        return {
            "current_occupancy": MetricValue("Current Occupancy", smooth_occ, avg_conf, ts, []),
            "queue_length": MetricValue("Queue Length", smooth_queue, avg_conf, ts, [])
        }
        
    def get_staff_metrics(self) -> Dict[str, MetricValue]:
        ts = datetime.now(timezone.utc)
        active_staff = [v for v in self.visit_manager.active_visits.values() if v.role == "staff"]
        
        roles = ["Host", "Waiter", "Manager", "Cleaner", "Kitchen", "Dishwasher", "Unknown"]
        results = {}
        for r in roles:
            role_staff = [v for v in active_staff if v.metrics.get("staff_role", "Unknown").capitalize() == r]
            count = len(role_staff)
            idle = len([v for v in role_staff if v.current_state == StaffState.IDLE.value])
            util = ((count - idle) / count) * 100 if count > 0 else 0.0
            avg_conf = sum(v.overall_confidence for v in role_staff) / count if count > 0 else 1.0
            
            # NOTE: EMA deliberately removed per forensic audit
            results[f"{r.lower()}_utilization_percent"] = MetricValue(f"{r} Utilization", util, avg_conf, ts, [])
            
        # Overall staff utilization
        total_count = len(active_staff)
        total_idle = len([v for v in active_staff if v.current_state == StaffState.IDLE.value])
        total_util = ((total_count - total_idle) / total_count) * 100 if total_count > 0 else 0.0
        total_conf = sum(v.overall_confidence for v in active_staff) / total_count if total_count > 0 else 1.0
        results["overall_staff_utilization_percent"] = MetricValue("Overall Staff Utilization", total_util, total_conf, ts, [])
        
        return results
        
    def get_zone_metrics(self) -> Dict[str, MetricValue]:
        ts = datetime.now(timezone.utc)
        zone_counts = {}
        for visit in self.visit_manager.active_visits.values():
            if visit.current_zone:
                zone_counts[visit.current_zone] = zone_counts.get(visit.current_zone, 0) + 1
                
        metrics = {}
        for zone, count in zone_counts.items():
            metrics[f"zone_occupancy_{zone}"] = MetricValue(f"Zone Occupancy ({zone})", count, 1.0, ts, [])
        return metrics
        
    def get_live_summary(self) -> Dict[str, Any]:
        """Provides a holistic snapshot for Dashboards."""
        restaurant = self.get_restaurant_metrics()
        staff = self.get_staff_metrics()
        return {
            "occupancy": restaurant["current_occupancy"].value,
            "queue_length": restaurant["queue_length"].value,
            "staff_utilization": staff["staff_utilization_percent"].value,
            "confidence": restaurant["current_occupancy"].confidence
        }
        
    def _find_visit_by_id(self, visit_id: str) -> Optional[Visit]:
        # Search active visits
        for v in self.visit_manager.active_visits.values():
            if v.visit_id == visit_id:
                return v
        return None
