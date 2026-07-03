# monitoring/runtime_metrics.py
"""
Runtime metrics collector for system performance and track monitoring.
Exports metrics to JSON and CSV.
"""

import os
import csv
import json
import time
import psutil
from datetime import datetime

class RuntimeMetricsCollector:
    def __init__(self, output_dir: str = "monitoring"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.metrics_history = []
        self.t0 = time.time()

    def collect(self, frame_id: int, current_guests: int, current_staff: int,
                total_guests: int, ghost_tracks: int, id_switches: int,
                latency_ms: float, fps: float):
        """Records metrics for a single processed frame/clip step."""
        cpu_pct = psutil.cpu_percent()
        ram_pct = psutil.virtual_memory().percent
        
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "frame_id": frame_id,
            "cpu_percent": cpu_pct,
            "ram_percent": ram_pct,
            "current_guests": current_guests,
            "current_staff": current_staff,
            "total_guests": total_guests,
            "ghost_tracks": ghost_tracks,
            "id_switches": id_switches,
            "latency_ms": latency_ms,
            "fps": fps
        }
        self.metrics_history.append(entry)

    def export_json(self, filename: str = "metrics.json"):
        """Exports metrics history as a structured JSON file."""
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w") as f:
            json.dump(self.metrics_history, f, indent=2)
        return filepath

    def export_csv(self, filename: str = "metrics.csv"):
        """Exports metrics history as a standard CSV file."""
        filepath = os.path.join(self.output_dir, filename)
        if not self.metrics_history:
            return filepath
            
        keys = self.metrics_history[0].keys()
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(self.metrics_history)
        return filepath
