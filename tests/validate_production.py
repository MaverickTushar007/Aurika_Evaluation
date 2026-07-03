# tests/validate_production.py
"""
Production Validation Suite: Automatically tests REST endpoints,
queries database constraint integrities, records API latencies,
and certifies the release candidate.
"""

import os
import sys
import time
import sqlite3
import httpx
import threading
import uvicorn
from datetime import datetime, timedelta

# Start FastAPI in a background thread
from analytics_api import app

def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="warning")

def run_validation():
    # Allow uvicorn to boot up
    time.sleep(2.0)
    
    print("\n=============================================")
    # 1. API Validation
    print("RUNNING API VALIDATION...")
    endpoints = [
        "/analytics/live",
        "/analytics/today",
        "/analytics/queue",
        "/analytics/heatmap",
        "/analytics/reports"
    ]
    
    api_results = []
    client = httpx.Client(base_url="http://127.0.0.1:8002")
    
    for ep in endpoints:
        t0 = time.time()
        try:
            res = client.get(ep)
            latency = (time.time() - t0) * 1000.0
            status = res.status_code
            
            # Simple schema sanity checks
            valid_schema = False
            if status == 200:
                data = res.json()
                if ep == "/analytics/live":
                    valid_schema = "occupancy" in data and "queue" in data
                elif ep == "/analytics/today":
                    valid_schema = "funnel" in data and "efficiency" in data
                elif ep == "/analytics/queue":
                    valid_schema = "current_queue_length" in data
                elif ep == "/analytics/heatmap":
                    valid_schema = "grid" in data
                elif ep == "/analytics/reports":
                    valid_schema = "file_url" in data
                    
            api_results.append({
                "endpoint": ep,
                "status": status,
                "latency_ms": round(latency, 2),
                "schema_valid": valid_schema
            })
            print(f"  GET {ep} - Status: {status} | Latency: {latency:.1f}ms | Schema: {'Pass' if valid_schema else 'Fail'}")
        except Exception as e:
            print(f"  GET {ep} - FAILED: {e}")
            api_results.append({
                "endpoint": ep,
                "status": 500,
                "latency_ms": 0.0,
                "schema_valid": False
            })
            
    # 2. Database Validation
    print("\nRUNNING DATABASE SCHEMA VALIDATION...")
    db_path = "db/customer_intel.db"
    db_valid = True
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        try:
            # Check table existence
            tables = ["raw_observations", "temporal_sessions", "staff_resolutions", "business_events"]
            for t in tables:
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,))
                assert cur.fetchone() is not None, f"Table {t} missing"
                
            # Verify no orphaned staff resolutions (referencing sessions)
            cur.execute("""
                SELECT COUNT(*) FROM staff_resolutions
                WHERE session_id NOT IN (SELECT session_id FROM temporal_sessions)
            """)
            orphans = cur.fetchone()[0]
            assert orphans == 0, f"Found {orphans} orphaned staff resolution records"
            
            # Verify timestamp ordering consistency
            cur.execute("""
                SELECT COUNT(*) FROM temporal_sessions
                WHERE end_time IS NOT NULL AND start_time > end_time
            """)
            corrupt_timestamps = cur.fetchone()[0]
            assert corrupt_timestamps == 0, f"Found {corrupt_timestamps} sessions with end_time before start_time"
            
            print("  Table Schemas: OK")
            print("  Foreign Key Constraints: OK (No orphans)")
            print("  Temporal Chronology: OK (No corrupt timestamps)")
        except Exception as e:
            print(f"  DB CHECK FAILED: {e}")
            db_valid = False
        finally:
            conn.close()
    else:
        print("  DB CHECK FAILED: customer_intel.db not found")
        db_valid = False
        
    print("\n=============================================")
    print("Acceptance Results Summary:")
    print(f"  API Validation: {'PASSED' if all(r['schema_valid'] for r in api_results) else 'FAILED'}")
    print(f"  Database Validation: {'PASSED' if db_valid else 'FAILED'}")
    print("=============================================\n")

def main():
    # Run uvicorn in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Run tests
    run_validation()

if __name__ == "__main__":
    main()
