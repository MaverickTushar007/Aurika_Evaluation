# queue_engine.py
"""
Queue Engine: Measures queue counts, wait times, and alert states
using zone events and business_events tables in SQLite.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta

class QueueEngine:
    def __init__(self, db_path: str = "db/customer_intel.db"):
        self.db_path = db_path

    def get_live_queue(self, zone_id: str = "Service_Zone") -> dict:
        """
        Returns the current number of guests in the queue zone.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Count sessions that have 'enter_zone' event in zone_id but no matching 'exit_zone'
        cur.execute("""
            SELECT COUNT(DISTINCT session_id) FROM business_events
            WHERE zone_id = ? AND event_type = 'enter_zone'
            AND session_id NOT IN (
                SELECT session_id FROM business_events
                WHERE zone_id = ? AND event_type = 'exit_zone'
            )
        """, (zone_id, zone_id))
        count = cur.fetchone()[0]
        
        # Calculate estimated wait time (rolling average of the last 5 completed wait times)
        cur.execute("""
            SELECT value FROM business_events
            WHERE zone_id = ? AND event_type = 'served'
            ORDER BY timestamp DESC LIMIT 5
        """, (zone_id,))
        recent_waits = [row[0] for row in cur.fetchall()]
        est_wait = float(pd.Series(recent_waits).mean()) if recent_waits else 0.0
        
        conn.close()
        return {
            "zone_id": zone_id,
            "current_queue_length": count,
            "estimated_wait_time_seconds": round(est_wait, 1)
        }

    def get_queue_metrics_summary(self, start_time: str, end_time: str, zone_id: str = "Service_Zone") -> dict:
        """
        Computes average queue lengths, peak wait times, and customer abandonment rates.
        """
        conn = sqlite3.connect(self.db_path)
        
        # Load served events
        df_events = pd.read_sql_query("""
            SELECT event_type, value, timestamp FROM business_events
            WHERE zone_id = ? AND timestamp BETWEEN ? AND ?
        """, conn, params=(zone_id, start_time, end_time))
        
        conn.close()
        
        if df_events.empty:
            return {
                "avg_queue_wait_seconds": 0.0,
                "peak_queue_wait_seconds": 0.0,
                "abandonment_rate": 0.0
            }
            
        served = df_events[df_events["event_type"] == "served"]
        abandoned = df_events[df_events["event_type"] == "abandoned"]
        
        avg_wait = float(served["value"].mean()) if not served.empty else 0.0
        peak_wait = float(served["value"].max()) if not served.empty else 0.0
        
        total_attempts = len(served) + len(abandoned)
        abandon_rate = float(len(abandoned) / total_attempts) if total_attempts > 0 else 0.0
        
        return {
            "avg_queue_wait_seconds": round(avg_wait, 1),
            "peak_queue_wait_seconds": round(peak_wait, 1),
            "abandonment_rate": round(abandon_rate * 100, 1)
        }
