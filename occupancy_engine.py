# occupancy_engine.py
"""
Occupancy Engine: Calculates live, average, peak, and historical occupancy
based on temporal_sessions and staff_resolutions tables in SQLite.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta

class OccupancyEngine:
    def __init__(self, db_path: str = "db/customer_intel.db"):
        self.db_path = db_path

    def get_live_occupancy(self, timestamp: str = None) -> dict:
        """
        Returns the count of active guest and staff sessions at the given timestamp (or now).
        A session is active if start_time <= timestamp and (end_time is None or end_time >= timestamp).
        """
        if not timestamp:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Count all active sessions
        cur.execute("""
            SELECT session_id FROM temporal_sessions
            WHERE start_time <= ? AND (end_time IS NULL OR end_time >= ?)
        """, (timestamp, timestamp))
        active_sessions = [row[0] for row in cur.fetchall()]
        
        if not active_sessions:
            conn.close()
            return {"timestamp": timestamp, "total": 0, "guests": 0, "staff": 0}
            
        # Segregate into staff vs guest
        placeholders = ",".join("?" for _ in active_sessions)
        cur.execute(f"""
            SELECT session_id, staff_id FROM staff_resolutions
            WHERE session_id IN ({placeholders})
        """, active_sessions)
        resolved_staff = {row[0] for row in cur.fetchall() if row[1] is not None}
        
        staff_count = len(resolved_staff)
        guest_count = len(active_sessions) - staff_count
        
        conn.close()
        return {
            "timestamp": timestamp,
            "total": len(active_sessions),
            "guests": guest_count,
            "staff": staff_count
        }

    def get_occupancy_history(self, start_time: str, end_time: str, interval_minutes: int = 5) -> list:
        """
        Generates a timeline of occupancy snapshots at periodic intervals between start and end times.
        """
        dt_start = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        dt_end = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        
        timeline = []
        current_dt = dt_start
        while current_dt <= dt_end:
            ts_str = current_dt.strftime("%Y-%m-%d %H:%M:%S")
            occ = self.get_live_occupancy(ts_str)
            timeline.append({
                "timestamp": ts_str,
                "total": occ["total"],
                "guests": occ["guests"],
                "staff": occ["staff"]
            })
            current_dt += timedelta(minutes=interval_minutes)
            
        return timeline

    def get_occupancy_summary(self, start_time: str, end_time: str) -> dict:
        """
        Computes peak and average occupancy metrics across a given historical window.
        """
        timeline = self.get_occupancy_history(start_time, end_time, interval_minutes=1)
        if not timeline:
            return {"avg_occupancy": 0.0, "peak_occupancy": 0, "peak_timestamp": None}
            
        df = pd.DataFrame(timeline)
        avg_occ = float(df["total"].mean())
        peak_idx = df["total"].idxmax()
        peak_occ = int(df.loc[peak_idx, "total"])
        peak_ts = df.loc[peak_idx, "timestamp"]
        
        return {
            "avg_occupancy": round(avg_occ, 2),
            "peak_occupancy": peak_occ,
            "peak_timestamp": peak_ts
        }
