import uuid
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any, Union
from restaurant_analytics.event_engine import EventEngine, BusinessEvent
from restaurant_analytics.visit_state import StateEngine, StateTransition

def load_system_config():
    try:
        with open("configs/system.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "zone_transition_confirmation": 3.0,
            "lost_visit_timeout": 30.0,
            "appearance_similarity": 0.8,
            "merge_threshold": 0.85,
            "metric_smoothing": 0.2
        }

CONFIG = load_system_config()

class Visit:
    """
    The canonical business representation of a person's journey through the restaurant.
    A Visit object owns its timeline, state, metrics, and lifecycle.
    """
    def __init__(self, person_id: str, role: str = "guest", entry_time: datetime = datetime.now(), camera_id: str = "default"):
        self.visit_id = str(uuid.uuid4())
        self.person_id = person_id
        self.role = role
        self.entry_time = entry_time
        self.exit_time: Optional[datetime] = None
        self.camera_id = camera_id
        
        self.current_zone: Optional[str] = None
        self.zone_entry_time: Optional[datetime] = entry_time
        
        # Hysteresis fields
        self.pending_zone: Optional[str] = None
        self.pending_zone_entry_time: Optional[datetime] = None
        
        self.last_centroid: Optional[tuple] = None
        self.previous_centroid: Optional[tuple] = None
        
        # Phase 4: State Engine attributes
        self.current_state: str = "UNKNOWN"
        self.previous_state: str = "UNKNOWN"
        self.last_transition_time: datetime = entry_time
        self.state_confidence: float = 1.0
        self.state_history: List[StateTransition] = []
        self.events: List[BusinessEvent] = []
        
        # Legacy metrics dictionary
        self.metrics: Dict[str, Any] = {}
        
        # Debounce and lock flags for business events
        self.guest_entered_fired = False
        self.guest_exited_fired = False
        self.waiting_fired = False
        self.seated_fired = False
        self.left_table_fired = False
        
    @property
    def overall_confidence(self) -> float:
        """
        Calculates a modular weighted confidence based on tracking, zone, and state stability.
        """
        tracking_conf = self.metrics.get("tracking_confidence", 0.90)
        state_conf = self.state_confidence
        zone_conf = self.metrics.get("zone_confidence", 1.0)
        
        weights = {"tracking": 0.5, "state": 0.4, "zone": 0.1}
        return (tracking_conf * weights["tracking"]) + (state_conf * weights["state"]) + (zone_conf * weights["zone"])
        
    @property
    def timeline(self) -> List[Dict[str, Any]]:
        """
        Dynamically derived timeline combining state transitions and business events.
        """
        items = []
        for e in self.events:
            items.append({
                "type": "event",
                "timestamp": e.timestamp,
                "event_type": e.event_type.value,
                "zone": e.zone
            })
        for s in self.state_history:
            items.append({
                "type": "state",
                "timestamp": s.timestamp,
                "state": s.new_state,
                "reason": s.reason
            })
        items.sort(key=lambda x: x["timestamp"])
        return items

    def update_zone(self, new_zone: Optional[str], timestamp: datetime):
        """Updates current zone and records the time of entry."""
        if self.current_zone != new_zone:
            self.current_zone = new_zone
            self.zone_entry_time = timestamp
            self.pending_zone = None
            self.pending_zone_entry_time = None

    def update_state(self, new_state: str, timestamp: datetime):
        if self.current_state != new_state:
            self.timeline.append({
                "type": "state_change",
                "from_state": self.current_state,
                "to_state": new_state,
                "timestamp": timestamp.isoformat()
            })
            self.current_state = new_state
            
    def update_role(self, new_role: str, timestamp: datetime):
        if self.role != new_role:
            self.timeline.append({
                "type": "role_change",
                "from_role": self.role,
                "to_role": new_role,
                "timestamp": timestamp.isoformat()
            })
            self.role = new_role

    def add_event(self, event_name: str, event_data: dict, timestamp: datetime):
        """Add a semantic business event to the visit."""
        self.events.append({
            "name": event_name,
            "data": event_data,
            "timestamp": timestamp.isoformat()
        })
        
    def end_visit(self, timestamp: datetime):
        self.exit_time = timestamp
        self.metrics["duration_seconds"] = (self.exit_time - self.entry_time).total_seconds()
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "visit_id": self.visit_id,
            "person_id": self.person_id,
            "role": self.role,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "current_zone": self.current_zone,
            "current_state": self.current_state,
            "timeline": self.timeline,
            "events": self.events,
            "metrics": self.metrics,
        }


class VisitManager:
    """
    Manages the lifecycle of active visits.
    Acts as the bridge between raw observations (track IDs) and business objects (Visits).
    Integrates Zone Hysteresis and Lost Visit Caching for production reliability.
    """
    def __init__(self, event_engine: Optional[EventEngine] = None, state_engine: Optional[StateEngine] = None):
        self.active_visits: Dict[str, Visit] = {}
        self.lost_visit_cache: Dict[str, Visit] = {}
        
        self.event_engine = event_engine or EventEngine()
        self.state_engine = state_engine or StateEngine(event_engine=self.event_engine)
        
    def handle_track_start(self, track_id: str, timestamp: datetime, role: str = "guest", camera_id: str = "default", centroid: Optional[tuple] = None) -> Visit:
        # Check lost visit cache for soft-reassociation
        best_match = None
        best_score = 0.0
        
        for v in list(self.lost_visit_cache.values()):
            if (timestamp - v.exit_time).total_seconds() > CONFIG["lost_visit_timeout"]:
                continue
                
            # Heuristic identity confidence scoring
            score = 0.5  # Base temporal match
            if centroid and v.last_centroid:
                dist = ((centroid[0] - v.last_centroid[0])**2 + (centroid[1] - v.last_centroid[1])**2)**0.5
                if dist < 120:  # Spatial radius
                    score += 0.4
                    
            if score >= CONFIG["merge_threshold"]:
                if score > best_score:
                    best_score = score
                    best_match = v

        if best_match:
            # Reassociate
            visit = best_match
            visit.person_id = track_id
            visit.exit_time = None
            if centroid: visit.last_centroid = centroid
            self.active_visits[track_id] = visit
            del self.lost_visit_cache[visit.visit_id]
            return visit

        # No match found, create new
        visit = Visit(person_id=track_id, role=role, entry_time=timestamp, camera_id=camera_id)
        if centroid: visit.last_centroid = centroid
        
        self.active_visits[track_id] = visit
        self.state_engine.initialize_visit(visit, timestamp)
        
        event = self.event_engine.publish_visit_created(visit.visit_id, visit.person_id, track_id, timestamp, camera_id, role)
        if event:
            visit.events.append(event)
            self.state_engine.process_event(visit, event)
            
        return visit

    def get_visit(self, track_id: str) -> Optional[Visit]:
        return self.active_visits.get(track_id)

    def update_visit_zone(self, track_id: str, new_zone: Optional[str], timestamp: datetime, centroid: Optional[tuple] = None):
        visit = self.get_visit(track_id)
        if not visit: return
        
        if centroid:
            visit.previous_centroid = visit.last_centroid
            visit.last_centroid = centroid

        if visit.current_zone == new_zone:
            visit.pending_zone = None
            visit.pending_zone_entry_time = None
            return

        if visit.pending_zone != new_zone:
            visit.pending_zone = new_zone
            visit.pending_zone_entry_time = timestamp

    def update_visit_role(self, track_id: str, new_role: str, timestamp: datetime):
        visit = self.get_visit(track_id)
        if visit and visit.role != new_role:
            visit.update_role(new_role, timestamp)
            
    def evaluate_temporal_states(self, current_timestamp: datetime):
        """Called periodically by the pipeline to trigger time-based state transitions and hysteresis processing."""
        for track_id, visit in self.active_visits.items():
            # Process Zone Hysteresis
            if visit.pending_zone is not None and visit.pending_zone_entry_time:
                dwell_time = (current_timestamp - visit.pending_zone_entry_time).total_seconds()
                if dwell_time >= CONFIG["zone_transition_confirmation"]:
                    old_zone = visit.current_zone
                    new_zone = visit.pending_zone
                    visit.update_zone(new_zone, current_timestamp)
                    
                    # 1. Entrance crossing GuestEntered
                    if old_zone != "Entrance" and new_zone == "Entrance":
                        if not visit.guest_entered_fired:
                            visit.guest_entered_fired = True
                            from restaurant_analytics.event_engine import BusinessEvent, EventType
                            ent_ev = BusinessEvent(
                                visit_id=visit.visit_id, person_id=visit.person_id, track_id=track_id,
                                event_type=EventType.GuestEntered, timestamp=current_timestamp,
                                zone="Entrance", camera=visit.camera_id
                            )
                            self.event_engine.publish(ent_ev)
                            visit.events.append(ent_ev)
                            self.state_engine.process_event(visit, ent_ev)
                            prev_xy = visit.previous_centroid or (0,0)
                            curr_xy = visit.last_centroid or (0,0)
                            print(f"ENTRY GATE CROSSED | Track {track_id} | Previous {prev_xy} | Current {curr_xy} | Gate Entrance | Event GuestEntered")

                    # 2. Exit crossing GuestExited
                    elif old_zone != "Exit" and new_zone == "Exit":
                        if not visit.guest_exited_fired and visit.guest_entered_fired:
                            visit.guest_exited_fired = True
                            from restaurant_analytics.event_engine import BusinessEvent, EventType
                            ex_ev = BusinessEvent(
                                visit_id=visit.visit_id, person_id=visit.person_id, track_id=track_id,
                                event_type=EventType.GuestExited, timestamp=current_timestamp,
                                zone="Exit", camera=visit.camera_id
                            )
                            self.event_engine.publish(ex_ev)
                            visit.events.append(ex_ev)
                            self.state_engine.process_event(visit, ex_ev)
                            prev_xy = visit.previous_centroid or (0,0)
                            curr_xy = visit.last_centroid or (0,0)
                            print(f"EXIT GATE CROSSED | Track {track_id} | Previous {prev_xy} | Current {curr_xy} | Gate Exit | Event GuestExited")

                    # 3. Waiting Area crossing
                    elif new_zone == "Waiting Area":
                        if not visit.waiting_fired:
                            visit.waiting_fired = True
                            from restaurant_analytics.event_engine import BusinessEvent, EventType
                            w_ev = BusinessEvent(
                                visit_id=visit.visit_id, person_id=visit.person_id, track_id=track_id,
                                event_type=EventType.WaitingStarted, timestamp=current_timestamp,
                                zone="Waiting Area", camera=visit.camera_id
                            )
                            self.event_engine.publish(w_ev)
                            visit.events.append(w_ev)
                            self.state_engine.process_event(visit, w_ev)
                            print(f"WAITING ZONE ENTERED | Track {track_id} | Event Waiting")

                    # 4. Table 101 Seated crossing
                    elif new_zone == "Table 101":
                        if not visit.seated_fired:
                            visit.seated_fired = True
                            from restaurant_analytics.event_engine import BusinessEvent, EventType
                            s_ev = BusinessEvent(
                                visit_id=visit.visit_id, person_id=visit.person_id, track_id=track_id,
                                event_type=EventType.DiningStarted, timestamp=current_timestamp,
                                zone="Table 101", camera=visit.camera_id
                            )
                            self.event_engine.publish(s_ev)
                            visit.events.append(s_ev)
                            self.state_engine.process_event(visit, s_ev)
                            print(f"TABLE POLYGON ENTERED | Track {track_id} | Event Seated")

                    # 5. Table 101 LeftTable crossing
                    if old_zone == "Table 101" and new_zone != "Table 101":
                        if not visit.left_table_fired and visit.seated_fired:
                            visit.left_table_fired = True
                            from restaurant_analytics.event_engine import BusinessEvent, EventType
                            l_ev = BusinessEvent(
                                visit_id=visit.visit_id, person_id=visit.person_id, track_id=track_id,
                                event_type=EventType.LeftTable, timestamp=current_timestamp,
                                zone="Table 101", camera=visit.camera_id
                            )
                            self.event_engine.publish(l_ev)
                            visit.events.append(l_ev)
                            self.state_engine.process_event(visit, l_ev)
                            print(f"TABLE POLYGON EXITED | Track {track_id} | Event LeftTable")

                    events = self.event_engine.publish_zone_change(
                        visit_id=visit.visit_id, person_id=visit.person_id, track_id=track_id, 
                        timestamp=current_timestamp, camera=visit.camera_id, 
                        from_zone=old_zone, to_zone=new_zone
                    )
                    if events:
                        for event in events:
                            visit.events.append(event)
                            self.state_engine.process_event(visit, event)
                            
            # Process state engine temporal evaluations
            self.state_engine.evaluate_temporal_state(visit, current_timestamp)
            
        # Clean up lost visits permanently and emit close events
        for v in list(self.lost_visit_cache.values()):
            if v.exit_time and (current_timestamp - v.exit_time).total_seconds() > CONFIG["lost_visit_timeout"]:
                # Permanently close visit
                if v.current_zone:
                    events = self.event_engine.publish_zone_change(
                        visit_id=v.visit_id, person_id=v.person_id, track_id=v.person_id, 
                        timestamp=v.exit_time, camera=v.camera_id, 
                        from_zone=v.current_zone, to_zone=None
                    )
                    if events:
                        for event in events:
                            v.events.append(event)
                            self.state_engine.process_event(v, event)
                            
                duration = v.metrics.get("duration_seconds", 0.0)
                served = v.metrics.get("served", False)
                closed_events = self.event_engine.publish_visit_closed(
                    visit_id=v.visit_id, person_id=v.person_id, track_id=v.person_id, 
                    timestamp=v.exit_time, camera=v.camera_id, role=v.role, duration=duration, served=served
                )
                if closed_events:
                    for event in closed_events:
                        v.events.append(event)
                        self.state_engine.process_event(v, event)
                del self.lost_visit_cache[v.visit_id]
        
    def handle_track_end(self, track_id: str, timestamp: datetime) -> Optional[Visit]:
        visit = self.active_visits.get(track_id)
        if visit:
            visit.end_visit(timestamp)
            self.lost_visit_cache[visit.visit_id] = visit
            del self.active_visits[track_id]
            return visit
        return None
