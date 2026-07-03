# heatmap_generator.py
"""
Heatmap Generator: Processes bounding box raw coordinates in SQLite
to generate 2D spatial occupancy grids, walking paths, and route analyses.
"""

import sqlite3
import numpy as np
import pandas as pd

class HeatmapGenerator:
    def __init__(self, db_path: str = "db/customer_intel.db", grid_size: tuple = (20, 20)):
        self.db_path = db_path
        self.grid_size = grid_size  # Width and height divisions

    def get_spatial_points(self, start_time: str = None, end_time: str = None) -> pd.DataFrame:
        """Loads bottom-center coordinates of raw observations inside the window."""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT bbox_x1, bbox_y1, bbox_x2, bbox_y2, timestamp
            FROM raw_observations
        """
        params = []
        if start_time and end_time:
            query += " WHERE timestamp BETWEEN ? AND ?"
            params = [start_time, end_time]
            
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if df.empty:
            return pd.DataFrame(columns=["x", "y"])
            
        # Calculate bottom center
        df["x"] = (df["bbox_x1"] + df["bbox_x2"]) / 2.0
        df["y"] = df["bbox_y2"]
        return df[["x", "y"]]

    def generate_heatmap_grid(self, start_time: str = None, end_time: str = None) -> dict:
        """
        Divides the coordinates space into a grid and returns density values.
        """
        df = self.get_spatial_points(start_time, end_time)
        grid = np.zeros(self.grid_size)
        
        if df.empty:
            return {"grid": grid.tolist(), "busy_zones": [], "dead_zones": []}
            
        # Standardize points between 0 and 1 (or map to a standard coordinate space, e.g. 1920x1080)
        # We divide x by 1920 and y by 1080 to map to normalized coordinates
        df["x_norm"] = (df["x"] / 1920.0).clip(0.0, 0.99)
        df["y_norm"] = (df["y"] / 1080.0).clip(0.0, 0.99)
        
        for _, row in df.iterrows():
            grid_x = int(row["x_norm"] * self.grid_size[0])
            grid_y = int(row["y_norm"] * self.grid_size[1])
            grid[grid_y, grid_x] += 1
            
        # Find busy and dead zones
        busy_threshold = np.percentile(grid, 90) if np.any(grid > 0) else 1.0
        busy_zones = []
        dead_zones = []
        
        for y in range(self.grid_size[1]):
            for x in range(self.grid_size[0]):
                val = float(grid[y, x])
                cell = {"x": x, "y": y, "density": val}
                if val >= busy_threshold and val > 0:
                    busy_zones.append(cell)
                elif val == 0:
                    dead_zones.append(cell)
                    
        return {
            "grid": grid.tolist(),
            "busy_zones": busy_zones[:10],
            "dead_zones": dead_zones[:10]
        }

    def get_walking_paths(self, max_paths: int = 15) -> list:
        """
        Reconstructs the movement trajectories (sequential bottom-center points)
        for the latest visitor sessions.
        """
        # Note: Bbox coordinates are stored in raw_observations. In a real-time system,
        # raw observations are indexed by timestamp and camera. If we want paths, we group by
        # temporal sessions and retrieve raw points ordered by time.
        # Since raw_observations doesn't have session_id directly (it has camera_id and bbox),
        # we can reconstruct paths by spatial proximity or track tracking logs.
        # For simplicity, we can fetch all points sorted by time as a stream.
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT bbox_x1, bbox_y1, bbox_x2, bbox_y2 FROM raw_observations
            ORDER BY timestamp DESC LIMIT 100
        """)
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            return []
            
        path = []
        for r in rows:
            cx = (r[0] + r[2]) / 2.0
            cy = r[3]
            path.append((int(cx), int(cy)))
            
        return [path]
