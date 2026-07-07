import os
import json
import sqlite3
from typing import Any

class TransitionValidator:
    last_validate_time_ms = 0.0

    @classmethod
    def validate(cls, transition: Any, db_path: str) -> bool:
        import time
        t_start = time.time()
        res = cls._validate_internal(transition, db_path)
        cls.last_validate_time_ms = (time.time() - t_start) * 1000.0
        return res

    @classmethod
    def _validate_internal(cls, transition: Any, db_path: str) -> bool:
        # Load camera configurations
        allow_spawn = True
        camera_role = "ENTRANCE"
        try:
            with open("configs/camera_config.json", "r") as f:
                cfg = json.load(f)
                cam_data = cfg.get(transition.camera, {})
                if isinstance(cam_data, dict):
                    allow_spawn = cam_data.get("allow_spawn_transition", True)
                    camera_role = cam_data.get("role", "ENTRANCE")
                else:
                    allow_spawn = True
        except Exception:
            pass

        is_spawn = (transition.previous_zone == "OUTSIDE")
        
        # 1. Camera spawn policy check
        is_initial_dining = getattr(transition, "is_initial_dining", False)
        if is_spawn and not allow_spawn and not is_initial_dining:
            print(f"VALIDATOR REJECTED: Camera spawn policy forbidden on camera {transition.camera}")
            cls.persist_validated(transition, db_path, 0.0, 0.0, 0.0, 0.0, False)
            return False

        # 2. Minimum distance check
        # Spawns and finalization exit events do not have to move
        is_finalization = getattr(transition, "is_finalization", False)
        if not is_spawn and not is_finalization and transition.distance_pixels < 5.0:
            print(f"VALIDATOR REJECTED: Transition distance {transition.distance_pixels:.1f}px is below minimum 5px")
            cls.persist_validated(transition, db_path, 0.0, 0.0, 0.0, 0.0, False)
            return False

        # 3. Maximum speed check
        if transition.travel_time > 0.1 and transition.average_speed > 500.0:
            print(f"VALIDATOR REJECTED: Speed {transition.average_speed:.1f}px/s exceeds max walking speed limit")
            cls.persist_validated(transition, db_path, 0.0, 0.0, 0.0, 0.0, False)
            return False

        # 4. Zone adjacency check
        prev = transition.previous_zone
        curr = transition.current_zone
        
        # Define adjacent pairs (symmetric)
        adjacent = [
            ("Entrance", "Dining"),
            ("Dining", "Entrance"),
            ("Entrance", "Reception"),
            ("Reception", "Entrance"),
            ("Entrance", "Queue"),
            ("Queue", "Entrance"),
            ("Entrance", "Waiting Area"),
            ("Waiting Area", "Entrance"),
            ("Entrance", "Exit"),
            ("Exit", "Entrance"),
            
            ("Reception", "Waiting Area"),
            ("Waiting Area", "Reception"),
            ("Reception", "Dining"),
            ("Dining", "Reception"),
            ("Reception", "Exit"),
            ("Exit", "Reception"),
            
            ("Queue", "Waiting Area"),
            ("Waiting Area", "Queue"),
            ("Queue", "Dining"),
            ("Dining", "Queue"),
            ("Queue", "Counter"),
            ("Counter", "Queue"),
            
            ("Waiting Area", "Dining"),
            ("Dining", "Waiting Area"),
            
            ("Dining", "Exit"),
            ("Exit", "Dining"),
            
            ("Dining", "Table 101"),
            ("Table 101", "Dining"),
            ("Dining", "Table 102"),
            ("Table 102", "Dining"),
            
            ("Dining", "Kitchen"),
            ("Kitchen", "Dining"),
            
            ("Exit", "OUTSIDE"),
            ("OUTSIDE", "Exit"),
            ("Entrance", "OUTSIDE"),
            ("OUTSIDE", "Entrance")
        ]
        
        if not is_spawn and not is_finalization and (prev, curr) not in adjacent and prev != curr:
            print(f"VALIDATOR REJECTED: Non-adjacent zone transition {prev} -> {curr}")
            cls.persist_validated(transition, db_path, 0.0, 0.0, 0.0, 0.0, False)
            return False

        # Calculate confidences
        tracking_conf = transition.confidence
        zone_conf = 0.95
        rule_conf = 0.90
        trans_conf = tracking_conf * zone_conf * rule_conf

        # Persist validated transition
        cls.persist_validated(transition, db_path, tracking_conf, zone_conf, rule_conf, trans_conf, True)
        return True

    @classmethod
    def persist_validated(cls, trans: Any, db_path: str, tracking_conf: float, zone_conf: float, rule_conf: float, trans_conf: float, is_valid: bool):
        conn = sqlite3.connect(db_path, timeout=60.0)
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
                average_speed REAL,
                distance_pixels REAL,
                direction TEXT,
                tracking_confidence REAL,
                zone_confidence REAL,
                rule_confidence REAL,
                transition_confidence REAL,
                is_valid INTEGER
            )
        ''')
        conn.execute('''
            INSERT OR REPLACE INTO validated_transitions (
                transition_id, journey_id, tracker_id, camera,
                previous_zone, current_zone, entry_frame, exit_frame,
                entry_timestamp, exit_timestamp, travel_time,
                average_speed, distance_pixels, direction,
                tracking_confidence, zone_confidence, rule_confidence,
                transition_confidence, is_valid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trans.transition_id, trans.journey_id, trans.tracker_id, trans.camera,
            trans.previous_zone, trans.current_zone, trans.entry_frame, trans.exit_frame,
            trans.entry_timestamp.isoformat(), trans.exit_timestamp.isoformat(),
            trans.travel_time, trans.average_speed, trans.distance_pixels, trans.direction,
            tracking_conf, zone_conf, rule_conf, trans_conf, int(is_valid)
        ))
        conn.commit()
        conn.close()
