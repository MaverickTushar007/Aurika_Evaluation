from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid

from restaurant_analytics.persistence_adapter import PersistenceAdapter

class EventType(Enum):
    GuestEntered = "GuestEntered"
    GuestExited = "GuestExited"
    ZoneEntered = "enter_zone"   # Keeps DB backward compatibility
    ZoneExited = "exit_zone"     # Keeps DB backward compatibility
    Served = "served"
    Abandoned = "abandoned"
    StaffShift = "staff_shift"
    WaitingStarted = "WaitingStarted"
    WaitingEnded = "WaitingEnded"
    GreetingStarted = "GreetingStarted"
    GreetingEnded = "GreetingEnded"
    Escorted = "Escorted"
    DiningStarted = "DiningStarted"
    DiningEnded = "DiningEnded"
    TableAssigned = "TableAssigned"
    HostIdle = "HostIdle"
    QueueStarted = "QueueStarted"
    QueueEnded = "QueueEnded"

@dataclass
class BusinessEvent:
    visit_id: str
    person_id: str
    track_id: str
    event_type: EventType
    timestamp: datetime
    zone: Optional[str] = None
    camera: Optional[str] = None
    confidence: Optional[float] = None
    source_module: str = "EventEngine"
    metadata: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class SystemDiagnosticEvent:
    event_type: str
    visit_id: Optional[str]
    timestamp: datetime
    reason: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

class EventEngine:
    """
    Listens to Visit lifecycle changes and generates semantic BusinessEvents.
    The ONLY module allowed to persist events to the database.
    Implements deduplication caching for production reliability.
    """
    def __init__(self, persistence_adapter: Optional[PersistenceAdapter] = None):
        self.persistence = persistence_adapter or PersistenceAdapter()
        self.recent_events_cache = {}  # (visit_id, event_type) -> datetime
        
    def publish(self, event: BusinessEvent) -> Optional[BusinessEvent]:
        """Core publishing method that delegates to Persistence Adapter and deduplicates."""
        cache_key = (event.visit_id, event.event_type.value)
        last_time = self.recent_events_cache.get(cache_key)
        
        # Deduplicate if same event happened within 5 seconds
        if last_time and (event.timestamp - last_time).total_seconds() < 5.0:
            return None
            
        self.recent_events_cache[cache_key] = event.timestamp
        self.persistence.save_event(event)
        return event

    def publish_diagnostic(self, event_type: str, visit_id: Optional[str], timestamp: datetime, reason: str, confidence: float = 1.0, metadata: Dict[str, Any] = None):
        """Publishes a system diagnostic event (e.g. IllegalStateTransition)."""
        diagnostic = SystemDiagnosticEvent(
            event_type=event_type,
            visit_id=visit_id,
            timestamp=timestamp,
            reason=reason,
            confidence=confidence,
            metadata=metadata or {}
        )
        self.persistence.save_event(diagnostic)
        
    def publish_zone_change(self, visit_id: str, person_id: str, track_id: str, timestamp: datetime, camera: str, from_zone: Optional[str], to_zone: Optional[str]) -> List[BusinessEvent]:
        """Translates a zone boundary crossing into specific zone events."""
        events = []
        if from_zone:
            event = BusinessEvent(
                visit_id=visit_id, person_id=person_id, track_id=track_id,
                event_type=EventType.ZoneExited, timestamp=timestamp,
                zone=from_zone, camera=camera
            )
            pub = self.publish(event)
            if pub: events.append(pub)
        
        if to_zone:
            event = BusinessEvent(
                visit_id=visit_id, person_id=person_id, track_id=track_id,
                event_type=EventType.ZoneEntered, timestamp=timestamp,
                zone=to_zone, camera=camera
            )
            pub = self.publish(event)
            if pub: events.append(pub)
        return events

    def publish_visit_created(self, visit_id: str, person_id: str, track_id: str, timestamp: datetime, camera: str, role: str) -> Optional[BusinessEvent]:
        """Emitted when a new Visit entity is instantiated."""
        if role == "guest":
            event = BusinessEvent(
                visit_id=visit_id, person_id=person_id, track_id=track_id,
                event_type=EventType.GuestEntered, timestamp=timestamp,
                camera=camera
            )
            return self.publish(event)
        return None
            
    def publish_visit_closed(self, visit_id: str, person_id: str, track_id: str, timestamp: datetime, camera: str, role: str, duration: float, served: bool = False) -> List[BusinessEvent]:
        """Emitted when a Visit terminates."""
        events = []
        if role == "staff":
            event_type = EventType.StaffShift
        else:
            event_type = EventType.Served if served else EventType.Abandoned
            
        event = BusinessEvent(
            visit_id=visit_id, person_id=person_id, track_id=track_id,
            event_type=event_type, timestamp=timestamp,
            camera=camera, metadata={"duration": duration}
        )
        pub = self.publish(event)
        if pub: events.append(pub)
        
        # Also emit GuestExited explicitly if needed, but for legacy compatibility we prioritize Served/Abandoned
        if role == "guest":
            guest_event = BusinessEvent(
                visit_id=visit_id, person_id=person_id, track_id=track_id,
                event_type=EventType.GuestExited, timestamp=timestamp,
                camera=camera, metadata={"duration": duration}
            )
            pub = self.publish(guest_event)
            if pub: events.append(pub)
            
        return events
            
    def publish_state_change(self, visit_id: str, person_id: str, track_id: str, timestamp: datetime, camera: str, from_state: str, to_state: str) -> Optional[BusinessEvent]:
        """Reserved for Phase 5 (State Machine) integration."""
        pass
