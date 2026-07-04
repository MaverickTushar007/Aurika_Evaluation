from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from restaurant_analytics.metrics_engine import MetricsEngine
from restaurant_analytics.restaurant_state import RestaurantSnapshot, ZoneStatus
from restaurant_analytics.persistence_adapter import PersistenceAdapter

class OperationalStateEngine:
    """
    Restaurant Operational State Engine (ROSE).
    The canonical source of operational truth. Synthesizes Metrics, Visits, and Diagnostics 
    into a single immutable RestaurantSnapshot.
    """
    def __init__(self, metrics_engine: MetricsEngine, persistence_adapter: Optional[PersistenceAdapter] = None):
        self.metrics_engine = metrics_engine
        self.persistence = persistence_adapter or PersistenceAdapter()
        self._current_snapshot: Optional[RestaurantSnapshot] = None
        
    def _calculate_zone_congestion(self, occupancy: int, avg_dwell: float) -> str:
        if occupancy >= 10:
            return "SEVERE"
        elif occupancy >= 5:
            return "MODERATE"
        return "LOW"
        
    def _calculate_health_score(self, queue_length: int, avg_wait: float, staff_utilization: float, active_alerts: int) -> float:
        """
        Calculates a derived 0-100 score. 
        Penalizes long queues, high waits, low staff utilization, and system alerts.
        """
        score = 100.0
        
        # Penalize for queue length
        score -= min(queue_length * 5, 30)
        
        # Penalize for average wait time (> 30s)
        if avg_wait > 30:
            score -= min((avg_wait - 30) * 0.5, 30)
            
        # Penalize for very low staff utilization (if we know staff exist)
        if staff_utilization < 20 and staff_utilization > 0:
            score -= 10
            
        # Penalize for active alerts
        score -= min(active_alerts * 5, 20)
        
        return max(0.0, min(100.0, score))
        
    def _build_snapshot(self) -> RestaurantSnapshot:
        ts = datetime.now(timezone.utc)
        
        # Fetch metrics
        restaurant_metrics = self.metrics_engine.get_restaurant_metrics()
        staff_metrics = self.metrics_engine.get_staff_metrics()
        zone_metrics = self.metrics_engine.get_zone_metrics()
        
        occupancy = restaurant_metrics.get("current_occupancy").value if "current_occupancy" in restaurant_metrics else 0
        queue_len = restaurant_metrics.get("queue_length").value if "queue_length" in restaurant_metrics else 0
        
        overall_staff_util = staff_metrics.get("overall_staff_utilization_percent").value if "overall_staff_utilization_percent" in staff_metrics else 0.0
        
        staff_util_by_role = {}
        for role in ["host", "waiter", "manager", "cleaner", "kitchen", "dishwasher", "unknown"]:
            key = f"{role}_utilization_percent"
            if key in staff_metrics:
                staff_util_by_role[role.capitalize()] = staff_metrics[key].value
        
        # Determine average wait time from active waiting guests
        wait_times = []
        active_guests = [v for v in self.metrics_engine.visit_manager.active_visits.values() if v.role == "guest"]
        for g in active_guests:
            m = self.metrics_engine.get_guest_metrics(g.visit_id)
            if "waiting_time_seconds" in m and m["waiting_time_seconds"].value > 0:
                wait_times.append(m["waiting_time_seconds"].value)
        
        avg_wait = sum(wait_times) / len(wait_times) if wait_times else 0.0
        
        # Zone Statuses
        zone_statuses = {}
        for metric_name, m_val in zone_metrics.items():
            zone_name = metric_name.replace("zone_occupancy_", "")
            
            # Find guests in this zone to calc dwell
            dwells = []
            for g in active_guests:
                if g.current_zone == zone_name:
                    gm = self.metrics_engine.get_guest_metrics(g.visit_id)
                    if "current_zone_dwell_seconds" in gm:
                        dwells.append(gm["current_zone_dwell_seconds"].value)
            
            avg_dwell = sum(dwells) / len(dwells) if dwells else 0.0
            peak_dwell = max(dwells) if dwells else 0.0
            
            zone_statuses[zone_name] = ZoneStatus(
                zone_name=zone_name,
                current_guests=m_val.value,
                average_dwell=avg_dwell,
                peak_dwell=peak_dwell,
                occupancy_percent=0.0, # Extension: require total zone capacity mapping
                congestion_level=self._calculate_zone_congestion(m_val.value, avg_dwell),
                confidence=m_val.confidence
            )
            
        # Diagnostics
        recent_diagnostics = self.persistence.get_recent_diagnostics(limit=20)
        alerts = []
        diag_summary = {}
        for d in recent_diagnostics:
            try:
                # SQLite isoformat might have Z or not. Handle safely.
                d_ts = datetime.fromisoformat(d['timestamp'].replace('Z', '+00:00'))
                # Replace tzinfo to allow naive substraction if d_ts is aware
                if d_ts.tzinfo is not None:
                    d_ts = d_ts.replace(tzinfo=None)
                if ts - d_ts < timedelta(minutes=5):
                    alerts.append(f"{d['event_type']}: {d['reason']}")
                    diag_summary[d['event_type']] = diag_summary.get(d['event_type'], 0) + 1
            except Exception:
                pass
                
        health_score = self._calculate_health_score(queue_len, avg_wait, overall_staff_util, len(alerts))
        overall_conf = restaurant_metrics.get("current_occupancy").confidence if "current_occupancy" in restaurant_metrics else 1.0
        
        snapshot = RestaurantSnapshot(
            timestamp=ts,
            restaurant_status="OPEN",
            current_occupancy=occupancy,
            current_queue_length=queue_len,
            average_wait_time=avg_wait,
            active_guests=len(active_guests),
            active_staff=len([v for v in self.metrics_engine.visit_manager.active_visits.values() if v.role == "staff"]),
            overall_staff_utilization=overall_staff_util,
            staff_utilization_by_role=staff_util_by_role,
            zone_status=zone_statuses,
            table_status={},
            host_status={},
            kitchen_status={},
            diagnostic_summary=diag_summary,
            current_alerts=alerts,
            health_score=health_score,
            overall_confidence=overall_conf,
            system_status="HEALTHY" if health_score >= 70 else "DEGRADED"
        )
        return snapshot

    def refresh(self):
        """Forces a rebuild of the immutable snapshot."""
        self._current_snapshot = self._build_snapshot()

    def get_current_snapshot(self) -> RestaurantSnapshot:
        """Retrieves the canonical representation of the restaurant."""
        self.refresh()
        return self._current_snapshot
        
    def get_restaurant_health(self) -> float:
        snap = self.get_current_snapshot()
        return snap.health_score
        
    def get_alerts(self) -> List[str]:
        snap = self.get_current_snapshot()
        return snap.current_alerts
