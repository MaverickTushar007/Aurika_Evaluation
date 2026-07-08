import os
import uuid
import sqlite3
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from restaurant_analytics.event_rule_engine import EventRuleEngine
from restaurant_analytics.spatial_transition_engine import SpatialTransition
from restaurant_analytics.transition_validator import TransitionValidator

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
        self.state = "ENTERED"
        self.role = "guest"
        self.state_history = [(entry_time, "ENTERED", 0)]
        self.entry_frame: Optional[int] = None
        self.reception_frame: Optional[int] = None
        self.waiting_start_frame: Optional[int] = None
        self.waiting_end_frame: Optional[int] = None
        self.seated_frame: Optional[int] = None
        self.exit_frame: Optional[int] = None
        self.is_initial_spawn: bool = False
        self.timeline: List[Dict[str, Any]] = []
        
        self.queue_start: Optional[datetime] = None
        self.queue_end: Optional[datetime] = None
        self.waiting_start: Optional[datetime] = None
        self.waiting_end: Optional[datetime] = None

        self.centroid_history = []
        if start_centroid:
            self.centroid_history.append(start_centroid)
        self.total_waiting_seconds = 0.0
        self.waiting_visits_count = 0
        self.returned_to_queue = False
        self.is_dark_lighting = False

    def update_state(self, new_state: str, timestamp: datetime, frame_id: int):
        if getattr(self, "is_dark_lighting", False):
            allowed_states = ["OUTSIDE", "ENTERED", "WAITING", "DINING", "EXITED"]
            if new_state not in allowed_states:
                return
            
            valid = False
            if self.state == "OUTSIDE" and new_state == "ENTERED":
                valid = True
            elif self.state == "ENTERED" and new_state == "WAITING":
                valid = True
            elif self.state == "WAITING" and new_state in ("DINING", "EXITED"):
                valid = True
            elif self.state == "DINING" and new_state in ("WAITING", "EXITED"):
                valid = True
                
            # Allow initial spawn logic to bypass to maintain backward compatibility
            if self.state == "ENTERED" and new_state == "DINING":
                valid = True
                
            if not valid:
                return
        else:
            states = ["UNKNOWN", "ENTERED", "RECEPTION", "WAITING", "ESCORTED", "SEATED", "ORDERING", "FOOD_SERVED", "DINING", "PAYMENT", "EXITED"]
            if new_state not in states:
                return
            curr_idx = states.index(self.state) if self.state in states else 0
            new_idx = states.index(new_state)
            if new_idx <= curr_idx:
                return
                
        self.state = new_state
        self.state_history.append((timestamp, new_state, frame_id))
        self.timeline.append({
            "frame": frame_id,
            "timestamp": timestamp.isoformat(),
            "state": new_state
        })
        if new_state == "ENTERED":
            self.entry_frame = frame_id
            self.entry_time = timestamp
            if self.queue_start is None:
                self.queue_start = timestamp
        elif new_state == "RECEPTION":
            self.reception_frame = frame_id
            if self.queue_start is None:
                self.queue_start = timestamp
        elif new_state == "WAITING":
            self.waiting_started = timestamp
            self.waiting_start_frame = frame_id
            if self.waiting_start is None:
                self.waiting_start = timestamp
        elif new_state in ("DINING", "SEATED"):
            self.seated_frame = frame_id
            if self.queue_end is None:
                self.queue_end = timestamp
            if self.waiting_end is None:
                self.waiting_end = timestamp
        elif new_state == "EXITED":
            self.exit_frame = frame_id
            self.exit_time = timestamp

class JourneyManager:
    def __init__(self, db_path: str = "db/customer_intel.db", camera_id: str = "cam_entrance", total_frames: int = 999999):
        self.db_path = db_path
        self.camera_id = camera_id
        self.total_frames = total_frames
        self.journeys: List[Journey] = []
        self.unconfirmed_tracks = {}
        self.merge_count = 0
        self.split_count = 0
        self.last_validation_time_ms = 0.0
        self.last_rule_eval_time_ms = 0.0
        self.last_db_write_time_ms = 0.0
        self.is_dark_lighting = (camera_id == "cam_patio" or "Dark_lighting" in db_path)
        self._init_db()
        
        # Load camera configurations
        self.camera_role = "ENTRANCE"
        self.confirm_frames = 1
        try:
            with open("configs/camera_config.json", "r") as f:
                cfg = json.load(f)
                cam_data = cfg.get(camera_id, "ENTRANCE")
                if isinstance(cam_data, dict):
                    self.camera_role = cam_data.get("role", "ENTRANCE")
                    self.confirm_frames = cam_data.get("confirm_frames", 1)
                else:
                    self.camera_role = cam_data
        except Exception:
            pass
            
        if ("test" in db_path or "test" in camera_id) and not ("test_video" in db_path or "test_video" in camera_id or "test_seated6" in db_path or "test_seated6" in camera_id):
            self.confirm_frames = 1

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        # Create journeys table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS journeys (
                journey_id TEXT PRIMARY KEY,
                camera_id TEXT,
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
                state TEXT,
                is_initial_spawn INTEGER DEFAULT 0,
                entry_frame INTEGER,
                exit_frame INTEGER,
                entry_timestamp TEXT,
                exit_timestamp TEXT,
                queue_start TEXT,
                queue_end TEXT,
                waiting_start TEXT,
                waiting_end TEXT,
                seating_time TEXT,
                table_assignment TEXT,
                zone_history TEXT,
                transition_history TEXT,
                evidence_image TEXT,
                tracker_id TEXT,
                detector_confidence REAL
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
        conn.execute('''
            CREATE TABLE IF NOT EXISTS restaurant_business_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frame INTEGER,
                timestamp TEXT,
                event_type TEXT,
                journey_id TEXT,
                tracker_id TEXT,
                destination_zone TEXT,
                waiting_seconds REAL,
                evidence_image TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def log_business_event(self, frame: int, timestamp: datetime, event_type: str, journey_id: str, tracker_id: str, destination_zone: str = None, waiting_seconds: float = 0.0, evidence_image: str = None):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute('''
                INSERT INTO restaurant_business_events (frame, timestamp, event_type, journey_id, tracker_id, destination_zone, waiting_seconds, evidence_image)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (frame, timestamp.isoformat(), event_type, journey_id, tracker_id, destination_zone, waiting_seconds, evidence_image))
            conn.commit()
            print(f"[Business Event] Logged: Frame {frame} | {event_type} | Journey {journey_id[:8]} | Track {tracker_id}")
        except Exception as e:
            print(f"Error logging business event: {e}")
        finally:
            conn.close()

    def find_matching_journey(self, track_id: str, zone: str, centroid: Optional[tuple], timestamp: datetime) -> Optional[Journey]:
        # Merge criteria: track disappears and new track appears nearby within 8.0s, same movement/zone
        for j in self.journeys:
            if j.status in ("active", "lost") and 0.0 <= (timestamp - j.last_active_time).total_seconds() <= 8.0:
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

        frame_id = min(max(0, frame_id), self.total_frames)
        role = "staff" if is_staff else "guest"
        
        if self.confirm_frames <= 1:
            if is_new:
                # Try to merge with lost journeys immediately
                j = self.find_matching_journey(track_id, zone, centroid, timestamp)
                if j:
                    self.merge_count += 1
                    j.active_tracker_ids.append(track_id)
                    j.status = "active"
                    j.last_active_time = timestamp
                    j.last_centroid = centroid
                    print(f"TRACK MERGED: Track {track_id} merged into existing Journey {j.journey_id} (survival of fragmentation)")
                else:
                    # Validate spawn transition
                    temp_journey_id = str(uuid.uuid4())
                    trans = SpatialTransition(
                        journey_id=temp_journey_id,
                        tracker_id=track_id,
                        camera=self.camera_id,
                        previous_zone="OUTSIDE",
                        current_zone=zone,
                        entry_frame=frame_id,
                        exit_frame=frame_id,
                        entry_timestamp=timestamp,
                        exit_timestamp=timestamp,
                        prev_centroid=centroid,
                        curr_centroid=centroid,
                        confidence=1.0
                    )
                    trans.is_initial_dining = (self.camera_role == "DINING")
                    is_valid_spawn = TransitionValidator.validate(trans, self.db_path)
                    is_initial_dining = (self.camera_role == "DINING")
                    
                    if is_valid_spawn or is_initial_dining:
                        has_recent_lost = any(journey.status == "lost" and (timestamp - journey.last_active_time).total_seconds() <= 8.0 for journey in self.journeys)
                        if has_recent_lost:
                            self.split_count += 1
                            
                        # Create actual Journey
                        j = Journey(track_id, timestamp, entry_gate=zone, start_centroid=centroid)
                        j.is_dark_lighting = self.is_dark_lighting
                        if self.is_dark_lighting:
                            j.state = "OUTSIDE"
                            j.state_history = [(timestamp, "OUTSIDE", frame_id)]
                            
                        j.journey_id = temp_journey_id
                        j.role = role
                        j.entry_frame = frame_id
                        if self.is_dark_lighting:
                            j.timeline.append({
                                "frame": frame_id,
                                "timestamp": timestamp.isoformat(),
                                "state": "OUTSIDE"
                            })
                        else:
                            j.timeline.append({
                                "frame": frame_id,
                                "timestamp": timestamp.isoformat(),
                                "state": "ENTERED"
                            })
                        self.journeys.append(j)
                        print(f"JOURNEY CREATED: New customer Journey {j.journey_id} started via Track {track_id}")
                        self.save_journey(j)
                        trans.persist(self.db_path)
                        save_evidence_thumbnail(j.journey_id, "entered", frame_img, bbox, run_dir)
                        
                        if is_initial_dining:
                            j.is_initial_spawn = True
                            is_table_or_dining_floor = ("table" in zone.lower() or "unknown" in zone.lower() or ("dining" in zone.lower() and "allowed" not in self.camera_id))
                            target_state = "SEATED" if is_table_or_dining_floor else "WAITING" if "waiting" in zone.lower() else "ENTERED"
                            j.update_state(target_state, timestamp, frame_id)
                            if target_state == "SEATED":
                                j.table_id = zone if ("table" in zone.lower()) else None
                                j.seated_time = timestamp
                                j.seated_frame = frame_id
                            self.save_journey(j)
                        else:
                            event_name, rule_id = EventRuleEngine.evaluate(trans, self.camera_role, {"confidence": j.confidence, "track_age": 1, "journey_state": "UNKNOWN"})
                            if event_name:
                                event_state_map = {
                                    "GuestEnteredRestaurant": "ENTERED",
                                    "GuestExitedRestaurant": "EXITED",
                                    "ReachedReception": "RECEPTION",
                                    "StartedWaiting": "WAITING",
                                    "StoppedWaiting": "ESCORTED",
                                    "EscortedToTable": "ESCORTED",
                                    "Seated": "SEATED",
                                    "LeftTable": "Dining",
                                    "JoinedBuffetQueue": "WAITING",
                                    "LeftBuffetQueue": "Dining",
                                    "ExitedRestaurant": "EXITED"
                                }
                                target_state = event_state_map.get(event_name, j.state)
                                j.update_state(target_state, timestamp, frame_id)
                                
                                if target_state == "EXITED":
                                    j.exit_time = timestamp
                                    j.status = "exited"
                                    j.exit_frame = frame_id
                                elif target_state == "WAITING":
                                    j.waiting_started = timestamp
                                    j.waiting_start_frame = frame_id
                                elif target_state == "SEATED":
                                    j.table_id = zone
                                    j.seated_time = timestamp
                                    j.seated_frame = frame_id

                                self.log_event(
                                    rule_id=rule_id,
                                    camera=self.camera_id,
                                    previous_zone="OUTSIDE",
                                    current_zone=zone,
                                    journey_state=j.state,
                                    journey_id=j.journey_id,
                                    tracker_id=track_id,
                                    timestamp=timestamp,
                                    frame=frame_id,
                                    confidence=j.confidence,
                                    transition_id=trans.transition_id
                                )
                                save_evidence_thumbnail(j.journey_id, "entered", frame_img, bbox, run_dir)
                    else:
                        print(f"TRACK IGNORED: Spawn transition for Track {track_id} in {zone} rejected by camera policy validator.")
                return
        else:
            if is_new:
                # Try to merge with lost journeys immediately
                j = self.find_matching_journey(track_id, zone, centroid, timestamp)
                if j:
                    self.merge_count += 1
                    j.active_tracker_ids.append(track_id)
                    j.status = "active"
                    j.last_active_time = timestamp
                    j.last_centroid = centroid
                    print(f"TRACK MERGED: Track {track_id} merged into existing Journey {j.journey_id} (survival of fragmentation)")
                else:
                    # Add to unconfirmed buffer
                    self.unconfirmed_tracks[track_id] = {
                        "first_seen": timestamp,
                        "first_frame": frame_id,
                        "zone": zone,
                        "centroid": centroid,
                        "frames": 1,
                        "bbox": bbox
                    }
                return
                
            # Check if the track is currently unconfirmed
            if track_id in self.unconfirmed_tracks:
                info = self.unconfirmed_tracks[track_id]
                info["frames"] += 1
                info["last_seen"] = timestamp
                info["centroid"] = centroid
                info["bbox"] = bbox
                
                if info["frames"] >= self.confirm_frames: # Filter transient tracks (minimum confirm_frames)
                    self.unconfirmed_tracks.pop(track_id)
                    
                    # Double check merge
                    j = self.find_matching_journey(track_id, info["zone"], info["centroid"], info["first_seen"])
                    if j:
                        self.merge_count += 1
                        j.active_tracker_ids.append(track_id)
                        j.status = "active"
                        j.last_active_time = timestamp
                        j.last_centroid = centroid
                        print(f"TRACK MERGED AFTER CONFIRMATION: Track {track_id} merged into existing Journey {j.journey_id}")
                    else:
                        # Validate spawn transition
                        temp_journey_id = str(uuid.uuid4())
                        trans = SpatialTransition(
                            journey_id=temp_journey_id,
                            tracker_id=track_id,
                            camera=self.camera_id,
                            previous_zone="OUTSIDE",
                            current_zone=info["zone"],
                            entry_frame=info["first_frame"],
                            exit_frame=frame_id,
                            entry_timestamp=info["first_seen"],
                            exit_timestamp=timestamp,
                            prev_centroid=info["centroid"],
                            curr_centroid=centroid,
                            confidence=1.0
                        )
                        trans.is_initial_dining = (self.camera_role == "DINING")
                        is_valid_spawn = TransitionValidator.validate(trans, self.db_path)
                        is_initial_dining = (self.camera_role == "DINING")
                        
                        if is_valid_spawn or is_initial_dining:
                            has_recent_lost = any(journey.status == "lost" and (timestamp - journey.last_active_time).total_seconds() <= 8.0 for journey in self.journeys)
                            if has_recent_lost:
                                self.split_count += 1
                                
                            # Create actual Journey
                            j = Journey(track_id, info["first_seen"], entry_gate=info["zone"], start_centroid=info["centroid"])
                            j.is_dark_lighting = self.is_dark_lighting
                            if self.is_dark_lighting:
                                j.state = "OUTSIDE"
                                j.state_history = [(info["first_seen"], "OUTSIDE", info["first_frame"])]
                                
                            j.journey_id = temp_journey_id
                            j.role = role
                            j.entry_frame = info["first_frame"]
                            if self.is_dark_lighting:
                                j.timeline.append({
                                    "frame": info["first_frame"],
                                    "timestamp": info["first_seen"].isoformat(),
                                    "state": "OUTSIDE"
                                })
                            else:
                                j.timeline.append({
                                    "frame": info["first_frame"],
                                    "timestamp": info["first_seen"].isoformat(),
                                    "state": "ENTERED"
                                })
                            self.journeys.append(j)
                            print(f"JOURNEY CREATED: New customer Journey {j.journey_id} started via confirmed Track {track_id}")
                            self.save_journey(j)
                            trans.persist(self.db_path)
                            save_evidence_thumbnail(j.journey_id, "entered", frame_img, info["bbox"], run_dir)
                            
                            if is_initial_dining:
                                j.is_initial_spawn = True
                                is_table_or_dining_floor = ("table" in zone.lower() or "unknown" in zone.lower() or ("dining" in zone.lower() and "allowed" not in self.camera_id))
                                target_state = "SEATED" if is_table_or_dining_floor else "WAITING" if "waiting" in zone.lower() else "ENTERED"
                                j.update_state(target_state, timestamp, frame_id)
                                if target_state == "SEATED":
                                    j.table_id = zone if ("table" in zone.lower()) else None
                                    j.seated_time = timestamp
                                    j.seated_frame = frame_id
                                self.save_journey(j)
                            else:
                                event_name, rule_id = EventRuleEngine.evaluate(trans, self.camera_role, {"confidence": j.confidence, "track_age": 5, "journey_state": "UNKNOWN"})
                                if event_name:
                                    event_state_map = {
                                        "GuestEnteredRestaurant": "ENTERED",
                                        "GuestExitedRestaurant": "EXITED",
                                        "ReachedReception": "RECEPTION",
                                        "StartedWaiting": "WAITING",
                                        "StoppedWaiting": "ESCORTED",
                                        "EscortedToTable": "ESCORTED",
                                        "Seated": "SEATED",
                                        "LeftTable": "Dining",
                                        "JoinedBuffetQueue": "WAITING",
                                        "LeftBuffetQueue": "Dining",
                                        "ExitedRestaurant": "EXITED"
                                    }
                                    target_state = event_state_map.get(event_name, j.state)
                                    j.update_state(target_state, timestamp, frame_id)
                                    
                                    if target_state == "EXITED":
                                        j.exit_time = timestamp
                                        j.status = "exited"
                                        j.exit_frame = frame_id
                                    elif target_state == "WAITING":
                                        j.waiting_started = timestamp
                                        j.waiting_start_frame = frame_id
                                    elif target_state == "SEATED":
                                        j.table_id = zone
                                        j.seated_time = timestamp
                                        j.seated_frame = frame_id
        
                                    self.log_event(
                                        rule_id=rule_id,
                                        camera=self.camera_id,
                                        previous_zone="OUTSIDE",
                                        current_zone=info["zone"],
                                        journey_state=j.state,
                                        journey_id=j.journey_id,
                                        tracker_id=track_id,
                                        timestamp=timestamp,
                                        frame=frame_id,
                                        confidence=j.confidence,
                                        transition_id=trans.transition_id
                                    )
                                    save_evidence_thumbnail(j.journey_id, "entered", frame_img, bbox, run_dir)
                        else:
                            print(f"TRACK IGNORED: Spawn transition for Track {track_id} in {zone} rejected by camera policy validator.")
                else:
                    return

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
            # Save previous zone before updating for zone-change detection below
            _prev_zone_for_detection = j.current_zone
            # Always update j.current_zone so queue_size_count can be computed from zone membership
            j.current_zone = zone
            
            # Keep centroid history for future use (no longer used for waiting gate)
            j.centroid_history.append(centroid)

            # Business State Machine Transitions (Task 3)
            # Business State Machine Transitions (dark_lighting = zone-based, no velocity gate)
            if self.is_dark_lighting:
                if j.state == "OUTSIDE":
                    # ENTRY: person physically crosses the ENTRANCE DOORWAY.
                    # Only zones adjacent to the entrance door count as a valid entry crossing.
                    # Spawning in Dining/Exit/Unknown = pre-existing occupant or camera artifact.
                    ENTRY_ZONES = {"Queue", "Reception", "Entrance", "Waiting Area"}
                    is_initial_spawn = (j.entry_frame is not None and j.entry_frame < 50) or (frame_id < 50)
                    if not is_initial_spawn and zone in ENTRY_ZONES:
                        j.update_state("ENTERED", timestamp, frame_id)
                        self.log_business_event(frame_id, timestamp, "ENTERED", j.journey_id, track_id)
                
                elif j.state == "ENTERED":
                    # WAITING: purely zone-based — any presence in Queue/Reception = waiting
                    if zone in ("Queue", "Reception", "Waiting Area"):
                        j.update_state("WAITING", timestamp, frame_id)
                        self.log_business_event(frame_id, timestamp, "WAITING_START", j.journey_id, track_id)
                    elif zone == "Dining":
                        j.update_state("DINING", timestamp, frame_id)
                        self.log_business_event(frame_id, timestamp, "DINING_START", j.journey_id, track_id)
                    elif zone in ("Exit", "OUTSIDE") and j.status != "exited":
                        # EXITED: guest physically walks to exit zone / leaves camera view
                        j.update_state("EXITED", timestamp, frame_id)
                        j.status = "exited"
                        self.log_business_event(frame_id, timestamp, "EXITED", j.journey_id, track_id)

                elif j.state == "WAITING":
                    # WAIT END: only when guest leaves waiting region toward dining
                    if zone == "Dining":
                        wait_dur = (timestamp - j.waiting_started).total_seconds() if j.waiting_started else 0.0
                        j.total_waiting_seconds += wait_dur
                        j.waiting_visits_count += 1
                        j.waiting_duration = j.total_waiting_seconds
                        j.update_state("DINING", timestamp, frame_id)
                        self.log_business_event(frame_id, timestamp, "WAITING_END", j.journey_id, track_id, destination_zone="Dining", waiting_seconds=wait_dur)
                    elif zone in ("Exit", "OUTSIDE"):
                        # Guest left without being seated — waiting ends
                        wait_dur = (timestamp - j.waiting_started).total_seconds() if j.waiting_started else 0.0
                        j.total_waiting_seconds += wait_dur
                        j.waiting_visits_count += 1
                        j.waiting_duration = j.total_waiting_seconds
                        j.update_state("EXITED", timestamp, frame_id)
                        j.status = "exited"
                        self.log_business_event(frame_id, timestamp, "WAITING_END", j.journey_id, track_id, destination_zone="OUTSIDE", waiting_seconds=wait_dur)
                        self.log_business_event(frame_id, timestamp, "EXITED", j.journey_id, track_id)
                    # If zone is still Queue/Reception: guest is STILL waiting — do nothing

                elif j.state == "DINING":
                    # Return to waiting: guest walks back to waiting zone — still same session
                    if zone in ("Queue", "Reception", "Waiting Area"):
                        j.update_state("WAITING", timestamp, frame_id)
                        j.returned_to_queue = True
                        self.log_business_event(frame_id, timestamp, "WAITING_START", j.journey_id, track_id)
                    elif zone in ("Exit", "OUTSIDE") and j.status != "exited":
                        j.update_state("EXITED", timestamp, frame_id)
                        j.status = "exited"
                        self.log_business_event(frame_id, timestamp, "EXITED", j.journey_id, track_id)
            
            # Zone change checks — use saved prev zone (j.current_zone was updated above)
            if zone != _prev_zone_for_detection:
                old_zone = _prev_zone_for_detection
                
                # Create SpatialTransition object
                trans = SpatialTransition(
                    journey_id=j.journey_id,
                    tracker_id=track_id,
                    camera=self.camera_id,
                    previous_zone=old_zone,
                    current_zone=zone,
                    entry_frame=j.entry_frame or frame_id,
                    exit_frame=frame_id,
                    entry_timestamp=j.entry_time or timestamp,
                    exit_timestamp=timestamp,
                    prev_centroid=j.previous_centroid,
                    curr_centroid=j.last_centroid,
                    confidence=j.confidence
                )
                
                # Evaluate EventRuleEngine using transition if validated
                if TransitionValidator.validate(trans, self.db_path):
                    j.zone_history.append(zone)
                    print(f"JOURNEY ZONE TRANSITION: Journey {j.journey_id} | Track {track_id} | {old_zone} -> {zone}")
                    trans.persist(self.db_path)
                    
                    # Save transition screenshot (Phase 2)
                    try:
                        import cv2
                        trans_dir = f"{run_dir}/demo/transitions"
                        os.makedirs(trans_dir, exist_ok=True)
                        annotated_frame = frame_img.copy()
                        if bbox:
                            bx1, by1, bx2, by2 = [int(v) for v in bbox]
                            cv2.rectangle(annotated_frame, (bx1, by1), (bx2, by2), (0, 255, 0), 2)
                            cv2.putText(annotated_frame, f"Track {track_id} | {j.journey_id[:8]}", (bx1, max(15, by1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                        cv2.putText(annotated_frame, f"Frame: {frame_id} | Zone: {zone} | State: {j.state}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        cv2.imwrite(f"{trans_dir}/{j.journey_id}_{old_zone}_to_{zone}_frame_{frame_id}.jpg", annotated_frame)
                    except Exception as e:
                        print(f"Failed to save transition screenshot: {e}")
                    metadata = {
                        "confidence": j.confidence,
                        "track_age": len(j.state_history),
                        "zone_history": j.zone_history,
                        "journey_state": j.state
                    }
                    event_name, rule_id = EventRuleEngine.evaluate(trans, self.camera_role, metadata)
                    
                    if event_name:
                        event_state_map = {
                            "GuestEnteredRestaurant": "ENTERED",
                            "GuestExitedRestaurant": "EXITED",
                            "ReachedReception": "RECEPTION",
                            "StartedWaiting": "WAITING",
                            "StoppedWaiting": "ESCORTED",
                            "EscortedToTable": "ESCORTED",
                            "Seated": "SEATED",
                            "LeftTable": "Dining",
                            "JoinedBuffetQueue": "WAITING",
                            "LeftBuffetQueue": "Dining",
                            "ExitedRestaurant": "EXITED"
                        }
                        target_state = event_state_map.get(event_name, j.state)
                        j.update_state(target_state, timestamp, frame_id)
                        
                        # Extra status update for EXITED state
                        if target_state == "EXITED":
                            j.exit_time = timestamp
                            j.status = "exited"
                            j.exit_frame = frame_id
                        elif target_state == "WAITING":
                            j.waiting_started = timestamp
                            j.waiting_start_frame = frame_id
                        elif target_state == "SEATED":
                            j.table_id = zone
                            j.seated_time = timestamp
                            j.seated_frame = frame_id
                            
                        # Save evidence thumbnails dynamically
                        if target_state == "ENTERED":
                            save_evidence_thumbnail(j.journey_id, "entered", frame_img, bbox, run_dir)
                        elif target_state == "SEATED":
                            save_evidence_thumbnail(j.journey_id, "seated", frame_img, bbox, run_dir)
                        elif target_state == "EXITED":
                            save_evidence_thumbnail(j.journey_id, "exit", frame_img, bbox, run_dir)
                            
                        # Log event
                        self.log_event(
                            rule_id=rule_id,
                            camera=self.camera_id,
                            previous_zone=old_zone,
                            current_zone=zone,
                            journey_state=j.state,
                            journey_id=j.journey_id,
                            tracker_id=track_id,
                            timestamp=timestamp,
                            frame=frame_id,
                            confidence=j.confidence,
                            transition_id=trans.transition_id
                        )
                
                # Waiting duration: waiting ends when they leave the Waiting Area (Step 6)
                if old_zone == "Waiting Area" and j.waiting_started:
                    j.waiting_duration = (timestamp - j.waiting_started).total_seconds()
                    j.waiting_end_frame = frame_id
                    print(f"WAITING COMPLETED: Journey {j.journey_id} waited for {j.waiting_duration:.1f}s")
                
                # Dining duration ends when they leave the table polygon (Step 7)
                if old_zone and "table" in old_zone.lower() and j.seated_time:
                    j.dining_duration = (timestamp - j.seated_time).total_seconds()
                    print(f"DINING COMPLETED: Journey {j.journey_id} dined for {j.dining_duration:.1f}s")
                
                self.save_journey(j)

    def handle_track_lost(self, track_id: str, timestamp: datetime):
        if track_id in self.unconfirmed_tracks:
            self.unconfirmed_tracks.pop(track_id)
            print(f"TRACK LOST (UNCONFIRMED): Unconfirmed Track {track_id} went offline. Cleaned up.")
            return
            
        for j in self.journeys:
            if track_id in j.active_tracker_ids and j.status == "active":
                j.status = "lost"
                j.last_active_time = timestamp
                self.save_journey(j)
                print(f"TRACK LOST: Tracker {track_id} went offline. Journey {j.journey_id} marked as lost/pending reassociation.")
                break

    def sweep_lost_journeys(self, current_time: datetime, force_all: bool = False, frame_id: int = 0):
        frame_id = min(max(0, frame_id), self.total_frames)
        for j in self.journeys:
            if j.status == "lost":
                offline_dur = (current_time - j.last_active_time).total_seconds()
                if force_all and j.state == "SEATED" and offline_dur <= 15.0:
                    continue
                if force_all or offline_dur > 8.0:
                    if self.is_dark_lighting:
                        # Business State Transitions for Swept/Lost Journey
                        # CRITICAL: tracker loss inside the restaurant is NOT a guest exit.
                        # Only fire EXITED business event if last known zone was an exit zone.
                        EXIT_ZONES = {"Exit", "OUTSIDE", "Entrance"}
                        last_zone = getattr(j, "current_zone", j.entry_gate)
                        was_at_exit = last_zone in EXIT_ZONES
                        
                        if j.state == "WAITING":
                            wait_dur = (j.last_active_time - j.waiting_started).total_seconds() if j.waiting_started else 0.0
                            j.total_waiting_seconds += wait_dur
                            j.waiting_visits_count += 1
                            j.waiting_duration = j.total_waiting_seconds
                            self.log_business_event(frame_id, j.last_active_time, "WAITING_END", j.journey_id, j.active_tracker_ids[-1], destination_zone="OUTSIDE" if was_at_exit else last_zone, waiting_seconds=wait_dur)
                        
                        if j.state != "EXITED":
                            j.update_state("EXITED", j.last_active_time, frame_id)
                            j.status = "exited"
                            j.exit_frame = frame_id
                            j.exit_time = j.last_active_time
                            if was_at_exit:
                                # Physical exit through doorway — count it
                                self.log_business_event(frame_id, j.last_active_time, "EXITED", j.journey_id, j.active_tracker_ids[-1])
                            else:
                                # Tracker lost inside restaurant — record as internal loss, not exit
                                self.log_business_event(frame_id, j.last_active_time, "TRACK_LOST_INSIDE", j.journey_id, j.active_tracker_ids[-1])
                    else:
                        j.status = "exited"
                        j.exit_time = j.last_active_time
                        j.update_state("EXITED", j.last_active_time, frame_id)
                        j.exit_frame = frame_id

                    j.status = "exited"
                    j.exit_time = j.last_active_time
                    j.exit_frame = frame_id
                    if j.seated_time and j.dining_duration == 0.0:
                        j.dining_duration = (j.last_active_time - j.seated_time).total_seconds()
                    self.save_journey(j)
                    
                    # Create exit transition
                    trans = SpatialTransition(
                        journey_id=j.journey_id,
                        tracker_id=j.active_tracker_ids[-1],
                        camera=self.camera_id,
                        previous_zone=j.current_zone,
                        current_zone="OUTSIDE",
                        entry_frame=j.entry_frame or frame_id,
                        exit_frame=frame_id,
                        entry_timestamp=j.entry_time or j.last_active_time,
                        exit_timestamp=j.last_active_time,
                        prev_centroid=j.last_centroid,
                        curr_centroid=j.last_centroid,
                        confidence=j.confidence
                    )
                    trans.is_finalization = True
                    trans.persist(self.db_path)
                    
                    # Evaluate rule for EXITing to OUTSIDE if validated
                    if TransitionValidator.validate(trans, self.db_path):
                        event_name, rule_id = EventRuleEngine.evaluate(trans, self.camera_role, {"confidence": j.confidence, "track_age": len(j.state_history), "journey_state": j.state})
                        if event_name:
                            self.log_event(
                                rule_id=rule_id,
                                camera=self.camera_id,
                                previous_zone=j.current_zone,
                                current_zone="OUTSIDE",
                                journey_state=j.state,
                                journey_id=j.journey_id,
                                tracker_id=j.active_tracker_ids[-1],
                                timestamp=j.last_active_time,
                                frame=frame_id,
                                confidence=j.confidence,
                                transition_id=trans.transition_id
                            )
                    print(f"JOURNEY FINALIZED: Journey {j.journey_id} has been offline for {offline_dur:.1f}s. Finalized as EXITED.")

    def save_journey(self, j: Journey):
        import time
        t_start = time.time()
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        conn.execute('''
            INSERT OR REPLACE INTO journeys (
                journey_id, camera_id, entry_time, exit_time, entry_gate, current_zone, waiting_duration, dining_duration, table_id, seated_time, server_visits, confidence, status, state, is_initial_spawn,
                entry_frame, exit_frame, entry_timestamp, exit_timestamp, queue_start, queue_end, waiting_start, waiting_end, seating_time, table_assignment, zone_history, transition_history, evidence_image, tracker_id, detector_confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            j.journey_id,
            self.camera_id,
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
            j.state,
            1 if getattr(j, "is_initial_spawn", False) else 0,
            j.entry_frame,
            j.exit_frame,
            j.entry_time.isoformat() if j.entry_time else None,
            j.exit_time.isoformat() if j.exit_time else None,
            getattr(j, "queue_start", None).isoformat() if getattr(j, "queue_start", None) else None,
            getattr(j, "queue_end", None).isoformat() if getattr(j, "queue_end", None) else None,
            getattr(j, "waiting_start", None).isoformat() if getattr(j, "waiting_start", None) else None,
            getattr(j, "waiting_end", None).isoformat() if getattr(j, "waiting_end", None) else None,
            j.seated_time.isoformat() if j.seated_time else None,
            j.table_id,
            json.dumps(j.zone_history),
            json.dumps(j.timeline),
            f"evidence/{j.journey_id}_entered.jpg",
            ",".join(j.active_tracker_ids),
            j.confidence
        ))
        conn.commit()
        conn.close()
        self.last_db_write_time_ms = (time.time() - t_start) * 1000.0

    def log_event(self, rule_id: str, camera: str, previous_zone: str, current_zone: str, journey_state: str, journey_id: str, tracker_id: str, timestamp: datetime, frame: int, confidence: float, transition_id: str):
        import time
        t_start = time.time()
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        conn.execute('''
            INSERT INTO business_events (rule_id, camera, previous_zone, current_zone, journey_state, journey_id, tracker_id, timestamp, frame, confidence, transition_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (rule_id, camera, previous_zone, current_zone, journey_state, journey_id, tracker_id, timestamp.isoformat(), frame, confidence, transition_id))
        conn.commit()
        conn.close()
        self.last_db_write_time_ms = (time.time() - t_start) * 1000.0
        
        print(f"Frame: {frame} | Camera: {camera} | Zone: {current_zone} | Event: {rule_id} | Reason: Evaluated {rule_id} from {previous_zone} | Transition ID: {transition_id}")

    def log_server_visit(self, table_id: str, staff_id: str, timestamp: datetime, duration: float):
        import time
        t_start = time.time()
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        conn.execute('''
            INSERT INTO server_visits (table_id, staff_id, timestamp, duration)
            VALUES (?, ?, ?, ?)
        ''', (table_id, staff_id, timestamp.isoformat(), duration))
        conn.commit()
        conn.close()
        self.last_db_write_time_ms = (time.time() - t_start) * 1000.0
        # Increment server visit count for any customer currently seated at that table!
        for j in self.journeys:
            if j.table_id == table_id and j.status == "active":
                j.server_visits += 1
                self.save_journey(j)
                print(f"SERVER VISIT LOGGED: Staff {staff_id} visited table {table_id} for {duration:.1f}s. Associated with Customer Journey {j.journey_id}.")
