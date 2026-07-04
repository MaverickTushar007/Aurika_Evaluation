from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Any

@dataclass(frozen=True)
class ZoneStatus:
    zone_name: str
    current_guests: int
    average_dwell: float
    peak_dwell: float
    occupancy_percent: float
    congestion_level: str
    confidence: float

@dataclass(frozen=True)
class RestaurantSnapshot:
    timestamp: datetime
    restaurant_status: str
    current_occupancy: int
    current_queue_length: int
    average_wait_time: float
    active_guests: int
    active_staff: int
    overall_staff_utilization: float
    staff_utilization_by_role: Dict[str, float]
    zone_status: Dict[str, ZoneStatus]
    table_status: Dict[str, Any]
    host_status: Dict[str, Any]
    kitchen_status: Dict[str, Any]
    diagnostic_summary: Dict[str, int]
    current_alerts: List[str]
    health_score: float
    overall_confidence: float
    system_status: str

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the immutable snapshot to a JSON-compatible dictionary."""
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d
