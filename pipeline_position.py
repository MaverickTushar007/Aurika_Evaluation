from ingestion.frame_sampler import stream_frames
from ultralytics import YOLO
from tracking.position_tracker import PositionTracker
import cv2
import sqlite3
import os
import json
import numpy as np
from collections import deque
from datetime import datetime, timezone, timedelta

# Rich Dashboard imports
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.table import Table

# Architecture imports
from restaurant_analytics.staff_identifier import MultiModalStaffIdentifier, UniformColorIdentifier, BadgeDetector
from restaurant_analytics.zone_mapper import ZoneMapper
from restaurant_analytics.visit_manager import VisitManager
from restaurant_analytics.metrics_engine import MetricsEngine
from restaurant_analytics.operational_state_engine import OperationalStateEngine
from restaurant_analytics.operational_intelligence import OperationalIntelligenceLayer
from restaurant_analytics.report_generator import ExecutiveReportGenerator

detector = YOLO('yolo_staff_customer.pt')
CONF_THRESHOLD = 0.25
VIDEO_START = datetime.now(timezone.utc)

def video_ts_to_iso(ts):
    return (VIDEO_START + timedelta(seconds=ts)).isoformat()

def load_zones(config_path="configs/zones.json"):
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    default_zones = {
        "Entrance": [(0, 0), (200, 0), (200, 1080), (0, 1080)],
        "Reception": [(200, 180), (482, 180), (482, 360), (200, 360)],
        "Waiting Area": [(482, 0), (800, 0), (800, 400), (482, 400)],
        "Dining": [(800, 0), (1920, 0), (1920, 1080), (800, 1080)],
        "Kitchen": [(200, 360), (482, 360), (482, 1080), (200, 1080)],
        "Exit": [(0, 1000), (200, 1000), (200, 1080), (0, 1080)],
        "Staff Only": [(482, 800), (800, 800), (800, 1080), (482, 1080)]
    }
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(default_zones, f, indent=4)
    return default_zones

DEFAULT_ZONES = load_zones()

def in_service_zone(centroid):
    x, y = centroid
    return 360 <= x <= 482 and 180 <= y <= 360

db_dir = os.path.join(os.path.dirname(__file__), 'db')
os.makedirs(db_dir, exist_ok=True)
db_path = os.path.join(db_dir, 'customer_intel.db')
DB = sqlite3.connect(db_path, check_same_thread=False)

for _tbl in ("business_events", "staff_resolutions", "temporal_sessions", "raw_observations", "system_diagnostics"):
    DB.execute(f"DELETE FROM {_tbl} WHERE 1=1")
DB.commit()

def log_session_start(session_id: str, camera_id: str, start_ts: float):
    DB.execute("INSERT OR IGNORE INTO temporal_sessions (session_id, camera_id, start_time) VALUES (?,?,?)", (session_id, camera_id, video_ts_to_iso(start_ts)))
    DB.commit()

def log_session_end(session_id: str, entry_ts: float, exit_ts: float, served_tokens: set, service_times: dict, is_staff: int):
    duration = exit_ts - entry_ts
    if duration > 2:
        DB.execute("UPDATE temporal_sessions SET end_time=?, duration_seconds=? WHERE session_id=?", (video_ts_to_iso(exit_ts), duration, session_id))
        DB.commit()

VIDEOS = [('Dark_lighting_test .mp4', 'cam_dark')]

color_identifiers = [
    UniformColorIdentifier(lower_hsv=(0, 120, 100), upper_hsv=(10, 255, 255), pixel_ratio_threshold=0.25),
    UniformColorIdentifier(lower_hsv=(170, 120, 100), upper_hsv=(180, 255, 255), pixel_ratio_threshold=0.25),
    UniformColorIdentifier(lower_hsv=(100, 100, 60), upper_hsv=(125, 255, 200), pixel_ratio_threshold=0.25),
]
class MultiRangeUniformIdentifier:
    def __init__(self, identifiers):
        self.identifiers = identifiers
    def identify_staff(self, frame, bbox):
        best_label, best_conf = None, 0.0
        for ident in self.identifiers:
            label, conf = ident.identify_staff(frame, bbox)
            if label and conf > best_conf:
                best_label, best_conf = label, conf
        return best_label, best_conf

identifier = MultiModalStaffIdentifier(MultiRangeUniformIdentifier(color_identifiers), BadgeDetector())

# Dashboard Layout Builder
def build_layout(snapshot, decisions):
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main")
    )
    layout["main"].split_row(
        Layout(name="left"),
        Layout(name="right")
    )
    layout["left"].split_column(
        Layout(name="health", size=6),
        Layout(name="alerts")
    )
    layout["right"].split_column(
        Layout(name="ops", size=7),
        Layout(name="recs")
    )
    
    layout["header"].update(Panel(f"[bold cyan]AURIKA EXECUTIVE DASHBOARD[/] | Status: [bold]{snapshot.system_status}[/] | Confidence: {snapshot.overall_confidence*100:.1f}% | Time: {snapshot.timestamp.strftime('%H:%M:%S')}"))
    layout["health"].update(Panel(f"Health Score: [bold green]{snapshot.health_score:.1f}/100[/]\nActive Staff: {snapshot.active_staff}\nStaff Util: {snapshot.staff_utilization:.1f}%", title="Restaurant Health"))
    
    alerts_table = Table("Severity", "Alert", "Reason")
    for d in decisions:
        if d.severity in ["CRITICAL", "HIGH", "WARNING"]:
            color = "red" if d.severity == "CRITICAL" else ("orange3" if d.severity == "HIGH" else "yellow")
            alerts_table.add_row(f"[{color}]{d.severity}[/]", d.title, d.reason)
    layout["alerts"].update(Panel(alerts_table, title="Active System Alerts"))
    
    layout["ops"].update(Panel(f"Occupancy: [bold]{snapshot.current_occupancy}[/]\nGuests Waiting: [bold yellow]{snapshot.current_queue_length}[/]\nAvg Wait Time: {snapshot.average_wait_time/60:.1f} min\nActive Guests: {snapshot.active_guests}", title="Live Operations"))
    
    recs_table = Table("Priority", "Action", "Impact")
    for d in decisions[:4]:
        recs_table.add_row(str(d.priority), d.recommended_action, d.estimated_impact)
    layout["recs"].update(Panel(recs_table, title="Top Operational Recommendations"))
    
    return layout

console = Console()
centroid_history = {} # For executive video trails

for _vid, _cam in VIDEOS:
    print(f"\n--- Initializing Executive Demo for {_cam} ---")
    tracker = PositionTracker(max_distance=150, max_missing_frames=150)
    zone_mapper = ZoneMapper(DEFAULT_ZONES)
    visit_manager = VisitManager()
    metrics_engine = MetricsEngine(visit_manager=visit_manager)
    rose = OperationalStateEngine(metrics_engine=metrics_engine)
    intel = OperationalIntelligenceLayer(rules_path="configs/rules.json")
    
    served_tokens = set()
    token_is_staff = {}
    token_current_zone = {}
    service_times = {}
    token_class_votes = {}
    
    writer = None
    
    # Store last generated snapshot for final report
    final_snapshot = None
    final_decisions = None

    with Live(console=console, screen=True, auto_refresh=False) as live:
        for fid, ts, frame in stream_frames(_vid, fps_target=8):
            if writer is None:
                h, w = frame.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                writer = cv2.VideoWriter('output_executive_demo.mp4', fourcc, 8, (w, h))
                
            results = detector(frame, conf=CONF_THRESHOLD, verbose=False)
            bboxes, box_classes, box_confidences = [], [], []
            for box in results[0].boxes:
                bboxes.append(box.xyxy[0].tolist())
                box_classes.append(int(box.cls[0]))
                box_confidences.append(float(box.conf[0]))

            tracks = tracker.update(bboxes, fid, ts)
            dt_ts_current = VIDEO_START + timedelta(seconds=ts)

            for i, (token, bbox, is_new) in enumerate(tracks):
                cx, cy = int((bbox[0]+bbox[2])/2), int((bbox[1]+bbox[3])/2)
                centroid_history.setdefault(token, deque(maxlen=20)).append((cx, cy))
                
                cls, conf = box_classes[i], box_confidences[i]
                token_class_votes.setdefault(token, []).append(cls)
                is_staff = 1 if (token_class_votes[token].count(1) > token_class_votes[token].count(0)) else 0
                token_is_staff[token] = is_staff

                if is_new:
                    visit_manager.handle_track_start(token, dt_ts_current, role="staff" if is_staff else "guest", camera_id=_cam)
                    log_session_start(token, _cam, ts)

                visit = visit_manager.get_visit(token)
                if visit:
                    visit_manager.update_visit_role(token, "staff" if is_staff else "guest", dt_ts_current)
                    
                current_z = zone_mapper.get_zone_for_bbox(bbox)
                prev_z = token_current_zone.get(token)
                if current_z != prev_z:
                    visit_manager.update_visit_zone(token, current_z, dt_ts_current)
                    token_current_zone[token] = current_z
                    
            visit_manager.evaluate_temporal_states(dt_ts_current)
            
            for token, entry_ts, exit_ts in tracker.get_exited(fid):
                visit_manager.handle_track_end(token, VIDEO_START + timedelta(seconds=exit_ts))
                if token in token_current_zone:
                    token_current_zone.pop(token)
                if token in centroid_history:
                    centroid_history.pop(token)
                log_session_end(token, entry_ts, exit_ts, served_tokens, service_times, token_is_staff.get(token, 0))

            # Render Executive Overlay
            overlay = frame.copy()
            for token, bbox, is_new in tracks:
                x1, y1, x2, y2 = [int(v) for v in bbox]
                is_staff = token_is_staff.get(token, 0)
                
                visit = visit_manager.get_visit(token)
                state_str = visit.current_state if visit else "UNKNOWN"
                zone_str = visit.current_zone if visit else "None"
                duration = int((dt_ts_current - visit.entry_time).total_seconds()) if visit else 0
                
                color = (0, 255, 100) if is_staff else (0, 165, 255)
                role = "STAFF" if is_staff else "GUEST"
                
                # Draw rounded-like box corners
                cv2.rectangle(overlay, (x1, y1), (x1+15, y1+2), color, -1)
                cv2.rectangle(overlay, (x1, y1), (x1+2, y1+15), color, -1)
                cv2.rectangle(overlay, (x2-15, y2-2), (x2, y2), color, -1)
                cv2.rectangle(overlay, (x2-2, y2-15), (x2, y2), color, -1)

                # Draw centroid trail
                pts = list(centroid_history.get(token, []))
                for i in range(1, len(pts)):
                    thickness = int(np.sqrt(20 / float(i + 1)) * 2.5)
                    cv2.line(overlay, pts[i - 1], pts[i], color, thickness)
                
                # Draw semi-transparent background for label
                label_text = f"{role} | {zone_str} | {state_str} | {duration}s"
                (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
                cv2.rectangle(overlay, (x1, y1-25), (x1+tw+8, y1), (20,20,20), -1)
                cv2.putText(overlay, label_text, (x1+4, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

            # Apply transparency
            frame = cv2.addWeighted(overlay, 0.75, frame, 0.25, 0)
            
            # Update Intelligence Layer
            rose.refresh()
            snapshot = rose.get_current_snapshot()
            decisions = intel.evaluate_snapshot(snapshot)
            
            final_snapshot = snapshot
            final_decisions = decisions

            # Update Rich Dashboard
            live.update(build_layout(snapshot, decisions), refresh=True)
            
            if writer:
                writer.write(frame)

            # Display video frame (cv2 waitKey allows OpenCV to draw)
            cv2.imshow('Aurika Executive Vision', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    if writer:
        writer.release()
        
    for token, entry_ts, exit_ts in tracker.flush_all():
        visit_manager.handle_track_end(token, VIDEO_START + timedelta(seconds=exit_ts))
    DB.commit()
    
    # Final Generation
    if final_snapshot and final_decisions is not None:
        ExecutiveReportGenerator.generate(final_snapshot, final_decisions, "executive_report.html")

cv2.destroyAllWindows()
DB.close()
