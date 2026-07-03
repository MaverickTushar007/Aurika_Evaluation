# analytics_engine.py
"""
Analytics Engine: Computes Business KPIs, visitor conversion funnels,
and compiles master executive indicators from SQLite data.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta

from occupancy_engine import OccupancyEngine
from queue_engine import QueueEngine
from heatmap_generator import HeatmapGenerator

class AnalyticsEngine:
    def __init__(self, db_path: str = "db/customer_intel.db"):
        self.db_path = db_path
        self.occupancy = OccupancyEngine(db_path)
        self.queue = QueueEngine(db_path)
        self.heatmap = HeatmapGenerator(db_path)

    def get_live_metrics(self) -> dict:
        """Compiles real-time occupancy, queue length, and wait times."""
        occ = self.occupancy.get_live_occupancy()
        q = self.queue.get_live_queue("Service_Zone")
        
        # Staff to guest ratio
        ratio = float(occ["guests"] / max(occ["staff"], 1))
        
        return {
            "timestamp": occ["timestamp"],
            "occupancy": {
                "total": occ["total"],
                "guests": occ["guests"],
                "staff": occ["staff"],
                "guest_to_staff_ratio": round(ratio, 1)
            },
            "queue": q
        }

    def calculate_conversion_funnel(self, start_time: str, end_time: str) -> dict:
        """
        Calculates funnel steps:
        1. Entrances (total unique sessions)
        2. Queue checkout (unique sessions entering Service_Zone)
        3. Completed transactions (unique sessions marked served)
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # 1. Total unique sessions
        cur.execute("""
            SELECT COUNT(DISTINCT session_id) FROM temporal_sessions
            WHERE start_time BETWEEN ? AND ?
        """, (start_time, end_time))
        entrances = cur.fetchone()[0]
        
        # 2. Queue checkout entries
        cur.execute("""
            SELECT COUNT(DISTINCT session_id) FROM business_events
            WHERE zone_id = 'Service_Zone' AND event_type = 'enter_zone'
            AND timestamp BETWEEN ? AND ?
        """, (start_time, end_time))
        checkout = cur.fetchone()[0]
        
        # 3. Completed transactions (served)
        cur.execute("""
            SELECT COUNT(DISTINCT session_id) FROM business_events
            WHERE zone_id = 'Service_Zone' AND event_type = 'served'
            AND timestamp BETWEEN ? AND ?
        """, (start_time, end_time))
        served = cur.fetchone()[0]
        
        conn.close()
        
        funnel = {
            "entrances": entrances,
            "checkout_attempts": checkout,
            "transactions": served,
            "checkout_conversion": round((checkout / max(entrances, 1)) * 100, 1),
            "service_conversion": round((served / max(checkout, 1)) * 100, 1)
        }
        return funnel

    def compute_operational_efficiency(self, start_time: str, end_time: str) -> dict:
        """
        Computes Operational Efficiency Score (0 to 100) based on wait times,
        staff availability, and abandonment rates.
        """
        q_summary = self.queue.get_queue_metrics_summary(start_time, end_time)
        occ_summary = self.occupancy.get_occupancy_summary(start_time, end_time)
        
        # Operational Efficiency calculation heuristic:
        # Start at 100 points, subtract based on wait times and abandonment
        score = 100.0
        
        # Wait time penalty (subtract 1 point per 10 seconds of average wait time)
        avg_wait = q_summary["avg_queue_wait_seconds"]
        score -= (avg_wait / 10.0)
        
        # Abandonment rate penalty (subtract 1.5 points per 1% abandonment rate)
        abandon_rate = q_summary["abandonment_rate"]
        score -= (abandon_rate * 1.5)
        
        score = max(0.0, min(100.0, score))
        
        return {
            "operational_efficiency_score": round(score, 1),
            "avg_dwell_time_seconds": round(q_summary["avg_queue_wait_seconds"], 1),
            "space_utilization_percent": round((occ_summary["avg_occupancy"] / 30.0) * 100, 1), # Capacity baseline 30
            "abandonment_rate": abandon_rate
        }
