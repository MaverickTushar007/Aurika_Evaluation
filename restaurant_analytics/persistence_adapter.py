import sqlite3
from typing import Any

class PersistenceAdapter:
    """
    Abstracts storage operations for the Event Engine.
    Currently uses SQLite for backward compatibility, but can be swapped out later.
    """
    def __init__(self, db_path: str = "db/customer_intel.db"):
        self.db_path = db_path
        self._init_diagnostics_table()
        
    def _init_diagnostics_table(self):
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS system_diagnostics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    visit_id TEXT,
                    timestamp TEXT,
                    reason TEXT,
                    confidence REAL,
                    metadata TEXT
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[PersistenceAdapter] Error initializing diagnostics table: {e}")
            
    def save_event(self, event: Any) -> bool:
        """
        Saves a BusinessEvent to the persistence layer.
        event is assumed to be a BusinessEvent object.
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            cursor = conn.cursor()
            
            # Check if event is a SystemDiagnosticEvent (using class name to avoid circular imports)
            if type(event).__name__ == 'SystemDiagnosticEvent':
                import json
                cursor.execute(
                    "INSERT INTO system_diagnostics (event_type, visit_id, timestamp, reason, confidence, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                    (event.event_type, event.visit_id, event.timestamp.isoformat(), event.reason, event.confidence, json.dumps(event.metadata))
                )
                conn.commit()
                conn.close()
                return True
                
            # Map BusinessEvent to legacy schema
            # Legacy Schema: id (auto), session_id, event_type, timestamp, value, zone_id
            
            # We must map EventType values to the strings the legacy analytics expect, 
            # especially 'enter_zone' and 'exit_zone' which expect a zone_id.
            
            # Backward compatibility: legacy session_id refers to the tracker token (person_id), not the new UUID visit_id
            session_id = event.person_id
            event_type = event.event_type.value
            timestamp = event.timestamp.isoformat()
            zone_id = event.zone
            
            # In legacy code, some events like 'staff_shift' or 'abandoned' used the 'value' column for duration.
            # We can extract duration from metadata if it exists.
            value = event.metadata.get("duration", None) if event.metadata else None
            
            cursor.execute(
                "INSERT INTO business_events (session_id, event_type, timestamp, value, zone_id) VALUES (?, ?, ?, ?, ?)",
                (session_id, event_type, timestamp, value, zone_id)
            )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"[PersistenceAdapter] Error saving event: {e}")
            return False

    def get_recent_diagnostics(self, limit: int = 50) -> list:
        """Retrieves recent system diagnostic events."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM system_diagnostics ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"[PersistenceAdapter] Error retrieving diagnostics: {e}")
            return []
