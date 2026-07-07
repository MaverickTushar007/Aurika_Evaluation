import os
import sqlite3
import json
import pytest
import numpy as np
from datetime import datetime, timedelta

from restaurant_analytics.journey_manager import JourneyManager, Journey
from restaurant_analytics.spatial_transition_engine import SpatialTransition
from restaurant_analytics.transition_validator import TransitionValidator
from restaurant_analytics.event_rule_engine import EventRuleEngine

DB_PATH = "runs/test_run/customer_intel_test.db"
RUN_DIR = "runs/test_run"
DUMMY_IMG = np.zeros((100, 100, 3), dtype=np.uint8)
DUMMY_BBOX = [10, 10, 50, 50]

def init_test_db(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
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
        CREATE TABLE IF NOT EXISTS spatial_transitions (
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
            confidence REAL
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
    conn.commit()
    conn.close()

@pytest.fixture(autouse=True)
def setup_teardown():
    os.makedirs(RUN_DIR, exist_ok=True)
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass
    # Create tables
    init_test_db(DB_PATH)
    # Initialize Rule Engine rules
    EventRuleEngine.load_rules("configs/event_rules.json")
    yield
    # Cleanup
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass

def test_tracker_birth():
    # TEST 1: Tracker Birth inside Dining -> Expected 0 events, 0 rule evals
    jm = JourneyManager(db_path=DB_PATH, camera_id="cam_dining")
    now = datetime.now()
    jm.handle_track_update(
        track_id="T001",
        zone="Dining",
        centroid=(100, 100),
        is_new=True,
        is_staff=False,
        timestamp=now,
        frame_id=1,
        frame_img=DUMMY_IMG,
        bbox=DUMMY_BBOX,
        run_dir=RUN_DIR
    )
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM business_events")
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 0

def test_entrance_crossing():
    # TEST 2: Move one object OUTSIDE -> Entrance -> Expected exactly 1 GuestEnteredRestaurant
    jm = JourneyManager(db_path=DB_PATH, camera_id="cam_entrance")
    now = datetime.now()
    jm.handle_track_update(
        track_id="T002",
        zone="Entrance",
        centroid=(100, 100),
        is_new=True,
        is_staff=False,
        timestamp=now,
        frame_id=1,
        frame_img=DUMMY_IMG,
        bbox=DUMMY_BBOX,
        run_dir=RUN_DIR
    )
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT rule_id FROM business_events")
    rows = cursor.fetchall()
    conn.close()
    
    assert len(rows) == 1
    assert rows[0][0] == "ENTRY_001"

def test_duplicate_frames():
    # TEST 3: Keep object inside Entrance for 100 frames -> Only 1 GuestEnteredRestaurant
    jm = JourneyManager(db_path=DB_PATH, camera_id="cam_entrance")
    now = datetime.now()
    jm.handle_track_update(
        track_id="T003",
        zone="Entrance",
        centroid=(100, 100),
        is_new=True,
        is_staff=False,
        timestamp=now,
        frame_id=0,
        frame_img=DUMMY_IMG,
        bbox=DUMMY_BBOX,
        run_dir=RUN_DIR
    )
    for f in range(1, 100):
        jm.handle_track_update(
            track_id="T003",
            zone="Entrance",
            centroid=(100, 100),
            is_new=False,
            is_staff=False,
            timestamp=now + timedelta(seconds=f),
            frame_id=f,
            frame_img=DUMMY_IMG,
            bbox=DUMMY_BBOX,
            run_dir=RUN_DIR
        )
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM business_events WHERE rule_id='ENTRY_001'")
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 1

def test_zone_flicker():
    # TEST 4: Zone Flicker Dining -> Waiting -> Dining -> Waiting -> Suppress oscillating events
    jm = JourneyManager(db_path=DB_PATH, camera_id="cam_dining")
    now = datetime.now()
    jm.handle_track_update(
        track_id="T004",
        zone="Dining",
        centroid=(100, 100),
        is_new=True,
        is_staff=False,
        timestamp=now,
        frame_id=1,
        frame_img=DUMMY_IMG,
        bbox=DUMMY_BBOX,
        run_dir=RUN_DIR
    )
    jm.handle_track_update(
        track_id="T004",
        zone="Waiting Area",
        centroid=(100, 100),
        is_new=False,
        is_staff=False,
        timestamp=now + timedelta(seconds=1),
        frame_id=2,
        frame_img=DUMMY_IMG,
        bbox=DUMMY_BBOX,
        run_dir=RUN_DIR
    )
    jm.handle_track_update(
        track_id="T004",
        zone="Dining",
        centroid=(100, 100),
        is_new=False,
        is_staff=False,
        timestamp=now + timedelta(seconds=2),
        frame_id=3,
        frame_img=DUMMY_IMG,
        bbox=DUMMY_BBOX,
        run_dir=RUN_DIR
    )
    jm.handle_track_update(
        track_id="T004",
        zone="Waiting Area",
        centroid=(100, 100),
        is_new=False,
        is_staff=False,
        timestamp=now + timedelta(seconds=3),
        frame_id=4,
        frame_img=DUMMY_IMG,
        bbox=DUMMY_BBOX,
        run_dir=RUN_DIR
    )
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM business_events")
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 0

def test_impossible_jump():
    # TEST 5: Impossible Jump -> Dining -> Outside directly without Exit
    trans = SpatialTransition(
        journey_id="J_IMP",
        tracker_id="T_IMP",
        camera="cam_dining",
        previous_zone="Dining",
        current_zone="OUTSIDE",
        entry_frame=1,
        exit_frame=2,
        entry_timestamp=datetime.now(),
        exit_timestamp=datetime.now() + timedelta(seconds=1),
        prev_centroid=(100, 100),
        curr_centroid=(200, 200)
    )
    res = TransitionValidator.validate(trans, DB_PATH)
    assert not res

def test_spawn_policy():
    # TEST 6: Spawn Policy DINING camera spawn=false
    trans = SpatialTransition(
        journey_id="J_SPAWN",
        tracker_id="T_SPAWN",
        camera="cam_dining",
        previous_zone="OUTSIDE",
        current_zone="Dining",
        entry_frame=1,
        exit_frame=1,
        entry_timestamp=datetime.now(),
        exit_timestamp=datetime.now(),
        prev_centroid=None,
        curr_centroid=(100, 100)
    )
    res = TransitionValidator.validate(trans, DB_PATH)
    assert not res

def test_travel_distance():
    # TEST 7: Travel Distance distance=0
    trans = SpatialTransition(
        journey_id="J_DIST",
        tracker_id="T_DIST",
        camera="cam_dining",
        previous_zone="Dining",
        current_zone="Waiting Area",
        entry_frame=1,
        exit_frame=2,
        entry_timestamp=datetime.now(),
        exit_timestamp=datetime.now() + timedelta(seconds=1),
        prev_centroid=(100, 100),
        curr_centroid=(100, 100)
    )
    res = TransitionValidator.validate(trans, DB_PATH)
    assert not res

def test_speed():
    # TEST 8: Travel speed exceeds max walking speed
    trans = SpatialTransition(
        journey_id="J_SPEED",
        tracker_id="T_SPEED",
        camera="cam_dining",
        previous_zone="Dining",
        current_zone="Waiting Area",
        entry_frame=1,
        exit_frame=2,
        entry_timestamp=datetime.now(),
        exit_timestamp=datetime.now() + timedelta(milliseconds=500),
        prev_centroid=(100, 100),
        curr_centroid=(1000, 1000)
    )
    res = TransitionValidator.validate(trans, DB_PATH)
    assert not res

def test_adjacency():
    # TEST 9: Adjacency: Waiting Area -> Reception PASS, Waiting Area -> Outside FAIL
    trans_pass = SpatialTransition(
        journey_id="J_ADJ_P",
        tracker_id="T_ADJ_P",
        camera="cam_entrance",
        previous_zone="Reception",
        current_zone="Waiting Area",
        entry_frame=1,
        exit_frame=2,
        entry_timestamp=datetime.now(),
        exit_timestamp=datetime.now() + timedelta(seconds=5),
        prev_centroid=(100, 100),
        curr_centroid=(120, 120)
    )
    assert TransitionValidator.validate(trans_pass, DB_PATH)
    
    trans_fail = SpatialTransition(
        journey_id="J_ADJ_F",
        tracker_id="T_ADJ_F",
        camera="cam_entrance",
        previous_zone="Waiting Area",
        current_zone="OUTSIDE",
        entry_frame=1,
        exit_frame=2,
        entry_timestamp=datetime.now(),
        exit_timestamp=datetime.now() + timedelta(seconds=5),
        prev_centroid=(100, 100),
        curr_centroid=(120, 120)
    )
    assert not TransitionValidator.validate(trans_fail, DB_PATH)

def test_evidence_chain():
    # TEST 10: Assert KPI -> business_event -> validated_transition -> journey -> frame -> image crop exists
    jm = JourneyManager(db_path=DB_PATH, camera_id="cam_entrance")
    now = datetime.now()
    jm.handle_track_update(
        track_id="T010",
        zone="Entrance",
        centroid=(100, 100),
        is_new=True,
        is_staff=False,
        timestamp=now,
        frame_id=1,
        frame_img=DUMMY_IMG,
        bbox=DUMMY_BBOX,
        run_dir=RUN_DIR
    )
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT transition_id, journey_id, frame FROM business_events LIMIT 1")
    row = cursor.fetchone()
    assert row is not None
    trans_id, journey_id, frame = row
    
    cursor.execute("SELECT COUNT(*) FROM spatial_transitions WHERE transition_id=?", (trans_id,))
    assert cursor.fetchone()[0] == 1
    
    cursor.execute("SELECT COUNT(*) FROM validated_transitions WHERE transition_id=?", (trans_id,))
    assert cursor.fetchone()[0] == 1
    
    cursor.execute("SELECT COUNT(*) FROM journeys WHERE journey_id=?", (journey_id,))
    assert cursor.fetchone()[0] == 1
    
    crop_path = f"{RUN_DIR}/evidence/{journey_id}_entered.jpg"
    assert os.path.exists(crop_path)
    conn.close()

def test_track_lost_and_sweep():
    # Test handle_track_lost and sweep_lost_journeys flow
    jm = JourneyManager(db_path=DB_PATH, camera_id="cam_entrance")
    now = datetime.now()
    jm.handle_track_update(
        track_id="T020",
        zone="Entrance",
        centroid=(100, 100),
        is_new=True,
        is_staff=False,
        timestamp=now,
        frame_id=1,
        frame_img=DUMMY_IMG,
        bbox=DUMMY_BBOX,
        run_dir=RUN_DIR
    )
    
    jm.handle_track_lost("T020", now + timedelta(seconds=2))
    assert jm.journeys[0].status == "lost"
    
    # Sweep lost journeys - should finalize transition because duration > 8s
    jm.sweep_lost_journeys(now + timedelta(seconds=12), force_all=False, frame_id=100)
    assert jm.journeys[0].status == "exited"
    assert jm.journeys[0].exit_frame == 100

def test_waiting_duration_complete():
    jm = JourneyManager(db_path=DB_PATH, camera_id="cam_reception")
    now = datetime.now()
    # Spawn at Reception
    jm.handle_track_update("T030", "Reception", (100, 100), True, False, now, 1, DUMMY_IMG, DUMMY_BBOX, RUN_DIR)
    
    # Start waiting (different centroid to avoid 0px validator rejection)
    jm.handle_track_update("T030", "Waiting Area", (110, 110), False, False, now + timedelta(seconds=1), 2, DUMMY_IMG, DUMMY_BBOX, RUN_DIR)
    # Transition to Dining -> waiting ends (different centroid)
    jm.handle_track_update("T030", "Dining", (120, 120), False, False, now + timedelta(seconds=6), 3, DUMMY_IMG, DUMMY_BBOX, RUN_DIR)
    
    assert jm.journeys[0].waiting_duration == 5.0

def test_dining_duration_complete():
    jm = JourneyManager(db_path=DB_PATH, camera_id="cam_dining_spawn_allowed")
    now = datetime.now()
    # Spawn inside Dining
    jm.handle_track_update("T040", "Dining", (100, 100), True, False, now, 1, DUMMY_IMG, DUMMY_BBOX, RUN_DIR)
    
    # Transition to Table 101 -> Seated
    jm.handle_track_update("T040", "Table 101", (120, 120), False, False, now + timedelta(seconds=2), 2, DUMMY_IMG, DUMMY_BBOX, RUN_DIR)
    # Transition back to Dining -> Seated/dining ends
    jm.handle_track_update("T040", "Dining", (100, 100), False, False, now + timedelta(seconds=12), 3, DUMMY_IMG, DUMMY_BBOX, RUN_DIR)
    
    assert jm.journeys[0].dining_duration == 10.0

def test_server_visit():
    jm = JourneyManager(db_path=DB_PATH, camera_id="cam_dining_spawn_allowed")
    now = datetime.now()
    jm.handle_track_update("T050", "Table 101", (100, 100), True, False, now, 1, DUMMY_IMG, DUMMY_BBOX, RUN_DIR)
    # Set seated status
    jm.journeys[0].table_id = "Table 101"
    jm.journeys[0].status = "active"
    jm.save_journey(jm.journeys[0])
    
    # Log server visit
    jm.log_server_visit("Table 101", "Staff_01", now + timedelta(seconds=5), 15.0)
    assert jm.journeys[0].server_visits == 1

def test_no_zone_change():
    jm = JourneyManager(db_path=DB_PATH, camera_id="cam_entrance")
    now = datetime.now()
    jm.handle_track_update("T060", "Entrance", (100, 100), True, False, now, 1, DUMMY_IMG, DUMMY_BBOX, RUN_DIR)
    
    # Same zone, different centroid
    jm.handle_track_update("T060", "Entrance", (105, 105), False, False, now + timedelta(seconds=2), 2, DUMMY_IMG, DUMMY_BBOX, RUN_DIR)
    
    # Verify last_centroid and last_active_time updated
    assert jm.journeys[0].last_centroid == (105, 105)
    assert jm.journeys[0].last_active_time == now + timedelta(seconds=2)

def test_tracker_reassociation_and_split():
    jm = JourneyManager(db_path=DB_PATH, camera_id="cam_entrance")
    now = datetime.now()
    
    # Birth track T070
    jm.handle_track_update("T070", "Entrance", (100, 100), True, False, now, 1, DUMMY_IMG, DUMMY_BBOX, RUN_DIR)
    # Lose track T070
    jm.handle_track_lost("T070", now + timedelta(seconds=1))
    
    # Birth track T071 within 8 seconds at Entrance -> triggers merge/reassociation
    jm.handle_track_update("T071", "Entrance", (102, 102), True, False, now + timedelta(seconds=3), 2, DUMMY_IMG, DUMMY_BBOX, RUN_DIR)
    assert jm.merge_count == 1
    assert "T071" in jm.journeys[0].active_tracker_ids
    
    # Lose track T071
    jm.handle_track_lost("T071", now + timedelta(seconds=4))
    
    # Birth track T072 when a track was lost recently -> triggers split suggestion check (different zone to avoid fallback merge)
    jm.handle_track_update("T072", "Dining", (400, 400), True, False, now + timedelta(seconds=5), 3, DUMMY_IMG, DUMMY_BBOX, RUN_DIR)
    assert jm.split_count >= 1

def test_exit_transition_zone():
    jm = JourneyManager(db_path=DB_PATH, camera_id="cam_exit_test")
    now = datetime.now()
    # Spawn at Exit zone
    jm.handle_track_update("T080", "Exit", (100, 100), True, False, now, 1, DUMMY_IMG, DUMMY_BBOX, RUN_DIR)
    
    # Override state to ENTERED to match EXIT_001 rule requirement
    jm.journeys[0].state = "ENTERED"
    
    # Transition to OUTSIDE
    jm.handle_track_update("T080", "OUTSIDE", (120, 120), False, False, now + timedelta(seconds=3), 2, DUMMY_IMG, DUMMY_BBOX, RUN_DIR)
    
    assert jm.journeys[0].status == "exited"
    assert jm.journeys[0].state == "EXITED"
    assert os.path.exists(f"{RUN_DIR}/evidence/{jm.journeys[0].journey_id}_exit.jpg")

def test_birth_reception_and_waiting_states():
    # Force mock rule to return ReachedReception and StartedWaiting on Birth
    # Setup test cameras with different settings
    orig_rules = EventRuleEngine._rules
    EventRuleEngine._rules = [{
        "id": "ENTRY_MOCK_RECEPTION",
        "emit": "ReachedReception",
        "from": "OUTSIDE",
        "to": "Reception",
        "camera_roles": ["RECEPTION"]
    }, {
        "id": "ENTRY_MOCK_WAIT",
        "emit": "StartedWaiting",
        "from": "OUTSIDE",
        "to": "Waiting Area",
        "camera_roles": ["RECEPTION"]
    }, {
        "id": "ENTRY_MOCK_SEATED",
        "emit": "Seated",
        "from": "OUTSIDE",
        "to": "Table 101",
        "camera_roles": ["DINING"]
    }, {
        "id": "ENTRY_MOCK_EXIT",
        "emit": "GuestExitedRestaurant",
        "from": "OUTSIDE",
        "to": "Exit",
        "camera_roles": ["EXIT"]
    }]
    
    try:
        now = datetime.now()
        # Test Birth -> RECEPTION
        jm1 = JourneyManager(db_path=DB_PATH, camera_id="cam_reception")
        jm1.handle_track_update("T090", "Reception", (100, 100), True, False, now, 1, DUMMY_IMG, DUMMY_BBOX, RUN_DIR)
        assert jm1.journeys[0].state == "RECEPTION"
        
        # Test Birth -> WAITING
        jm2 = JourneyManager(db_path=DB_PATH, camera_id="cam_reception")
        jm2.handle_track_update("T091", "Waiting Area", (100, 100), True, False, now, 1, DUMMY_IMG, DUMMY_BBOX, RUN_DIR)
        assert jm2.journeys[0].state == "WAITING"
        assert jm2.journeys[0].waiting_started is not None
        
        # Test Birth -> SEATED
        jm3 = JourneyManager(db_path=DB_PATH, camera_id="cam_dining_spawn_allowed")
        jm3.handle_track_update("T092", "Table 101", (100, 100), True, False, now, 1, DUMMY_IMG, DUMMY_BBOX, RUN_DIR)
        assert jm3.journeys[0].state == "SEATED"
        assert jm3.journeys[0].seated_time is not None
        
        # Test Birth -> EXITED
        jm4 = JourneyManager(db_path=DB_PATH, camera_id="cam_exit_test")
        jm4.handle_track_update("T093", "Exit", (100, 100), True, False, now, 1, DUMMY_IMG, DUMMY_BBOX, RUN_DIR)
        assert jm4.journeys[0].state == "EXITED"
        assert jm4.journeys[0].status == "exited"
    finally:
        EventRuleEngine._rules = orig_rules

def test_event_rule_engine_edge_cases():
    EventRuleEngine.load_rules("configs/non_existent.json")
    assert EventRuleEngine._rules == []
    
    invalid_path = "configs/invalid.json"
    with open(invalid_path, "w") as f:
        f.write("{invalid_json:")
    try:
        EventRuleEngine.load_rules(invalid_path)
        assert EventRuleEngine._rules == []
    finally:
        if os.path.exists(invalid_path):
            os.remove(invalid_path)
            
    EventRuleEngine.load_rules("configs/event_rules.json")
    
    # Test evaluate direct impossible transitions using keyword arguments
    trans_imp1 = SpatialTransition(
        journey_id="id", tracker_id="J", camera="cam",
        previous_zone="Table 101", current_zone="Entrance",
        entry_frame=1, exit_frame=2,
        entry_timestamp=datetime.now(), exit_timestamp=datetime.now() + timedelta(seconds=1),
        prev_centroid=(100, 100), curr_centroid=(120, 120)
    )
    e, r = EventRuleEngine.evaluate(trans_imp1, "ENTRANCE", {})
    assert e is None
    
    trans_imp2 = SpatialTransition(
        journey_id="id", tracker_id="J", camera="cam",
        previous_zone="Queue", current_zone="Reception",
        entry_frame=1, exit_frame=2,
        entry_timestamp=datetime.now(), exit_timestamp=datetime.now() + timedelta(seconds=1),
        prev_centroid=(100, 100), curr_centroid=(120, 120)
    )
    e, r = EventRuleEngine.evaluate(trans_imp2, "ENTRANCE", {})
    assert e is None
    
    trans_imp3 = SpatialTransition(
        journey_id="id", tracker_id="J", camera="cam",
        previous_zone="Dining", current_zone="OUTSIDE",
        entry_frame=1, exit_frame=2,
        entry_timestamp=datetime.now(), exit_timestamp=datetime.now() + timedelta(seconds=1),
        prev_centroid=(100, 100), curr_centroid=(120, 120)
    )
    e, r = EventRuleEngine.evaluate(trans_imp3, "ENTRANCE", {"zone_history": ["Entrance", "Dining"]})
    assert e is None

    # Mock specific rules with conditions for full coverage of checks
    EventRuleEngine._rules = [{
        "id": "RULE_CONF_TEST",
        "emit": "TestEvent",
        "from": "OUTSIDE",
        "to": "Entrance",
        "camera_roles": ["ENTRANCE"],
        "enabled": True,
        "conditions": {
            "minimum_confidence": 0.8,
            "minimum_track_age": 2
        }
    }, {
        "id": "RULE_DISABLED",
        "emit": "DisabledEvent",
        "from": "OUTSIDE",
        "to": "Entrance",
        "camera_roles": ["ENTRANCE"],
        "enabled": False
    }]
    
    trans = SpatialTransition(
        journey_id="id", tracker_id="J", camera="cam",
        previous_zone="OUTSIDE", current_zone="Entrance",
        entry_frame=1, exit_frame=2,
        entry_timestamp=datetime.now(), exit_timestamp=datetime.now() + timedelta(seconds=1),
        prev_centroid=(100, 100), curr_centroid=(120, 120)
    )
    e, r = EventRuleEngine.evaluate(trans, "ENTRANCE", {"confidence": 0.1, "track_age": 10})
    assert e is None

    # Test condition failure - track age too low
    e, r = EventRuleEngine.evaluate(trans, "ENTRANCE", {"confidence": 0.9, "track_age": 0})
    assert e is None
    
    # Test pass conditions
    e, r = EventRuleEngine.evaluate(trans, "ENTRANCE", {"confidence": 0.9, "track_age": 3})
    assert e == "TestEvent"

def test_transition_validator_edge_cases():
    # Test camera spawn policy loading with invalid config file path
    backup_path = "configs/camera_config.json.bak"
    os.rename("configs/camera_config.json", backup_path)
    try:
        trans = SpatialTransition(
            journey_id="id", tracker_id="J", camera="cam_dining",
            previous_zone="OUTSIDE", current_zone="Dining",
            entry_frame=1, exit_frame=2,
            entry_timestamp=datetime.now(), exit_timestamp=datetime.now() + timedelta(seconds=1),
            prev_centroid=(100, 100), curr_centroid=(120, 120)
        )
        res = TransitionValidator.validate(trans, DB_PATH)
        assert res
    finally:
        os.rename(backup_path, "configs/camera_config.json")
        
    # Test camera config with string role instead of dictionary
    with open("configs/camera_config.json", "r") as f:
        orig = json.load(f)
    cfg = orig.copy()
    cfg["cam_dining"] = "DINING"
    with open("configs/camera_config.json", "w") as f:
        json.dump(cfg, f)
        
    try:
        trans = SpatialTransition(
            journey_id="id", tracker_id="J", camera="cam_dining",
            previous_zone="OUTSIDE", current_zone="Dining",
            entry_frame=1, exit_frame=2,
            entry_timestamp=datetime.now(), exit_timestamp=datetime.now() + timedelta(seconds=1),
            prev_centroid=(100, 100), curr_centroid=(120, 120)
        )
        res = TransitionValidator.validate(trans, DB_PATH)
        assert res
    finally:
        with open("configs/camera_config.json", "w") as f:
            json.dump(orig, f)

def test_restaurant_state_engine():
    from restaurant_analytics.restaurant_state_engine import RestaurantStateEngine
    engine = RestaurantStateEngine(db_path=DB_PATH, run_dir=RUN_DIR)
    
    # 1. Test performance update
    engine.update_performance({"yolo_inference_time_ms": 10.0})
    assert engine.perf_profiles["yolo_inference_time_ms"] == 10.0
    
    # 2. Test heatmap accumulation
    tracks = [("T001", [10, 20, 30, 40], True)]
    engine.accumulate_heatmap_points(tracks, {"T001": 0})
    assert len(engine.occupancy_points) == 1
    assert len(engine.customer_movement_points) == 1
    
    # 3. Test processing state
    engine.process_frame_state(datetime.now(), 1, tracks, {"T001": 0})
    assert os.path.exists(engine.state_file_path)

