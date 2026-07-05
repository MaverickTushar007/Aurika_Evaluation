import os
import uuid
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

class Journey:
    def __init__(self, first_track_id: str, entry_time: datetime, entry_gate: str = "Entrance", start_centroid: Optional[tuple] = None):
        self.journey_id = str(uuid.uuid4())
        self.active_tracker_ids = [first_track_id]
        self.entry_time = entry_time
        self.exit_time: Optional[datetime] = None
        self.entry_gate = entry_gate
        self.current_zone = entry_gate
        self.zone_history = [entry_gate]
        self.waiting_started: Optional[datetime] = None
        self.waiting_duration: float = 0.0
        self.dining_duration: float = 0.0
        self.table_id: Optional[str] = None
        self.seated_time: Optional[datetime] = None
        self.server_visits = 0
        self.confidence = 1.0
        self.status = "active" # "active", "exited", "lost"
        self.last_centroid = start_centroid
        self.previous_centroid = None
        self.last_active_time = entry_time
        self.state = "ENTERED" # Forward-only states
        self.role = "guest"
        self.state_history = [(entry_time, "ENTERED", 0)]
        self.entry_frame: Optional[int] = None
        self.reception_frame: Optional[int] = None
        self.waiting_start_frame: Optional[int] = None
        self.waiting_end_frame: Optional[int] = None
        self.seated_frame: Optional[int] = None
        self.exit_frame: Optional[int] = None
        self.timeline: List[Dict[str, Any]] = []

    def update_state(self, new_state: str, timestamp: datetime, frame_id: int):
        states = ["UNKNOWN", "ENTERED", "RECEPTION", "WAITING", "ESCORTED", "SEATED", "ORDERING", "FOOD_SERVED", "DINING", "PAYMENT", "EXITED"]
        if new_state not in states:
            return
        curr_idx = states.index(self.state)
        new_idx = states.index(new_state)
        if new_idx > curr_idx: # Only move forward!
            self.state = new_state
            self.state_history.append((timestamp, new_state, frame_id))
            self.timeline.append({
                "frame": frame_id,
                "timestamp": timestamp.isoformat(),
                "state": new_state
            })
            
            # Map frames
            if new_state == "ENTERED":
                self.entry_frame = frame_id
            elif new_state == "RECEPTION":
                self.reception_frame = frame_id
            elif new_state == "WAITING":
                self.waiting_start_frame = frame_id
            elif new_state == "SEATED":
                self.seated_frame = frame_id
            elif new_state == "EXITED":
                self.exit_frame = frame_id

class JourneyManager:
    def __init__(self, db_path: str = "db/customer_intel.db"):
        self.db_path = db_path
        self.journeys: List[Journey] = []
        self.merge_count = 0
        self.split_count = 0
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        # Create journeys table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS journeys (
                journey_id TEXT PRIMARY KEY,
                entry_time TEXT,
                exit_time TEXT,
                entry_gate TEXT,
                current_zone TEXT,
                waiting_duration REAL,
                dining_duration REAL,
                table_id TEXT,
                seated_time TEXT,
                server_visits INTEGER,
                confidence REAL,
                status TEXT,
                state TEXT
            )
        ''')
        # Create server_visits table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS server_visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_id TEXT,
                staff_id TEXT,
                timestamp TEXT,
                duration REAL
            )
        ''')
        conn.commit()
        conn.close()

    def find_matching_journey(self, track_id: str, zone: str, centroid: Optional[tuple], timestamp: datetime) -> Optional[Journey]:
        # Merge criteria: track disappears and new track appears nearby within 8.0s, same movement/zone
        for j in self.journeys:
            if j.status == "lost" and (timestamp - j.last_active_time).total_seconds() <= 8.0:
                # Spatial check
                if centroid and j.last_centroid:
                    dist = ((centroid[0]-j.last_centroid[0])**2 + (centroid[1]-j.last_centroid[1])**2)**0.5
                    if dist <= 150: # Nearby
                        return j
                # Same zone fallback
                if j.current_zone == zone:
                    return j
        return None

    def handle_track_update(self, track_id: str, zone: str, centroid: tuple, is_new: bool, is_staff: bool, timestamp: datetime, frame_id: int, frame_img: Any, bbox: list, run_dir: str):
        def save_evidence_thumbnail(journey_id, state, img, box, directory):
            try:
                import cv2
                evidence_dir = f"{directory}/evidence"
                os.makedirs(evidence_dir, exist_ok=True)
                h, w = img.shape[:2]
                x1, y1, x2, y2 = [max(0, min(int(v), limit)) for v, limit in zip(box, [w, h, w, h])]
                crop = img[y1:y2, x1:x2]
                if crop.size > 0:
                    cv2.imwrite(f"{evidence_dir}/{journey_id}_{state.lower()}.jpg", crop)
            except Exception as e:
                print(f"Failed to save evidence thumbnail: {e}")

        role = "staff" if is_staff else "guest"
        if is_new:
            # Try to merge with lost journeys
            j = self.find_matching_journey(track_id, zone, centroid, timestamp)
            if j:
                self.merge_count += 1
                j.active_tracker_ids.append(track_id)
                j.status = "active"
                j.last_active_time = timestamp
                j.last_centroid = centroid
                print(f"TRACK MERGED: Track {track_id} merged into existing Journey {j.journey_id} (survival of fragmentation)")
            else:
                # Check for recent track lost that suggests split
                has_recent_lost = any(journey.status == "lost" and (timestamp - journey.last_active_time).total_seconds() <= 8.0 for journey in self.journeys)
                if has_recent_lost:
                    self.split_count += 1
                
                # Create a new Journey
                j = Journey(track_id, timestamp, entry_gate=zone, start_centroid=centroid)
                j.role = role
                j.entry_frame = frame_id
                self.journeys.append(j)
                print(f"JOURNEY CREATED: New customer Journey {j.journey_id} started via Track {track_id}")
                self.save_journey(j)
                # Emit Entered event
                self.log_event(j.journey_id, track_id, "entered", timestamp, zone)
                save_evidence_thumbnail(j.journey_id, "entered", frame_img, bbox, run_dir)
        else:
            # Find the active journey owning this track ID
            j = None
            for journey in self.journeys:
                if track_id in journey.active_tracker_ids:
                    j = journey
                    break
            if j:
                j.last_active_time = timestamp
                j.previous_centroid = j.last_centroid
                j.last_centroid = centroid
                
                # Zone change checks
                if zone != j.current_zone:
                    old_zone = j.current_zone
                    j.current_zone = zone
                    j.zone_history.append(zone)
                    self.log_event(j.journey_id, track_id, "enter_zone", timestamp, zone)
                    print(f"JOURNEY ZONE TRANSITION: Journey {j.journey_id} | Track {track_id} | {old_zone} -> {zone}")
                    
                    # Waiting duration: waiting ends when they leave the Waiting Area (Step 6)
                    if old_zone == "Waiting Area" and j.waiting_started:
                        j.waiting_duration = (timestamp - j.waiting_started).total_seconds()
                        j.waiting_end_frame = frame_id
                        print(f"WAITING COMPLETED: Journey {j.journey_id} waited for {j.waiting_duration:.1f}s")
                    
                    # Dining duration ends when they leave the table polygon (Step 7)
                    if old_zone and "table" in old_zone.lower() and j.seated_time:
                        j.dining_duration = (timestamp - j.seated_time).total_seconds()
                        print(f"DINING COMPLETED: Journey {j.journey_id} dined for {j.dining_duration:.1f}s")
                    
                    # Update business state machine (Step 4 & 5)
                    if zone == "Entrance":
                        j.update_state("ENTERED", timestamp, frame_id)
                        save_evidence_thumbnail(j.journey_id, "entered", frame_img, bbox, run_dir)
                    elif zone == "Reception":
                        j.update_state("RECEPTION", timestamp, frame_id)
                        save_evidence_thumbnail(j.journey_id, "reception", frame_img, bbox, run_dir)
                        self.log_event(j.journey_id, track_id, "Reached Reception", timestamp, zone)
                    elif zone == "Waiting Area":
                        j.update_state("WAITING", timestamp, frame_id)
                        j.waiting_started = timestamp
                        j.waiting_start_frame = frame_id
                        save_evidence_thumbnail(j.journey_id, "waiting", frame_img, bbox, run_dir)
                        self.log_event(j.journey_id, track_id, "waiting", timestamp, zone)
                    elif "table" in zone.lower():
                        j.update_state("SEATED", timestamp, frame_id)
                        j.table_id = zone
                        j.seated_time = timestamp
                        j.seated_frame = frame_id
                        save_evidence_thumbnail(j.journey_id, "seated", frame_img, bbox, run_dir)
                        self.log_event(j.journey_id, track_id, "seated", timestamp, zone)
                    elif zone == "Exit":
                        j.update_state("EXITED", timestamp, frame_id)
                        j.exit_time = timestamp
                        j.status = "exited"
                        j.exit_frame = frame_id
                        save_evidence_thumbnail(j.journey_id, "exit", frame_img, bbox, run_dir)
                        self.log_event(j.journey_id, track_id, "exited", timestamp, zone)
                    elif zone == "Dining" and j.state in ["WAITING", "RECEPTION", "ENTERED"]:
                        j.update_state("ESCORTED", timestamp, frame_id)
                        self.log_event(j.journey_id, track_id, "escorted", timestamp, zone)

                    self.save_journey(j)

    def handle_track_lost(self, track_id: str, timestamp: datetime):
        for j in self.journeys:
            if track_id in j.active_tracker_ids and j.status == "active":
                j.status = "lost"
                j.last_active_time = timestamp
                self.save_journey(j)
                print(f"TRACK LOST: Tracker {track_id} went offline. Journey {j.journey_id} marked as lost/pending reassociation.")
                break

    def sweep_lost_journeys(self, current_time: datetime, force_all: bool = False, frame_id: int = 0):
        for j in self.journeys:
            if j.status == "lost":
                offline_dur = (current_time - j.last_active_time).total_seconds()
                if force_all or offline_dur > 8.0:
                    j.status = "exited"
                    j.exit_time = j.last_active_time
                    j.update_state("EXITED", j.last_active_time, frame_id)
                    j.exit_frame = frame_id
                    if j.seated_time and j.dining_duration == 0.0:
                        j.dining_duration = (j.last_active_time - j.seated_time).total_seconds()
                    self.save_journey(j)
                    # Also log the Exited business event to SQLite for CEO QA questions!
                    self.log_event(j.journey_id, j.active_tracker_ids[-1], "exited", j.last_active_time, j.current_zone)
                    print(f"JOURNEY FINALIZED: Journey {j.journey_id} has been offline for {offline_dur:.1f}s. Finalized as EXITED.")

    def save_journey(self, j: Journey):
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        conn.execute('''
            INSERT OR REPLACE INTO journeys (journey_id, entry_time, exit_time, entry_gate, current_zone, waiting_duration, dining_duration, table_id, seated_time, server_visits, confidence, status, state)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            j.journey_id,
            j.entry_time.isoformat() if j.entry_time else None,
            j.exit_time.isoformat() if j.exit_time else None,
            j.entry_gate,
            j.current_zone,
            j.waiting_duration,
            j.dining_duration,
            j.table_id,
            j.seated_time.isoformat() if j.seated_time else None,
            j.server_visits,
            j.confidence,
            j.status,
            j.state
        ))
        conn.commit()
        conn.close()

    def log_event(self, journey_id: str, track_id: str, event_type: str, timestamp: datetime, zone: str):
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        conn.execute('''
            INSERT INTO business_events (session_id, event_type, timestamp, value, zone_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (track_id, event_type, timestamp.isoformat(), None, zone))
        conn.commit()
        conn.close()

    def log_server_visit(self, table_id: str, staff_id: str, timestamp: datetime, duration: float):
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        conn.execute('''
            INSERT INTO server_visits (table_id, staff_id, timestamp, duration)
            VALUES (?, ?, ?, ?)
        ''', (table_id, staff_id, timestamp.isoformat(), duration))
        conn.commit()
        conn.close()
        # Increment server visit count for any customer currently seated at that table!
        for j in self.journeys:
            if j.table_id == table_id and j.status == "active":
                j.server_visits += 1
                self.save_journey(j)
                print(f"SERVER VISIT LOGGED: Staff {staff_id} visited table {table_id} for {duration:.1f}s. Associated with Customer Journey {j.journey_id}.")
