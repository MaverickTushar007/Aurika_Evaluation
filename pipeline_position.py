from ingestion.frame_sampler import stream_frames
from ultralytics import YOLO
from tracking.position_tracker import PositionTracker
import cv2
import sqlite3
import os
import time
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
from restaurant_analytics.journey_manager import JourneyManager
from restaurant_analytics.event_rule_engine import EventRuleEngine
from restaurant_analytics.transition_validator import TransitionValidator

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
    for _tbl in ("business_events", "staff_resolutions", "temporal_sessions", "raw_observations", "system_diagnostics", "persons", "wait_metrics", "spatial_transitions", "validated_transitions", "journeys", "server_visits"):
        try:
            conn.execute(f"DROP TABLE IF EXISTS {_tbl}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    
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
            rule_id TEXT,
            camera TEXT,
            previous_zone TEXT,
            current_zone TEXT,
            journey_state TEXT,
            journey_id TEXT,
            tracker_id TEXT,
            timestamp TEXT,
            frame INTEGER,
            confidence REAL,
            transition_id TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS validated_transitions (
            transition_id TEXT PRIMARY KEY,
            journey_id TEXT,
            tracker_id TEXT,
            camera TEXT,
            previous_zone TEXT,
            current_zone TEXT,
            entry_frame INTEGER,
            exit_frame INTEGER,
            entry_timestamp TEXT,
            exit_timestamp TEXT,
            travel_time REAL,
            distance_pixels REAL,
            average_speed REAL,
            direction TEXT,
            tracking_confidence REAL,
            zone_confidence REAL,
            rule_confidence REAL,
            transition_confidence REAL,
            is_valid INTEGER DEFAULT 1
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS frame_occupancies (
            frame INTEGER,
            camera_id TEXT,
            occupancy INTEGER,
            active_journey_ids TEXT,
            PRIMARY KEY (frame, camera_id)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS frame_queues (
            frame INTEGER,
            camera_id TEXT,
            queue_length INTEGER,
            queue_members TEXT,
            PRIMARY KEY (frame, camera_id)
        )
    ''')
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
    
    is_dining_cam = ("seated" in db_path or "dining" in db_path) and "allowed" not in db_path
    if is_dining_cam:
        entered_journeys = 0
        exited_journeys = 0
    
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
        
    cursor.execute("SELECT COUNT(*) FROM business_events WHERE rule_id LIKE '%WAIT%' OR rule_id LIKE '%Queue%'")
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

video_paths = [
    "datasets/Dark_lighting.mp4"
]
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
def build_layout(snapshot, state_engine):
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
    
    # Header Panel
    layout["header"].update(Panel(f"[bold cyan]AURIKA RESTAURANT OPERATIONS INTELLIGENCE[/] | Status: [bold green]OPEN[/] | Time: {snapshot.timestamp.strftime('%H:%M:%S')}"))
    
    # Health Panel
    layout["health"].update(Panel(f"Health Score: [bold green]{snapshot.health_score:.1f}/100[/]\nStaff Visible: {state_engine.perf_profiles.get('staff_currently_visible', state_engine.perf_profiles.get('staff_visible', 0))}\nService Load: [bold yellow]{state_engine.perf_profiles.get('current_service_load', 'Normal')}[/]", title="Restaurant Health"))
    
    # Alerts Panel
    alerts_table = Table("Severity", "Alert Source", "Operational Impact")
    for a in state_engine.perf_profiles.get("alerts", []):
        sev = "HIGH" if "limit" in a["reason"].lower() or "critical" in a["reason"].lower() else "WARNING"
        color = "red" if sev == "HIGH" else "yellow"
        alerts_table.add_row(f"[{color}]{sev}[/]", "Operations", a["reason"])
    layout["alerts"].update(Panel(alerts_table, title="Restaurant Alerts"))
    
    # Occupancy & KPIs Panel
    avg_wait = state_engine.perf_profiles.get("kpis", {}).get("average_wait_time", 0.0)
    avg_dining = state_engine.perf_profiles.get("kpis", {}).get("average_dining_time", 0.0)
    entered = state_engine.perf_profiles.get("kpis", {}).get("customers_entered", 0)
    exited = state_engine.perf_profiles.get("kpis", {}).get("customers_exited", 0)
    seated = state_engine.perf_profiles.get("kpis", {}).get("customers_seated", 0)
    
    layout["ops"].update(Panel(
        f"Occupancy: [bold]{state_engine.perf_profiles.get('current_occupancy', 0)}[/] guests\n"
        f"Guests Seated: {seated} | Waiting: {state_engine.perf_profiles.get('current_waiting_customers', 0)} | Queue: {state_engine.perf_profiles.get('current_queue_length', 0)}\n"
        f"Total Entries: {entered} | Exits: {exited}\n"
        f"Average Dwell: Wait: {avg_wait:.1f}s | Dining: {avg_dining:.1f}s",
        title="Restaurant Occupancy & KPIs"
    ))
    
    # Timeline Panel
    timeline_table = Table("Time", "Event Description")
    timeline_events = state_engine.perf_profiles.get("timeline", [])[-4:] # Show last 4 events
    for t_evt in timeline_events:
        try:
            t_str = datetime.fromisoformat(t_evt["timestamp"]).strftime('%H:%M:%S')
        except Exception:
            t_str = t_evt["timestamp"]
        timeline_table.add_row(t_str, t_evt["message"])
    layout["recs"].update(Panel(timeline_table, title="Restaurant Timeline"))
    
    return layout

console = Console()
centroid_history = {} # For executive video trails

for _vid, _cam in VIDEOS:
    video_name = os.path.splitext(os.path.basename(_vid))[0]
    tracker_name = os.environ.get("OS_ACTIVE_TRACKER", "Centroid")
    run_dir = f"runs/{video_name}/{tracker_name}"
    os.makedirs(run_dir, exist_ok=True)
    db_path = f"{run_dir}/customer_intel.db"
    
    max_occ_seen = -1
    max_q_seen = -1
    peak_occ_img = None
    max_q_img = None
    peak_occ_frame_id = 0
    max_q_frame_id = 0
    saved_entries = set()
    
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass
    DB = init_db(db_path)
    
    print(f"\n--- Initializing Executive Demo for {_cam} (Run Directory: {run_dir}) ---")
    from tracking.position_tracker import PositionTracker, ByteTracker, OCSORTTracker, DeepSORTTracker, BoTSORTTracker, StrongSORTTracker
    if tracker_name == "ByteTrack":
        tracker = ByteTracker(max_missing_frames=200)
    elif tracker_name == "OC-SORT":
        tracker = OCSORTTracker(max_missing_frames=200)
    elif tracker_name == "DeepSORT":
        tracker = DeepSORTTracker(max_missing_frames=200)
    elif tracker_name == "BoT-SORT":
        tracker = BoTSORTTracker(max_missing_frames=200)
    elif tracker_name == "StrongSORT":
        tracker = StrongSORTTracker(max_missing_frames=200)
    else:
        tracker = PositionTracker(max_distance=100, max_missing_frames=200)
    cap_temp = cv2.VideoCapture(_vid)
    w_vid = int(cap_temp.get(cv2.CAP_PROP_FRAME_WIDTH))
    h_vid = int(cap_temp.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap_temp.get(cv2.CAP_PROP_FRAME_COUNT))
    cap_temp.release()
    if total_frames <= 0:
        total_frames = 999999

    if os.environ.get("OS_PERTURB_MODE") == "resized_polygons":
        scale = 1.0 + float(os.environ.get("OS_PERTURB_PROB", "0.1"))
        scaled_zones = {}
        for zone_name, pts in DEFAULT_ZONES.items():
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            scaled_pts = []
            for x, y in pts:
                nx = int(cx + (x - cx) * scale)
                ny = int(cy + (y - cy) * scale)
                scaled_pts.append([nx, ny])
            scaled_zones[zone_name] = scaled_pts
        zone_mapper = ZoneMapper(scaled_zones, frame_size=(w_vid, h_vid))
    else:
        zone_mapper = ZoneMapper(DEFAULT_ZONES, frame_size=(w_vid, h_vid))
    visit_manager = VisitManager()
    metrics_engine = MetricsEngine(visit_manager=visit_manager)
    rose = OperationalStateEngine(metrics_engine=metrics_engine)
    intel = OperationalIntelligenceLayer(rules_path="configs/rules.json")
    journey_manager = JourneyManager(db_path=db_path, camera_id=_cam, total_frames=total_frames)
    staff_table_durations = {}
    
    from restaurant_analytics.restaurant_state_engine import RestaurantStateEngine
    state_engine = RestaurantStateEngine(db_path=db_path, run_dir=run_dir)
    
    served_tokens = set()
    token_is_staff = {}
    token_current_zone = {}
    service_times = {}
    token_class_votes = {}
    
    writer = None
    frame_people_counts = []
    frame_stats = []
    event_log_rows = []
    prev_entered_count = 0
    prev_exited_count = 0
    prev_queue_size = 0
    prev_peak_occ = 0
    banner_text = None
    banner_color = (0, 255, 0)
    banner_timer = 0
    
    import random
    perturb_mode = os.environ.get("OS_PERTURB_MODE")
    perturb_prob = float(os.environ.get("OS_PERTURB_PROB", "0.0"))
    fps_target_val = int(os.environ.get("OS_PERTURB_FPS", "8"))

    with Live(console=console, screen=True, auto_refresh=False) as live:
        for fid, ts, frame in stream_frames(_vid, fps_target=fps_target_val):
            if perturb_mode == "dropped_frames" and random.random() < perturb_prob:
                continue
                
            t_frame_start = time.time()
            if writer is None:
                h, w = frame.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                # Extract base filename to avoid writing over previous output
                out_name = f"{run_dir}/output.mp4"
                writer = cv2.VideoWriter(out_name, fourcc, 8, (w, h))
                
            t_yolo_start = time.time()
            results = detector(frame, conf=CONF_THRESHOLD, verbose=False)
            yolo_ms = (time.time() - t_yolo_start) * 1000.0
            
            bboxes, box_classes, box_confidences = [], [], []
            for box in results[0].boxes:
                conf = float(box.conf[0])
                if perturb_mode == "low_confidence":
                    conf *= (1.0 - perturb_prob)
                    if conf < CONF_THRESHOLD:
                        continue
                
                bbox = box.xyxy[0].tolist()
                if perturb_mode == "occlusion":
                    cx = (bbox[0] + bbox[2]) / 2.0
                    cy = (bbox[1] + bbox[3]) / 2.0
                    h_img, w_img = frame.shape[:2]
                    if (w_img * 0.25 <= cx <= w_img * 0.75) and (h_img * 0.25 <= cy <= h_img * 0.75):
                        continue
                        
                if perturb_mode == "missing_detections" and random.random() < perturb_prob:
                    continue
                    
                if perturb_mode == "camera_jitter":
                    dx = random.randint(-15, 15)
                    dy = random.randint(-15, 15)
                    bbox = [bbox[0]+dx, bbox[1]+dy, bbox[2]+dx, bbox[3]+dy]

                bboxes.append(bbox)
                box_classes.append(int(box.cls[0]))
                box_confidences.append(conf)

            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            signatures = []
            for bbox in bboxes:
                try:
                    h_img, w_img = frame.shape[:2]
                    x1_c, y1_c, x2_c, y2_c = [int(v) for v in bbox]
                    x1_c, y1_c = max(0, x1_c), max(0, y1_c)
                    x2_c, y2_c = min(w_img, x2_c), min(h_img, y2_c)
                    if x2_c <= x1_c or y2_c <= y1_c:
                        signatures.append(np.zeros((125,), dtype=np.float32))
                    else:
                        crop = frame[y1_c:y2_c, x1_c:x2_c]
                        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                        hist = cv2.calcHist([hsv], [0, 1, 2], None, [5, 5, 5], [0, 180, 0, 256, 0, 256])
                        cv2.normalize(hist, hist)
                        signatures.append(hist.flatten())
                except Exception:
                    signatures.append(np.zeros((125,), dtype=np.float32))
            
            t_track_start = time.time()
            tracks = tracker.update(bboxes, fid, ts, frame_gray=frame_gray, confs=box_confidences, signatures=signatures)
            track_ms = (time.time() - t_track_start) * 1000.0
            
            if perturb_mode == "tracker_id_switch" and len(tracks) >= 2:
                if random.random() < perturb_prob:
                    idx1, idx2 = random.sample(range(len(tracks)), 2)
                    t1, b1, n1 = tracks[idx1]
                    t2, b2, n2 = tracks[idx2]
                    tracks[idx1] = (t2, b1, n1)
                    tracks[idx2] = (t1, b2, n2)

            t_journey_start = time.time()
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
                    try:
                        evidence_dir = os.path.join(run_dir, "evidence")
                        os.makedirs(evidence_dir, exist_ok=True)
                        h_img, w_img = frame.shape[:2]
                        x1_e, y1_e, x2_e, y2_e = [int(v) for v in bbox]
                        x1_e, y1_e = max(0, x1_e), max(0, y1_e)
                        x2_e, y2_e = min(w_img, x2_e), min(h_img, y2_e)
                        if x2_e > x1_e and y2_e > y1_e:
                            crop = frame[y1_e:y2_e, x1_e:x2_e]
                            cv2.imwrite(os.path.join(evidence_dir, f"{token}_{fid}.jpg"), crop)
                    except Exception:
                        pass

                visit = visit_manager.get_visit(token)
                if visit:
                    visit_manager.update_visit_role(token, "staff" if is_staff else "guest", dt_ts_current)
                    
                prev_z = token_current_zone.get(token)
                if current_z != prev_z:
                    visit_manager.update_visit_zone(token, current_z, dt_ts_current, centroid=(cx, cy))
                    token_current_zone[token] = current_z
                    if prev_z is not None:
                        try:
                            evidence_dir = os.path.join(run_dir, "evidence")
                            os.makedirs(evidence_dir, exist_ok=True)
                            h_img, w_img = frame.shape[:2]
                            x1_e, y1_e, x2_e, y2_e = [int(v) for v in bbox]
                            x1_e, y1_e = max(0, x1_e), max(0, y1_e)
                            x2_e, y2_e = min(w_img, x2_e), min(h_img, y2_e)
                            if x2_e > x1_e and y2_e > y1_e:
                                crop = frame[y1_e:y2_e, x1_e:x2_e]
                                cv2.imwrite(os.path.join(evidence_dir, f"{token}_{current_z}_{fid}.jpg"), crop)
                        except Exception:
                            pass

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

            # Render Executive Overlay (Phase 2)
            overlay = frame.copy()
            fid_clamped = min(fid, total_frames)

            # Compute stats early based on business state machine (Task 3 & 4)
            entered_count = sum(1 for j in journey_manager.journeys if j.state in ("ENTERED", "WAITING", "DINING", "EXITED") and not getattr(j, "is_initial_spawn", False))
            exited_count = sum(1 for j in journey_manager.journeys if j.state == "EXITED" and not getattr(j, "is_initial_spawn", False))
            curr_occ = sum(1 for j in journey_manager.journeys if j.state in ("ENTERED", "WAITING", "DINING") and not getattr(j, "is_initial_spawn", False))
            active_tables_count = 0 # No table view in this camera role
            
            queue_size_count = sum(1 for j in journey_manager.journeys if j.state == "WAITING" and not getattr(j, "is_initial_spawn", False))
            queue_members_list = [j.journey_id for j in journey_manager.journeys if j.state == "WAITING" and not getattr(j, "is_initial_spawn", False)]

            # Track peak occupancy updates
            if curr_occ > max_occ_seen:
                max_occ_seen = curr_occ
                peak_occ_img = frame.copy()
                peak_occ_frame_id = fid
            if queue_size_count > max_q_seen:
                max_q_seen = queue_size_count
                max_q_img = frame.copy()
                max_q_frame_id = fid

            # Check for business events and log them / trigger banners (Task 3)
            if entered_count > prev_entered_count:
                recent_ent = [j for j in journey_manager.journeys if j.entry_frame == fid_clamped]
                ent_jid = recent_ent[0].journey_id if recent_ent else "N/A"
                ent_tid = recent_ent[0].active_tracker_ids[-1] if (recent_ent and recent_ent[0].active_tracker_ids) else "N/A"
                banner_text = "ENTRY +1"
                banner_color = (0, 255, 0)
                banner_timer = 20
                event_log_rows.append([fid_clamped, dt_ts_current.isoformat(), "Guest Entered", ent_jid, ent_tid, entered_count, exited_count, curr_occ, queue_size_count])
                prev_entered_count = entered_count

            if exited_count > prev_exited_count:
                recent_ex = [j for j in journey_manager.journeys if j.exit_frame == fid_clamped]
                ex_jid = recent_ex[0].journey_id if recent_ex else "N/A"
                ex_tid = recent_ex[0].active_tracker_ids[-1] if (recent_ex and recent_ex[0].active_tracker_ids) else "N/A"
                banner_text = "EXIT +1"
                banner_color = (0, 0, 255)
                banner_timer = 20
                event_log_rows.append([fid_clamped, dt_ts_current.isoformat(), "Guest Exited", ex_jid, ex_tid, entered_count, exited_count, curr_occ, queue_size_count])
                prev_exited_count = exited_count

            if queue_size_count != prev_queue_size:
                banner_text = f"QUEUE = {queue_size_count}"
                banner_color = (0, 165, 255)
                banner_timer = 20
                event_log_rows.append([fid_clamped, dt_ts_current.isoformat(), "Queue Changed", "N/A", "N/A", entered_count, exited_count, curr_occ, queue_size_count])
                prev_queue_size = queue_size_count

            if curr_occ > prev_peak_occ:
                banner_text = f"NEW PEAK OCCUPANCY = {curr_occ}"
                banner_color = (255, 0, 255)
                banner_timer = 20
                event_log_rows.append([fid_clamped, dt_ts_current.isoformat(), "Peak Occupancy Updated", "N/A", "N/A", entered_count, exited_count, curr_occ, queue_size_count])
                prev_peak_occ = curr_occ

            # Draw polygon debug overlay
            for zone_name, poly_pts in zone_mapper.zones.items():
                pts_arr = np.array(poly_pts, np.int32).reshape((-1, 1, 2))
                cv2.polylines(overlay, [pts_arr], isClosed=True, color=(100, 100, 100), thickness=1)
                cv2.putText(overlay, zone_name, (int(max(5, poly_pts[0][0])), int(max(15, poly_pts[0][1]))), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (140, 140, 140), 1)

            drawn_label_ys = [] # Prevent label overlap
            for token, bbox, is_new in tracks:
                x1, y1, x2, y2 = [int(v) for v in bbox]
                is_staff = token_is_staff.get(token, 0)
                visit = visit_manager.get_visit(token)
                state_str = visit.current_state if visit else "UNKNOWN"
                zone_str = visit.current_zone if visit else "None"
                
                # Check active journey details (Task 2)
                matching_j = None
                for j in journey_manager.journeys:
                    if token in j.active_tracker_ids and j.status == "active":
                        matching_j = j
                        break
                if matching_j:
                    jid_str = matching_j.journey_id[:8]
                    zone_str = matching_j.current_zone
                    state_str = matching_j.state
                    label_text = f"Trk {token} | J: {jid_str} | Z: {zone_str} | St: {state_str}"
                else:
                    label_text = f"Trk {token} | Zone: {zone_str} | State: {state_str}"
                
                color = (0, 255, 100) if is_staff else (0, 165, 255)
                # Bounding box corners
                cv2.rectangle(overlay, (x1, y1), (x1+15, y1+2), color, -1)
                cv2.rectangle(overlay, (x1, y1), (x1+2, y1+15), color, -1)
                cv2.rectangle(overlay, (x2-15, y2-2), (x2, y2), color, -1)
                cv2.rectangle(overlay, (x2-2, y2-15), (x2, y2), color, -1)

                pts = list(centroid_history.get(token, []))
                for i in range(1, len(pts)):
                    thickness = int(np.sqrt(10 / float(i + 1)) * 2.0)
                    cv2.line(overlay, pts[i - 1], pts[i], color, thickness)
                
                font_scale = 0.35
                (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
                lx = max(0, min(x1, w - tw - 10))
                ly = y1 - 10
                while any(abs(ly - dy) < 18 for dy in drawn_label_ys):
                    ly -= 18
                ly = max(th + 5, min(ly, h - 5))
                drawn_label_ys.append(ly)
                cv2.rectangle(overlay, (lx, ly - th - 6), (lx + tw + 8, ly + 2), (0, 0, 0), -1)
                cv2.putText(overlay, label_text, (lx + 4, ly - 2), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 1)

            # Draw Telemetry HUD Card (Task 2 & 3)
            hud_x, hud_y = w - 260, 20
            cv2.rectangle(overlay, (hud_x, hud_y), (hud_x + 240, hud_y + 170), (0, 0, 0), -1)
            cv2.rectangle(overlay, (hud_x, hud_y), (hud_x + 240, hud_y + 170), (100, 100, 100), 1)
            cv2.putText(overlay, f"Frame: {fid_clamped}", (hud_x + 10, hud_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
            cv2.putText(overlay, f"Guests Entered: {entered_count}", (hud_x + 10, hud_y + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
            cv2.putText(overlay, f"Guests Exited: {exited_count}", (hud_x + 10, hud_y + 85), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
            cv2.putText(overlay, f"Current Occupancy: {curr_occ}", (hud_x + 10, hud_y + 115), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 165, 0), 1)
            cv2.putText(overlay, f"Queue Length: {queue_size_count}", (hud_x + 10, hud_y + 145), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

            # Highlight Event Banners (Task 3)
            if banner_text and banner_timer > 0:
                banner_timer -= 1
                bx1, by1 = int(w * 0.15), int(h * 0.4)
                bx2, by2 = int(w * 0.85), int(h * 0.55)
                cv2.rectangle(overlay, (bx1, by1), (bx2, by2), (0, 0, 0), -1)
                cv2.rectangle(overlay, (bx1, by1), (bx2, by2), banner_color, 2)
                text_scale = 1.1
                (txw, txh), _ = cv2.getTextSize(banner_text, cv2.FONT_HERSHEY_SIMPLEX, text_scale, 3)
                tx = bx1 + (bx2 - bx1 - txw) // 2
                ty = by1 + (by2 - by1 + txh) // 2
                cv2.putText(overlay, banner_text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, text_scale, banner_color, 3)

            # Apply transparency
            frame = cv2.addWeighted(overlay, 0.75, frame, 0.25, 0)
            
            # Update state engine
            journey_update_ms = (time.time() - t_journey_start) * 1000.0
            state_engine.accumulate_heatmap_points(tracks, token_is_staff)
            state_engine.update_performance({
                "yolo_inference_time_ms": round(yolo_ms, 2),
                "tracking_latency_ms": round(track_ms, 2),
                "journey_update_time_ms": round(journey_update_ms, 2),
                "rule_evaluation_time_ms": round(EventRuleEngine.last_eval_time_ms, 2),
                "transition_validation_time_ms": round(TransitionValidator.last_validate_time_ms, 2),
                "sqlite_write_latency_ms": round(getattr(journey_manager, "last_db_write_time_ms", 0.0), 2),
                "overall_fps": round(1.0 / (time.time() - t_frame_start), 1) if (time.time() - t_frame_start) > 0 else 0.0
            })
            state_engine.process_frame_state(dt_ts_current, fid, tracks, token_is_staff)
            
            rose.refresh()
            snapshot = rose.get_current_snapshot()
            decisions = intel.evaluate_snapshot(snapshot)
            final_snapshot = snapshot
            final_decisions = decisions

            live.update(build_layout(snapshot, state_engine), refresh=True)
            
            frame_stats.append({
                "frame": fid_clamped,
                "people_visible": len(tracks),
                "staff_visible": sum(1 for token, bbox, is_new in tracks if token_is_staff.get(token, 0) == 1),
                "customer_visible": sum(1 for token, bbox, is_new in tracks if token_is_staff.get(token, 0) != 1),
                "active_journeys": sum(1 for j in journey_manager.journeys if j.status == "active"),
                "active_tables": active_tables_count,
                "queue_size": queue_size_count
            })
            
            # Persist frame occupancies (Phase 5)
            active_j_ids = ",".join(j.journey_id for j in journey_manager.journeys if j.status == "active" and j.current_zone != "OUTSIDE")
            DB.execute("INSERT OR REPLACE INTO frame_occupancies (frame, camera_id, occupancy, active_journey_ids) VALUES (?, ?, ?, ?)", (fid_clamped, _cam, curr_occ, active_j_ids))
            
            # Persist frame queues
            queue_members = ",".join(queue_members_list)
            DB.execute("INSERT OR REPLACE INTO frame_queues (frame, camera_id, queue_length, queue_members) VALUES (?, ?, ?, ?)", (fid_clamped, _cam, queue_size_count, queue_members))
            DB.commit()
            
            curr_occ = sum(1 for j in journey_manager.journeys if j.status == "active" and j.current_zone != "OUTSIDE")
            if curr_occ > max_occ_seen:
                max_occ_seen = curr_occ
                peak_occ_img = frame.copy()
                peak_occ_frame_id = fid
                
            if queue_size_count > max_q_seen:
                max_q_seen = queue_size_count
                max_q_img = frame.copy()
                max_q_frame_id = fid
                
            for j in journey_manager.journeys:
                if j.entry_frame == fid and j.journey_id not in saved_entries:
                    saved_entries.add(j.journey_id)
                    entry_dir = f"runs/{video_name}/demo_final/annotated_guest_entries"
                    os.makedirs(entry_dir, exist_ok=True)
                    cv2.imwrite(f"{entry_dir}/{j.journey_id}_entry.jpg", frame)
            
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
        # Append summary freeze-frame slide (Task 7)
        summary_slide = np.zeros((h_vid, w_vid, 3), dtype=np.uint8)
        cv2.rectangle(summary_slide, (20, 20), (w_vid-20, h_vid-20), (50, 50, 50), 2)
        cv2.putText(summary_slide, "AURIKA EXECUTIVE SUMMARY", (int(w_vid * 0.15), 80), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
        cv2.putText(summary_slide, f"Guests Entered: {entered_count}", (int(w_vid * 0.2), 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(summary_slide, f"Guests Exited: {exited_count}", (int(w_vid * 0.2), 210), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(summary_slide, f"Current Occupancy: {curr_occ}", (int(w_vid * 0.2), 260), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(summary_slide, f"Peak Occupancy: {max_occ_seen}", (int(w_vid * 0.2), 310), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(summary_slide, f"Maximum Queue Length: {max_q_seen}", (int(w_vid * 0.2), 360), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(summary_slide, f"Tables Occupied: {active_tables_count}", (int(w_vid * 0.2), 410), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        for _ in range(90): # 3.0 seconds slide show
            writer.write(summary_slide)
        writer.release()
        writer = None

    # Write event_log.csv
    import csv
    event_log_path = f"runs/{video_name}/demo_final/event_log.csv"
    os.makedirs(os.path.dirname(event_log_path), exist_ok=True)
    with open(event_log_path, "w", newline="") as f:
        writer_log = csv.writer(f)
        writer_log.writerow(["Frame", "Time", "Event", "Journey ID", "Track ID", "Running Entered", "Running Exited", "Running Occupancy", "Running Queue"])
        for row in event_log_rows:
            writer_log.writerow(row)
        
    for token, entry_ts, exit_ts in tracker.flush_all():
        visit_manager.handle_track_end(token, VIDEO_START + timedelta(seconds=exit_ts))
        log_session_end(token, entry_ts, exit_ts, served_tokens, service_times, token_is_staff.get(token, 0))
        # If the track disappeared at least 1.0 second before the final frame, mark as exited/lost
        if exit_ts < ts - 1.0:
            journey_manager.handle_track_lost(token, VIDEO_START + timedelta(seconds=exit_ts))
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
        if j.entry_time and not getattr(j, "is_initial_spawn", False):
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
        if (j.status == "exited" or j.exit_time) and not getattr(j, "is_initial_spawn", False):
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
        elif j.seated_time and j.status == "active":
            dining_dur = (j.last_active_time - j.seated_time).total_seconds()
            if dining_dur > 0:
                dining_support.append({
                    "journey": j.journey_id,
                    "dining_duration_seconds": dining_dur,
                    "seated_time": j.seated_time.isoformat()
                })
    avg_dining = sum(x["dining_duration_seconds"] for x in dining_support)/len(dining_support) if dining_support else 0.0
    kpis_evidence["average_dining_time"] = {
        "metric": "average_dining_time",
        "value": avg_dining,
        "support": dining_support
    }
    
    with open(f"{run_dir}/kpis_evidence.json", "w") as f:
        json.dump(kpis_evidence, f, indent=4)
        
    with open(f"{run_dir}/frame_statistics.json", "w") as f:
        json.dump(frame_stats, f, indent=4)
        
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

    # Trigger Business Intelligence report generation
    try:
        from restaurant_analytics.business_intelligence_engine import BusinessIntelligenceEngine
        bi_engine = BusinessIntelligenceEngine(db_path, f"runs/{video_name}/business_intelligence")
        bi_engine.generate_report(video_name)
    except Exception as e:
        print(f"[BI Engine] Failed to generate business intelligence report: {e}")

    # Trigger verified Demo Package generation
    try:
        from restaurant_analytics.demo_package_generator import DemoPackageGenerator
        demo_gen = DemoPackageGenerator(db_path, f"runs/{video_name}/demo")
        demo_gen.generate(video_name)
    except Exception as e:
        print(f"[Demo Generator] Failed to generate demo package: {e}")

    # Write peak occupancy and max queue annotated frames
    demo_final_dir = f"runs/{video_name}/demo_final"
    os.makedirs(demo_final_dir, exist_ok=True)
    if peak_occ_img is not None:
        cv2.imwrite(f"{demo_final_dir}/annotated_peak_occupancy.jpg", peak_occ_img)
    if max_q_img is not None:
        cv2.imwrite(f"{demo_final_dir}/annotated_max_queue.jpg", max_q_img)

    # Trigger final verified validation package
    try:
        from restaurant_analytics.demo_final_validator import DemoFinalValidator
        cap_temp = cv2.VideoCapture(_vid)
        total_native_frames = int(cap_temp.get(cv2.CAP_PROP_FRAME_COUNT))
        cap_temp.release()
        final_validator = DemoFinalValidator(db_path, demo_final_dir, total_frames=total_native_frames)
        final_validator.generate_package(video_name)
    except Exception as e:
        print(f"[Demo Final Validator] Failed to generate verified final package: {e}")

try:
    cv2.destroyAllWindows()
except Exception:
    pass
try:
    if DB:
        DB.close()
except Exception:
    pass
