# zone_engine.py
"""
Zone Engine: Calculates zone occupancy, dwell times, and transitions
based on business_events table in SQLite.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta

class ZoneEngine:
    def __init__(self, db_path: str = "db/customer_intel.db"):
        self.db_path = db_path
        
    def get_live_zone_occupancy(self, zone_id: str) -> int:
        """
        Returns the current number of people (sessions) in a specific zone.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT COUNT(DISTINCT session_id) FROM business_events
            WHERE zone_id = ? AND event_type = 'enter_zone'
            AND session_id NOT IN (
                SELECT session_id FROM business_events
                WHERE zone_id = ? AND event_type = 'exit_zone'
            )
        """, (zone_id, zone_id))
        count = cur.fetchone()[0]
        conn.close()
        return count

    def get_all_live_occupancies(self) -> dict:
        """
        Returns the live occupancy for all zones.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Get all distinct zones that have entries
        cur.execute("SELECT DISTINCT zone_id FROM business_events WHERE zone_id IS NOT NULL")
        zones = [row[0] for row in cur.fetchall()]
        conn.close()
        
        occupancies = {}
        for z in zones:
            occupancies[z] = self.get_live_zone_occupancy(z)
            
        return occupancies

    def get_zone_dwell_times(self, zone_id: str, start_time: str, end_time: str) -> dict:
        """
        Computes the average and peak dwell times for a zone in the specified period.
        Requires matched enter_zone and exit_zone events.
        """
        conn = sqlite3.connect(self.db_path)
        
        # Fetch entries and exits
        df_entries = pd.read_sql_query("""
            SELECT session_id, timestamp as entry_time FROM business_events
            WHERE zone_id = ? AND event_type = 'enter_zone' AND timestamp BETWEEN ? AND ?
        """, conn, params=(zone_id, start_time, end_time))
        
        df_exits = pd.read_sql_query("""
            SELECT session_id, timestamp as exit_time FROM business_events
            WHERE zone_id = ? AND event_type = 'exit_zone' AND timestamp BETWEEN ? AND ?
        """, conn, params=(zone_id, start_time, end_time))
        
        conn.close()
        
        if df_entries.empty or df_exits.empty:
            return {"avg_dwell_seconds": 0.0, "peak_dwell_seconds": 0.0, "completed_visits": 0}
            
        # Merge on session_id to calculate duration
        df_merged = pd.merge(df_entries, df_exits, on="session_id")
        
        if df_merged.empty:
            return {"avg_dwell_seconds": 0.0, "peak_dwell_seconds": 0.0, "completed_visits": 0}
            
        # Convert timestamps to datetime to compute difference
        df_merged["entry_time"] = pd.to_datetime(df_merged["entry_time"])
        df_merged["exit_time"] = pd.to_datetime(df_merged["exit_time"])
        
        # Calculate duration in seconds
        df_merged["dwell_seconds"] = (df_merged["exit_time"] - df_merged["entry_time"]).dt.total_seconds().abs()
        
        avg_dwell = df_merged["dwell_seconds"].mean()
        peak_dwell = df_merged["dwell_seconds"].max()
        completed = len(df_merged)
        
        return {
            "avg_dwell_seconds": round(avg_dwell, 1),
            "peak_dwell_seconds": round(peak_dwell, 1),
            "completed_visits": completed
        }

    def get_zone_transitions(self, start_time: str, end_time: str) -> dict:
        """
        Computes counts of transitions between zones (e.g. Entrance -> Reception).
        Returns a dictionary mapping 'ZoneA -> ZoneB' to count.
        """
        conn = sqlite3.connect(self.db_path)
        
        # Get all enter_zone events ordered by time per session
        df_enters = pd.read_sql_query("""
            SELECT session_id, zone_id, timestamp FROM business_events
            WHERE event_type = 'enter_zone' AND timestamp BETWEEN ? AND ?
            ORDER BY session_id, timestamp
        """, conn, params=(start_time, end_time))
        
        conn.close()
        
        if df_enters.empty:
            return {}
            
        transitions = {}
        # Group by session and find sequential zone changes
        for session_id, group in df_enters.groupby("session_id"):
            zones = group["zone_id"].tolist()
            for i in range(len(zones) - 1):
                z_from = zones[i]
                z_to = zones[i+1]
                if z_from != z_to:
                    trans_key = f"{z_from} -> {z_to}"
                    transitions[trans_key] = transitions.get(trans_key, 0) + 1
                    
        return transitions
