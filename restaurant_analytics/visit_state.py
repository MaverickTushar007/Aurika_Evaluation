from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid
import logging

from restaurant_analytics.event_engine import BusinessEvent

logger = logging.getLogger("StateEngine")

class GuestState(Enum):
    UNKNOWN = "UNKNOWN"
    ENTERING = "ENTERING"
    GREETING = "GREETING"
    WAITING = "WAITING"
    ESCORTED = "ESCORTED"
    SEATED = "SEATED"
    DINING = "DINING"
    PAYING = "PAYING"
    EXITING = "EXITING"
    EXITED = "EXITED"

class StaffState(Enum):
    UNKNOWN = "UNKNOWN"
    IDLE = "IDLE"
    GREETING = "GREETING"
    ESCORTING = "ESCORTING"
    SERVING = "SERVING"
    KITCHEN = "KITCHEN"
    CLEANING = "CLEANING"
    OFF_SHIFT = "OFF_SHIFT"

@dataclass
class StateTransition:
    transition_id: str
    visit_id: str
    timestamp: datetime
    previous_state: str
    new_state: str
    reason: str
    confidence: float = 1.0
    source_event_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class StateTransitionValidator:
    """Validates state transitions to prevent illegal state changes."""
    
    GUEST_VALID_TRANSITIONS = {
        GuestState.UNKNOWN: {GuestState.ENTERING, GuestState.WAITING, GuestState.SEATED}, # Can start anywhere if tracking lost
        GuestState.ENTERING: {GuestState.GREETING, GuestState.WAITING, GuestState.SEATED, GuestState.EXITING},
        GuestState.GREETING: {GuestState.WAITING, GuestState.ESCORTED, GuestState.SEATED, GuestState.EXITING},
        GuestState.WAITING: {GuestState.ESCORTED, GuestState.SEATED, GuestState.EXITING},
        GuestState.ESCORTED: {GuestState.SEATED, GuestState.DINING},
        GuestState.SEATED: {GuestState.DINING, GuestState.PAYING, GuestState.EXITING},
        GuestState.DINING: {GuestState.PAYING, GuestState.EXITING},
        GuestState.PAYING: {GuestState.EXITING},
        GuestState.EXITING: {GuestState.EXITED},
        GuestState.EXITED: set()
    }
    
    @classmethod
    def can_transition(cls, current_state: GuestState, target_state: GuestState) -> bool:
        if current_state == target_state:
            return False # No-op
        valid_next = cls.GUEST_VALID_TRANSITIONS.get(current_state, set())
        return target_state in valid_next

class StateEngine:
    """
    The canonical source for understanding what a Visit is doing RIGHT NOW.
    Interprets Business Events and temporal conditions into State.
    """
    
    def __init__(self, event_engine: Optional[Any] = None):
        # Configuration for temporal rules
        self.WAITING_THRESHOLD_SECONDS = 30.0
        self.event_engine = event_engine
        
    def initialize_visit(self, visit: Any, timestamp: datetime):
        """Sets the initial state for a newly created Visit."""
        state = GuestState.ENTERING.value if visit.role == "guest" else StaffState.IDLE.value
        visit.current_state = state
        visit.previous_state = GuestState.UNKNOWN.value if visit.role == "guest" else StaffState.UNKNOWN.value
        visit.last_transition_time = timestamp
        
        transition = StateTransition(
            transition_id=str(uuid.uuid4()),
            visit_id=visit.visit_id,
            timestamp=timestamp,
            previous_state=visit.previous_state,
            new_state=state,
            reason="Visit Created"
        )
        visit.state_history.append(transition)

    def validate_transition(self, visit: Any, target_state: str) -> bool:
        try:
            if visit.role == "guest":
                current_enum = GuestState(visit.current_state)
                target_enum = GuestState(target_state)
                return StateTransitionValidator.can_transition(current_enum, target_enum)
            return True # Simplified staff validation for now
        except ValueError:
            return False
            
    def transition(self, visit: Any, target_state: str, timestamp: datetime, reason: str, source_event: Optional[BusinessEvent] = None, confidence: float = 1.0) -> bool:
        """Attempts to transition a visit to a new state. Returns True if successful."""
        if visit.current_state == target_state:
            return False
            
        if not self.validate_transition(visit, target_state):
            reason_msg = f"Illegal state transition rejected: {visit.current_state} -> {target_state} (Reason: {reason})"
            logger.warning(
                f"Illegal state transition rejected for visit {visit.visit_id}: "
                f"{visit.current_state} -> {target_state} (Reason: {reason})"
            )
            if self.event_engine:
                self.event_engine.publish_diagnostic(
                    event_type="IllegalStateTransition",
                    visit_id=visit.visit_id,
                    timestamp=timestamp,
                    reason=reason_msg,
                    confidence=confidence,
                    metadata={"current_state": visit.current_state, "attempted_state": target_state}
                )
            return False
            
        # Execute transition
        visit.previous_state = visit.current_state
        visit.current_state = target_state
        visit.last_transition_time = timestamp
        visit.state_confidence = confidence
        
        transition = StateTransition(
            transition_id=str(uuid.uuid4()),
            visit_id=visit.visit_id,
            timestamp=timestamp,
            previous_state=visit.previous_state,
            new_state=target_state,
            reason=reason,
            confidence=confidence,
            source_event_id=source_event.event_id if source_event else None
        )
        visit.state_history.append(transition)
        return True

    def process_event(self, visit: Any, event: BusinessEvent):
        """Interprets a BusinessEvent immediately."""
        if visit.role != "guest":
            return
            
        if event.event_type.value == "enter_zone":
            zone = event.zone.lower() if event.zone else ""
            if "dining" in zone or "table" in zone:
                self.transition(visit, GuestState.SEATED.value, event.timestamp, reason="Entered Dining Zone", source_event=event)
            elif "exit" in zone or "door" in zone:
                self.transition(visit, GuestState.EXITING.value, event.timestamp, reason="Entered Exit Zone", source_event=event)
                
        elif event.event_type.value == "GuestExited":
            self.transition(visit, GuestState.EXITED.value, event.timestamp, reason="Visit Closed", source_event=event)

    def evaluate_temporal_state(self, visit: Any, current_timestamp: datetime):
        """
        Evaluates temporal rules (e.g., waiting for >30s).
        Designed to be called periodically (e.g. every frame or every N seconds).
        """
        if visit.role != "guest" or visit.current_state == GuestState.WAITING.value:
            return
            
        # If the guest is in the Waiting area, check how long they've been there
        if visit.current_zone and "waiting" in visit.current_zone.lower():
            # Time since they entered the zone
            # We assume last_transition_time approximates zone entry if entering zone was the last major state change,
            # but ideally Visit should track zone_entry_time explicitly. 
            # We will use visit.zone_entry_time which we will add to Visit.
            zone_entry = getattr(visit, "zone_entry_time", visit.last_transition_time)
            
            if zone_entry:
                dwell_time = (current_timestamp - zone_entry).total_seconds()
                if dwell_time >= self.WAITING_THRESHOLD_SECONDS:
                    self.transition(
                        visit, 
                        GuestState.WAITING.value, 
                        current_timestamp, 
                        reason=f"Dwelled in waiting zone for {dwell_time:.1f}s"
                    )
