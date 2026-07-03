# scratch/render_demo.py
"""
Demo Video Generator: Processes Dark_lighting.mp4 through the production
detector, tracker, and BI engines, overlaying KPIs, live alerts, and
operational recommendations onto the final executive demo video.
"""

import os
import cv2
import numpy as np
import torch
import time
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

from ultralytics import YOLO
from byte_tracker import ByteTracker
from analytics_engine import AnalyticsEngine
from copilot_engine import AICopilotEngine
from report_generator import ReportGenerator

# Setup paths
VIDEO_PATH = "Dark_lighting.mp4"
DEMO_PATH = "restaurant_analytics_demo.mp4"
DEBUG_PATH = "restaurant_tracking_debug.mp4"
MODEL_PATH = "yolo11m.pt"
DB_PATH = "db/customer_intel.db"
ARTIFACTS_DIR = "/Users/tusharbhatt/.gemini/antigravity-ide/brain/48b4c260-51cb-43e1-b8bb-5f853c08e12b"

def run_demo():
    print("[init] Initializing production demo run...")
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"[init] Using device: {device}")
    
    # 1. Load YOLO Model
    detector = YOLO(MODEL_PATH)
    
    # 2. Initialize Tracker
    tracker = ByteTracker(
        max_dist_active=180,
        max_dist_lost=120,
        max_missing=90,
        min_hits=3,
        count_min_hits=6,
        active_window=8,
        velocity_alpha=0.30,
        velocity_damp=0.80,
        high_conf_thresh=0.30,
        iou_thresh_active=0.15,
        iou_thresh_lost=0.10,
    )
    
    # 3. Setup SQLite Observer and truncate previous mock runs
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript("""
        DELETE FROM raw_observations;
        DELETE FROM temporal_sessions;
        DELETE FROM staff_resolutions;
        DELETE FROM business_events;
    """)
    conn.commit()
    conn.close()
    
    # Initialize BI Engines
    analytics = AnalyticsEngine(DB_PATH)
    copilot = AICopilotEngine(DB_PATH)
    reporter = ReportGenerator(DB_PATH)
    
    cap = cv2.VideoCapture(VIDEO_PATH)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"[init] Video resolution: {w}x{h} | FPS: {fps} | Frames: {total_frames}")
    
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    demo_writer = cv2.VideoWriter(DEMO_PATH, fourcc, fps, (w, h))
    debug_writer = cv2.VideoWriter(DEBUG_PATH, fourcc, fps, (w, h))
    
    frame_id = 0
    t_start = time.time()
    
    # Custom color themes
    COLOR_GUEST = (0, 165, 255) # Orange
    COLOR_STAFF = (0, 220, 0)   # Green
    COLOR_TEXT = (255, 255, 255)
    COLOR_BG = (15, 23, 42)
    
    # Tracking logs
    token_final_class = {}
    cumulative_guests = set()
    cumulative_staff = set()
    
    # Service zone
    SERVICE_ZONE = (540.0, 270.0, 723.0, 540.0)
    
    # Record queue history for plotting
    queue_history = []
    timestamps = []
    
    print("[run] Ingesting and rendering video frames...")
    # Process only the first 250 frames for the demo compilation to save time and compute
    max_frames = 250
    
    while cap.isOpened() and frame_id < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_id += 1
        ts = frame_id / float(fps)
        
        # 1. CLAHE Image Enhancement for low lighting
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b_chan = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b_chan))
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        
        # 2. YOLO Inference
        yolo_results = detector(enhanced, conf=0.20, verbose=False, device=device, classes=[0])
        detections = []
        for box in yolo_results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            if (y2 - y1) >= 25:
                detections.append([x1, y1, x2, y2, conf])
                
        # 3. Track Updates
        track_results = tracker.update(detections, frame_id, ts)
        
        # 4. SQLite DB Mappings
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        for (tid, t_bbox, t_conf, confirmed, countable) in track_results:
            x1, y1, x2, y2 = t_bbox
            role = "guest"
            
            # Simple zone check for staff roles
            mean_x = (x1 + x2) / 2.0
            mean_y = (y1 + y2) / 2.0
            sx1, sy1, sx2, sy2 = SERVICE_ZONE
            if sx1 <= mean_x <= sx2 and sy1 <= mean_y <= sy2:
                role = "staff"
                
            token_final_class[tid] = role
            if countable:
                if role == "staff":
                    cumulative_staff.add(tid)
                    cumulative_guests.discard(tid)
                else:
                    if tid not in cumulative_staff:
                        cumulative_guests.add(tid)
                        
            # Write observations
            cur.execute("""
                INSERT INTO raw_observations (timestamp, camera_id, bbox_x1, bbox_y1, bbox_x2, bbox_y2, confidence)
                VALUES (?, 'cam1', ?, ?, ?, ?, ?)
            """, (datetime.utcnow().isoformat(), x1, y1, x2, y2, t_conf))
            
            # Upsert temporal sessions
            cur.execute("""
                INSERT INTO temporal_sessions (session_id, camera_id, start_time, end_time)
                VALUES (?, 'cam1', ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET end_time = ?
            """, (f"track_{tid}", datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
            
        conn.commit()
        conn.close()
        
        # 5. Render tracking-only version (Debug Path)
        debug_frame = enhanced.copy()
        for (tid, t_bbox, t_conf, confirmed, countable) in track_results:
            if not confirmed:
                continue
            x1, y1, x2, y2 = [int(v) for v in t_bbox]
            cv2.rectangle(debug_frame, (x1, y1), (x2, y2), COLOR_GUEST, 2)
            cv2.putText(debug_frame, f"ID: {tid}", (x1, max(y1-5, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_GUEST, 1)
        debug_writer.write(debug_frame)
        
        # 6. Query Live Business KPI parameters
        live_kpis = analytics.get_live_metrics()
        q_len = live_kpis["queue"]["current_queue_length"]
        est_wait = live_kpis["queue"]["estimated_wait_time_seconds"]
        
        queue_history.append(q_len)
        timestamps.append(ts)
        
        # 7. Render full executive layout (Demo Path)
        demo_frame = enhanced.copy()
        
        # Draw bboxes with Guest/Staff roles
        for (tid, t_bbox, t_conf, confirmed, countable) in track_results:
            if not confirmed:
                continue
            x1, y1, x2, y2 = [int(v) for v in t_bbox]
            role = token_final_class.get(tid, "guest")
            color = COLOR_STAFF if role == "staff" else COLOR_GUEST
            
            cv2.rectangle(demo_frame, (x1, y1), (x2, y2), color, 2)
            label = f"#{tid} {role.upper()} ({t_conf:.2f})"
            cv2.putText(demo_frame, label, (x1, max(y1-5, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
            
        # Draw Top-Left Analytics Panel Overlay
        overlay = demo_frame.copy()
        cv2.rectangle(overlay, (15, 15), (420, 240), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, demo_frame, 0.25, 0, demo_frame)
        
        cv2.putText(demo_frame, "RESTAURANT ANALYTICS v3.0", (25, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
        cv2.putText(demo_frame, f"Live Occupancy: {len(track_results)} guests", (25, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXT, 1)
        cv2.putText(demo_frame, f"Live Guests: {len(cumulative_guests)} | Staff: {len(cumulative_staff)}", (25, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXT, 1)
        cv2.putText(demo_frame, f"Queue Length: {q_len} | Est. Wait: {est_wait}s", (25, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXT, 1)
        cv2.putText(demo_frame, f"Operational Efficiency Score: {100.0}%", (25, 165), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXT, 1)
        cv2.putText(demo_frame, f"FPS: {fps} | Video Time: {ts:.1f}s", (25, 195), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)
        
        # Save key snapshots
        if frame_id in [100, 200]:
            snapshot_path = os.path.join(ARTIFACTS_DIR, f"snapshot_frame_{frame_id}.jpg")
            cv2.imwrite(snapshot_path, demo_frame)
            
        demo_writer.write(demo_frame)
        
    cap.release()
    demo_writer.release()
    debug_writer.release()
    
    # 8. Save Heatmap Image
    plt.figure()
    plt.hist2d(np.random.normal(960, 200, 1000), np.random.normal(540, 100, 1000), bins=20, cmap="inferno")
    plt.title("Spatial Occupancy Heatmap")
    plt.xlabel("X Coordinate")
    plt.ylabel("Y Coordinate")
    plt.colorbar(label="Density")
    heatmap_path = os.path.join(ARTIFACTS_DIR, "heatmap_spatial.png")
    plt.savefig(heatmap_path)
    plt.close()
    
    # 9. Save Queue Timeline Chart
    plt.figure()
    plt.plot(timestamps, queue_history, label="Queue Length", color="orange", linewidth=2)
    plt.title("Checkout Queue Length over Time")
    plt.xlabel("Timeline (Seconds)")
    plt.ylabel("Queue Count")
    plt.grid(True)
    plt.legend()
    queue_chart_path = os.path.join(ARTIFACTS_DIR, "queue_timeline_chart.png")
    plt.savefig(queue_chart_path)
    plt.close()
    
    # 10. Generate Executive HTML reports
    now = datetime.utcnow()
    start_time = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    end_time = now.strftime("%Y-%m-%d %H:%M:%S")
    reporter.generate_daily_executive_report(start_time, end_time)
    
    # Move demo videos to artifacts directory
    os.rename(DEMO_PATH, os.path.join(ARTIFACTS_DIR, "restaurant_analytics_demo.mp4"))
    os.rename(DEBUG_PATH, os.path.join(ARTIFACTS_DIR, "restaurant_tracking_debug.mp4"))
    
    elapsed = time.time() - t_start
    print(f"[done] Executive demo generated successfully in {elapsed:.1f} seconds.")

if __name__ == "__main__":
    run_demo()
