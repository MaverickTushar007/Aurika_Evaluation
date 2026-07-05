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
        "Reception": [(200, 0), (482, 0), (482, 360), (200, 360)],
        "Waiting Area": [(482, 0), (800, 0), (800, 800), (482, 800)],
        "Dining": [(800, 0), (1920, 0), (1920, 1080), (800, 1080)],
        "Kitchen": [(200, 360), (482, 360), (482, 1080), (200, 1080)],
        "Exit": [(0, 1000), (200, 1000), (200, 1080), (0, 1080)],
        "Staff Only": [(482, 800), (800, 800), (800, 1080), (482, 1080)],
        "Table 101": [(1000, 300), (1400, 300), (1400, 700), (1000, 700)]
    }
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(default_zones, f, indent=4)
    return default_zones

DEFAULT_ZONES = load_zones()

def in_service_zone(centroid):
    x, y = centroid
    return 360 <= x <= 482 and 180 <= y <= 360

def init_db(db_path):
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=60.0)
    # Ensure legacy tables exist
    conn.execute('''
        CREATE TABLE IF NOT EXISTS persons (
            token_id TEXT PRIMARY KEY,
            first_seen TEXT,
            last_seen TEXT,
            camera_id TEXT,
            abandoned INTEGER DEFAULT 0,
            is_staff INTEGER DEFAULT 0,
            staff_id TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS wait_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_id TEXT,
            entry_time TEXT,
            exit_time TEXT,
            wait_seconds REAL,
            time_to_service REAL,
            abandoned INTEGER DEFAULT 0,
            date TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS temporal_sessions (
            session_id TEXT PRIMARY KEY,
            camera_id TEXT,
            start_time TEXT,
            end_time TEXT,
            duration_seconds REAL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS business_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            event_type TEXT,
            timestamp TEXT,
            value REAL,
            zone_id TEXT
        )
    ''')
    conn.commit()
    
    for _tbl in ("business_events", "staff_resolutions", "temporal_sessions", "raw_observations", "system_diagnostics", "persons", "wait_metrics"):
        try:
            conn.execute(f"DELETE FROM {_tbl} WHERE 1=1")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    return conn

DB = None

from restaurant_analytics.journey_manager import JourneyManager
import glob

def log_session_start(session_id: str, camera_id: str, start_ts: float):
    DB.execute("INSERT OR IGNORE INTO temporal_sessions (session_id, camera_id, start_time) VALUES (?,?,?)", (session_id, camera_id, video_ts_to_iso(start_ts)))
    DB.execute("INSERT OR IGNORE INTO persons (token_id, first_seen, camera_id) VALUES (?,?,?)", (session_id, video_ts_to_iso(start_ts), camera_id))
    DB.commit()

def log_session_end(session_id: str, entry_ts: float, exit_ts: float, served_tokens: set, service_times: dict, is_staff: int):
    duration = exit_ts - entry_ts
    if duration > 2:
        DB.execute("UPDATE temporal_sessions SET end_time=?, duration_seconds=? WHERE session_id=?", (video_ts_to_iso(exit_ts), duration, session_id))
        DB.execute("UPDATE persons SET last_seen=?, is_staff=? WHERE token_id=?", (video_ts_to_iso(exit_ts), is_staff, session_id))
        date = VIDEO_START.strftime('%Y-%m-%d')
        DB.execute(
            "INSERT INTO wait_metrics (token_id, entry_time, exit_time, wait_seconds, abandoned, date) VALUES (?,?,?,?,?,?)",
            (session_id, video_ts_to_iso(entry_ts), video_ts_to_iso(exit_ts), round(duration, 2), 0, date)
        )
        DB.commit()

def answer_ceo_questions(db_path, run_dir, video_path, total_frames, avg_visible, max_visible, merge_count, split_count):
    # Determine video duration
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    cap.release()
    video_duration = total_frames / fps
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Query Database counts
    cursor.execute("SELECT COUNT(*) FROM journeys")
    entered_journeys = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM journeys WHERE status='exited'")
    exited_journeys = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(distinct journey_id) FROM journeys WHERE seated_time IS NOT NULL")
    seated_journeys = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(waiting_duration) FROM journeys WHERE waiting_duration > 0")
    avg_wait = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT AVG(dining_duration) FROM journeys WHERE dining_duration > 0")
    avg_dining = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT COUNT(*) FROM journeys WHERE status='active'")
    current_occupancy = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM journeys WHERE current_zone='Waiting Area'")
    queue_length = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(distinct token_id) FROM wait_metrics")
    unique_trackers = cursor.fetchone()[0]
    
    print("\n===========================================================")
    print(f"ISOLATED BUSINESS METRICS & KPI AUDIT FOR {os.path.basename(video_path)}")
    print("===========================================================")
    print(f"- Video File: {video_path}")
    print(f"- Video Duration: {video_duration:.2f} seconds")
    print(f"- Total Frames Processed: {total_frames}")
    print(f"- Average Visible People: {avg_visible:.2f}")
    print(f"- Maximum Visible People: {max_visible}")
    print(f"- Unique Tracker IDs (Detections): {unique_trackers}")
    print(f"- Unique Customer Journeys: {entered_journeys}")
    print(f"- Journey Merge Count: {merge_count}")
    print(f"- Journey Split Count: {split_count}")
    print(f"- Total Entered: {entered_journeys}")
    print(f"- Total Exited: {exited_journeys}")
    print(f"- Total Seated: {seated_journeys}")
    print(f"- Average Waiting Time: {avg_wait:.2f} seconds")
    print(f"- Average Dining Time: {avg_dining:.2f} seconds")
    print(f"- Current Occupancy: {current_occupancy}")
    print(f"- Queue Length: {queue_length}")
    print("-----------------------------------------------------------")
    
    # Step 3 & 4: Sanity assertions
    print("[SANITY ASSERTIONS]")
    if avg_wait > video_duration:
        print("WARNING: Average waiting time exceeds video duration!")
    else:
        print("✔ Average waiting time is within physical bounds.")
        
    if avg_dining > video_duration:
        print("WARNING: Average dining time exceeds video duration!")
    else:
        print("✔ Average dining time is within physical bounds.")
        
    if current_occupancy > max_visible:
        print(f"WARNING: Current occupancy ({current_occupancy}) exceeds maximum visible people ({max_visible})!")
    else:
        print("✔ Current occupancy is within maximum simultaneous visible people bounds.")
        
    if queue_length > max_visible:
        print(f"WARNING: Queue length ({queue_length}) exceeds maximum visible people ({max_visible})!")
    else:
        print("✔ Queue length is within physical bounds.")
        
    if entered_journeys > unique_trackers * 1.5:
        print(f"WARNING: Journey count ({entered_journeys}) exceeds unique tracker count ({unique_trackers}) by more than 1.5x (high fragmentation warning)!")
        
    cursor.execute("SELECT COUNT(*) FROM business_events WHERE event_type='waiting'")
    waiting_events = cursor.fetchone()[0]
    if avg_wait == 0 and waiting_events > 0:
        print("WARNING: Average wait time is 0 but waiting events exist in DB!")
        
    if current_occupancy > max_visible:
        print("WARNING: Active occupancy exceeds maximum visible people count!")
        
    # Step 10: Final consistency checks
    # Entered ≈ Exited + Current Occupancy
    delta = abs(entered_journeys - (exited_journeys + current_occupancy))
    if delta > 10:
        print(f"WARNING: Conservation of flow discrepancy! Entered ({entered_journeys}) != Exited ({exited_journeys}) + Current ({current_occupancy}) (delta={delta})")
    else:
        print(f"✔ Conservation of Flow: Entered ({entered_journeys}) ≈ Exited ({exited_journeys}) + Current Occupancy ({current_occupancy}) (delta={delta}).")

    # Check for negative wait/dining times or zero duration visits
    cursor.execute("SELECT COUNT(*) FROM journeys WHERE waiting_duration < 0 OR dining_duration < 0")
    negatives = cursor.fetchone()[0]
    if negatives > 0:
        print(f"WARNING: Found {negatives} journeys with negative durations!")
    else:
        print("✔ No negative durations found in journeys database.")
        
    cursor.execute("SELECT COUNT(*) FROM server_visits WHERE duration <= 0")
    zero_visits = cursor.fetchone()[0]
    if zero_visits > 0:
        print(f"WARNING: Found {zero_visits} zero-length server visits!")
    else:
        print("✔ No zero-length server visits found.")
        
    print("-----------------------------------------------------------")
    # Step 5: Journey validation list
    print("[DETAILED JOURNEY TRACKING AUDIT]")
    cursor.execute("SELECT journey_id, entry_time, exit_time, current_zone, waiting_duration, dining_duration, seated_time, status, state, confidence FROM journeys")
    journeys_list = cursor.fetchall()
    
    rejected_count = 0
    for row in journeys_list:
        j_id, entry_t, exit_t, zone, wait_dur, dining_dur, seat_t, status, state, confidence = row
        # Reject journeys missing Entered and Exited unless still active
        is_active = (status == "active" or status == "lost")
        has_entered = entry_t is not None
        has_exited = (exit_t is not None or state == "EXITED" or status == "exited")
        
        # Calculate duration
        dur = 0.0
        if entry_t:
            d_start = datetime.fromisoformat(entry_t)
            d_end = datetime.fromisoformat(exit_t) if exit_t else datetime.now(timezone.utc)
            dur = (d_end - d_start).total_seconds()
            
        is_valid = True
        reason = ""
        if not is_active and not (has_entered and has_exited):
            is_valid = False
            reason = "Missing Entered or Exited timestamp on closed journey"
            rejected_count += 1
            
        valid_status = "✔ VALID" if is_valid else f"❌ REJECTED ({reason})"
        print(f"Journey: {j_id} | State: {state} | Wait: {wait_dur:.1f}s | Dining: {dining_dur:.1f}s | Dur: {dur:.1f}s | Confidence: {confidence:.2f} | Status: {valid_status}")
        
    if rejected_count > 0:
        print(f"WARNING: Rejected {rejected_count} invalid journeys missing boundary states!")
    else:
        print("✔ All finalized customer journeys passed boundary checks.")
    print("===========================================================\n")
    conn.close()

video_paths = sorted(
    glob.glob("datasets/*.mp4") + 
    glob.glob("datasets/*.mkv") + 
    glob.glob("datasets/*.avi")
)
VIDEOS = []
for p in video_paths:
    basename = os.path.basename(p)
    if "test_video" in basename:
        cam = "cam_entrance"
    elif "seated" in basename:
        cam = "cam_dining"
    elif "Dark_lighting" in basename:
        cam = "cam_patio"
    else:
        cam = "cam_" + os.path.splitext(basename)[0].lower().replace(" ", "_")
    VIDEOS.append((p, cam))

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
    layout["health"].update(Panel(f"Health Score: [bold green]{snapshot.health_score:.1f}/100[/]\nActive Staff: {snapshot.active_staff}\nStaff Util: {snapshot.overall_staff_utilization:.1f}%", title="Restaurant Health"))
    
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
    video_name = os.path.splitext(os.path.basename(_vid))[0]
    run_dir = f"runs/{video_name}"
    os.makedirs(run_dir, exist_ok=True)
    db_path = f"{run_dir}/customer_intel.db"
    
    DB = init_db(db_path)
    
    print(f"\n--- Initializing Executive Demo for {_cam} (Run Directory: {run_dir}) ---")
    tracker = PositionTracker(max_distance=100, max_missing_frames=200)
    zone_mapper = ZoneMapper(DEFAULT_ZONES)
    visit_manager = VisitManager()
    metrics_engine = MetricsEngine(visit_manager=visit_manager)
    rose = OperationalStateEngine(metrics_engine=metrics_engine)
    intel = OperationalIntelligenceLayer(rules_path="configs/rules.json")
    journey_manager = JourneyManager(db_path=db_path)
    staff_table_durations = {}
    
    served_tokens = set()
    token_is_staff = {}
    token_current_zone = {}
    service_times = {}
    token_class_votes = {}
    
    writer = None
    frame_people_counts = []
    
    # Store last generated snapshot for final report
    final_snapshot = None
    final_decisions = None

    with Live(console=console, screen=True, auto_refresh=False) as live:
        for fid, ts, frame in stream_frames(_vid, fps_target=8):
            if writer is None:
                h, w = frame.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                # Extract base filename to avoid writing over previous output
                out_name = f"{run_dir}/output.mp4"
                writer = cv2.VideoWriter(out_name, fourcc, 8, (w, h))
                
            results = detector(frame, conf=CONF_THRESHOLD, verbose=False)
            bboxes, box_classes, box_confidences = [], [], []
            for box in results[0].boxes:
                bboxes.append(box.xyxy[0].tolist())
                box_classes.append(int(box.cls[0]))
                box_confidences.append(float(box.conf[0]))

            tracks = tracker.update(bboxes, fid, ts)
            dt_ts_current = VIDEO_START + timedelta(seconds=ts)
            frame_people_counts.append(len(tracks))

            # Track staff locations for server visits
            staff_locations = {}
            for i, (token, bbox, is_new) in enumerate(tracks):
                cx, cy = int((bbox[0]+bbox[2])/2), int((bbox[1]+bbox[3])/2)
                centroid_history.setdefault(token, deque(maxlen=10)).append((cx, cy))
                
                cls, conf = box_classes[i], box_confidences[i]
                token_class_votes.setdefault(token, []).append(cls)
                is_staff = 1 if (token_class_votes[token].count(1) > token_class_votes[token].count(0)) else 0
                token_is_staff[token] = is_staff

                current_z = zone_mapper.get_zone_for_bbox(bbox)
                if is_new:
                    visit_manager.handle_track_start(token, dt_ts_current, role="staff" if is_staff else "guest", camera_id=_cam, centroid=(cx, cy))
                    log_session_start(token, _cam, ts)

                visit = visit_manager.get_visit(token)
                if visit:
                    visit_manager.update_visit_role(token, "staff" if is_staff else "guest", dt_ts_current)
                    
                prev_z = token_current_zone.get(token)
                if current_z != prev_z:
                    visit_manager.update_visit_zone(token, current_z, dt_ts_current, centroid=(cx, cy))
                    token_current_zone[token] = current_z

                # Update JourneyManager (Step 2, 3, 4, 5, 6)
                journey_manager.handle_track_update(
                    track_id=token, 
                    zone=current_z or "UNKNOWN_ZONE", 
                    centroid=(cx, cy), 
                    is_new=is_new, 
                    is_staff=(is_staff == 1), 
                    timestamp=dt_ts_current,
                    frame_id=fid,
                    frame_img=frame,
                    bbox=bbox,
                    run_dir=run_dir
                )
                if is_staff:
                    staff_locations[token] = (cx, cy)

            # Server Visit Detection (Step 7)
            for staff_token, (scx, scy) in staff_locations.items():
                staff_zone = zone_mapper.get_zone_for_bbox([scx-10, scy-10, scx+10, scy+10])
                if staff_zone and "table" in staff_zone.lower():
                    key = (staff_token, staff_zone)
                    staff_table_durations.setdefault(key, []).append(dt_ts_current)
                    times = staff_table_durations[key]
                    if len(times) >= 16: # ~2.0 seconds
                        dur = (times[-1] - times[0]).total_seconds()
                        if int(dur) % 10 == 0:
                            journey_manager.log_server_visit(staff_zone, staff_token, times[0], dur)
                else:
                    for key in list(staff_table_durations.keys()):
                        if key[0] == staff_token:
                            times = staff_table_durations.pop(key)
                            dur = (times[-1] - times[0]).total_seconds()
                            if dur >= 2.0:
                                journey_manager.log_server_visit(key[1], staff_token, times[0], dur)
                                
            visit_manager.evaluate_temporal_states(dt_ts_current)
            journey_manager.sweep_lost_journeys(dt_ts_current, frame_id=fid)
            
            for token, entry_ts, exit_ts in tracker.get_exited(fid):
                visit_manager.handle_track_end(token, VIDEO_START + timedelta(seconds=exit_ts))
                journey_manager.handle_track_lost(token, VIDEO_START + timedelta(seconds=exit_ts))
                if token in token_current_zone:
                    token_current_zone.pop(token)
                if token in centroid_history:
                    centroid_history.pop(token)
                log_session_end(token, entry_ts, exit_ts, served_tokens, service_times, token_is_staff.get(token, 0))

            # Render Executive Overlay
            overlay = frame.copy()
            
            # Draw polygon debug overlay (Priority 5)
            for zone_name, poly_pts in zone_mapper.zones.items():
                pts_arr = np.array(poly_pts, np.int32).reshape((-1, 1, 2))
                cv2.polylines(overlay, [pts_arr], isClosed=True, color=(100, 100, 100), thickness=1)
                # Label the zone name near the first vertex, clamped within image
                cv2.putText(overlay, zone_name, (max(5, poly_pts[0][0]), max(15, poly_pts[0][1])), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (140, 140, 140), 1)

            drawn_label_ys = [] # To prevent labels overlapping vertically

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
                    thickness = int(np.sqrt(10 / float(i + 1)) * 2.0)
                    cv2.line(overlay, pts[i - 1], pts[i], color, thickness)
                
                # Draw text label with clutter avoidance, contrast, clamping, size reduction
                label_text = f"{role} | {zone_str} | {state_str} | {duration}s"
                font_scale = 0.35
                (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
                
                # Position label above the box y1, clamp inside frame
                lx = max(0, min(x1, w - tw - 10))
                ly = y1 - 10
                
                # Anti-overlap vertical placement packing
                while any(abs(ly - dy) < 18 for dy in drawn_label_ys):
                    ly -= 18
                ly = max(th + 5, min(ly, h - 5))
                drawn_label_ys.append(ly)

                cv2.rectangle(overlay, (lx, ly - th - 6), (lx + tw + 8, ly + 2), (0, 0, 0), -1)
                cv2.putText(overlay, label_text, (lx + 4, ly - 2), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 1)

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

            # Display video frame (cv2 waitKey allows OpenCV to draw if GUI is available)
            try:
                cv2.imshow('Aurika Executive Vision', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except Exception:
                pass

    if writer:
        writer.release()
        writer = None
        
    for token, entry_ts, exit_ts in tracker.flush_all():
        visit_manager.handle_track_end(token, VIDEO_START + timedelta(seconds=exit_ts))
    DB.commit()
    
    journey_manager.sweep_lost_journeys(dt_ts_current, force_all=True, frame_id=fid)
    DB.close()
    
    # Write journeys_explainable.json (Step 7)
    journeys_data = []
    for j in journey_manager.journeys:
        journeys_data.append({
            "journey_id": j.journey_id,
            "tracker_ids_merged": j.active_tracker_ids,
            "entry_time": j.entry_time.isoformat() if j.entry_time else None,
            "exit_time": j.exit_time.isoformat() if j.exit_time else None,
            "entry_gate": j.entry_gate,
            "current_zone": j.current_zone,
            "zone_history": j.zone_history,
            "entry_frame": j.entry_frame,
            "reception_frame": j.reception_frame,
            "waiting_start_frame": j.waiting_start_frame,
            "waiting_end_frame": j.waiting_end_frame,
            "seated_frame": j.seated_frame,
            "exit_frame": j.exit_frame,
            "waiting_duration": j.waiting_duration,
            "dining_duration": j.dining_duration,
            "table_id": j.table_id,
            "seated_time": j.seated_time.isoformat() if j.seated_time else None,
            "server_visits": j.server_visits,
            "confidence": j.confidence,
            "status": j.status,
            "state": j.state,
            "timeline": j.timeline
        })
    with open(f"{run_dir}/journeys_explainable.json", "w") as f:
        json.dump(journeys_data, f, indent=4)
    with open(f"{run_dir}/journeys.json", "w") as f:
        json.dump(journeys_data, f, indent=4)

    # Write kpis_evidence.json (Step 2 & 5)
    kpis_evidence = {}
    
    # 1. Customers Entered
    entered_support = []
    for j in journey_manager.journeys:
        if j.entry_time:
            entered_support.append({
                "journey": j.journey_id,
                "frame": j.entry_frame or 0,
                "timestamp": j.entry_time.isoformat(),
                "camera": _cam,
                "reason": "Crossed Entry Gate / Entrance"
            })
    kpis_evidence["customers_entered"] = {
        "metric": "customers_entered",
        "value": len(entered_support),
        "support": entered_support
    }
    
    # 2. Customers Seated
    seated_support = []
    for j in journey_manager.journeys:
        if j.seated_time:
            seated_support.append({
                "journey": j.journey_id,
                "frame": j.seated_frame or 0,
                "timestamp": j.seated_time.isoformat(),
                "camera": _cam,
                "reason": "Entered Seated Table Polygon"
            })
    kpis_evidence["customers_seated"] = {
        "metric": "customers_seated",
        "value": len(seated_support),
        "support": seated_support
    }
    
    # 3. Customers Exited
    exited_support = []
    for j in journey_manager.journeys:
        if j.status == "exited" or j.exit_time:
            exited_support.append({
                "journey": j.journey_id,
                "frame": j.exit_frame or 0,
                "timestamp": j.exit_time.isoformat() if j.exit_time else j.last_active_time.isoformat(),
                "camera": _cam,
                "reason": "Crossed Exit gate or went offline in exit area"
            })
    kpis_evidence["customers_exited"] = {
        "metric": "customers_exited",
        "value": len(exited_support),
        "support": exited_support
    }
    
    # 4. Average Wait Time
    wait_support = []
    for j in journey_manager.journeys:
        if j.waiting_duration > 0:
            wait_support.append({
                "journey": j.journey_id,
                "waiting_duration_seconds": j.waiting_duration,
                "waiting_start": j.waiting_started.isoformat() if j.waiting_started else None
            })
    avg_wait = sum(x["waiting_duration_seconds"] for x in wait_support)/len(wait_support) if wait_support else 0.0
    kpis_evidence["average_wait_time"] = {
        "metric": "average_wait_time",
        "value": avg_wait,
        "support": wait_support
    }
    
    # 5. Average Dining Time
    dining_support = []
    for j in journey_manager.journeys:
        if j.dining_duration > 0:
            dining_support.append({
                "journey": j.journey_id,
                "dining_duration_seconds": j.dining_duration,
                "seated_time": j.seated_time.isoformat() if j.seated_time else None
            })
    avg_dining = sum(x["dining_duration_seconds"] for x in dining_support)/len(dining_support) if dining_support else 0.0
    kpis_evidence["average_dining_time"] = {
        "metric": "average_dining_time",
        "value": avg_dining,
        "support": dining_support
    }
    
    with open(f"{run_dir}/kpis_evidence.json", "w") as f:
        json.dump(kpis_evidence, f, indent=4)
        
    # Output CEO answers from JourneyManager (Step 8)
    answer_ceo_questions(
        db_path=db_path,
        run_dir=run_dir,
        video_path=_vid,
        total_frames=len(frame_people_counts),
        avg_visible=sum(frame_people_counts)/len(frame_people_counts) if frame_people_counts else 0.0,
        max_visible=max(frame_people_counts) if frame_people_counts else 0,
        merge_count=journey_manager.merge_count,
        split_count=journey_manager.split_count
    )
    
    # Final Generation
    if final_snapshot and final_decisions is not None:
        ExecutiveReportGenerator.generate(final_snapshot, final_decisions, f"{run_dir}/executive_report.html")

try:
    cv2.destroyAllWindows()
except Exception:
    pass
try:
    if DB:
        DB.close()
except Exception:
    pass
