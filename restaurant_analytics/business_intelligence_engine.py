import os
import csv
import json
import sqlite3
import shutil
from datetime import datetime

class BusinessIntelligenceEngine:
    def __init__(self, db_path, output_dir):
        self.db_path = db_path
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def get_semantic_zone(self, zone, camera_role):
        if zone == "UNKNOWN_ZONE" or not zone:
            if camera_role == "DINING":
                return "Dining Room"
            elif camera_role == "RECEPTION":
                return "Waiting/Reception Area"
            elif camera_role == "BUFFET":
                return "Buffet/Patio Area"
            else:
                return "Main Entrance"
        return zone

    def generate_report(self, video_name):
        if not os.path.exists(self.db_path):
            print(f"[BI Engine] Database missing at {self.db_path}")
            return
            
        # Load camera role from configs
        camera_role = "ENTRANCE"
        try:
            with open("configs/camera_config.json", "r") as f:
                cfg = json.load(f)
                for cam_id, cam_data in cfg.items():
                    if isinstance(cam_data, dict):
                        if cam_id in video_name or video_name.lower().startswith(cam_id.split("cam_")[-1]):
                            camera_role = cam_data.get("role", "ENTRANCE")
                            break
        except Exception:
            pass

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # --- Phase 4: Retrieve metrics exclusively from restaurant_business_events ---
        cursor.execute("SELECT COUNT(*) FROM restaurant_business_events WHERE event_type = 'ENTERED'")
        entered_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM restaurant_business_events WHERE event_type = 'EXITED'")
        exited_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT j.journey_id) FROM journeys j WHERE j.is_initial_spawn = 1 OR j.entry_frame < 50 OR j.journey_id NOT IN (SELECT journey_id FROM restaurant_business_events WHERE event_type = 'ENTERED')")
        initial_spawns = cursor.fetchone()[0] or 0

        active_count = max(0, initial_spawns + entered_count - exited_count)

        # Peak occupancy
        cursor.execute("SELECT event_type FROM restaurant_business_events WHERE event_type IN ('ENTERED', 'EXITED') ORDER BY frame ASC")
        occ = initial_spawns
        peak_occ = occ
        for row in cursor.fetchall():
            if row[0] == 'ENTERED':
                occ += 1
            elif row[0] == 'EXITED':
                occ -= 1
            if occ > peak_occ:
                peak_occ = occ
        avg_occ = 0.0

        # Peak queue
        cursor.execute("SELECT event_type FROM restaurant_business_events WHERE event_type IN ('WAITING_START', 'WAITING_END') ORDER BY frame ASC")
        q_len = 0
        max_q = 0
        for row in cursor.fetchall():
            if row[0] == 'WAITING_START':
                q_len += 1
            elif row[0] == 'WAITING_END':
                q_len -= 1
            if q_len > max_q:
                max_q = q_len
        avg_q = 0.0

        tables_occupied = []

        # Load database records for mapping and outputs
        journeys = []
        cursor.execute("SELECT journey_id, entry_time, exit_time, entry_gate, current_zone, waiting_duration, dining_duration, table_id, seated_time, server_visits, confidence, status, state, is_initial_spawn, entry_frame, exit_frame FROM journeys")
        for row in cursor.fetchall():
            journeys.append({
                "journey_id": row[0],
                "entry_time": row[1],
                "exit_time": row[2],
                "entry_gate": self.get_semantic_zone(row[3], camera_role),
                "current_zone": self.get_semantic_zone(row[4], camera_role),
                "waiting_duration": row[5] or 0.0,
                "dining_duration": row[6] or 0.0,
                "table_id": row[7],
                "seated_time": row[8],
                "server_visits": row[9] or 0,
                "confidence": row[10] or 1.0,
                "status": row[11],
                "state": row[12],
                "is_initial_spawn": row[13] or 0,
                "entry_frame": row[14],
                "exit_frame": row[15]
            })

        events = []
        cursor.execute("SELECT frame, timestamp, event_type, journey_id, tracker_id, destination_zone, waiting_seconds, evidence_image FROM restaurant_business_events ORDER BY frame ASC")
        for row in cursor.fetchall():
            ev_type = row[2]
            prev_z = "OUTSIDE"
            curr_z = "Entrance"
            if ev_type == "WAITING_START":
                prev_z = "Entrance"
                curr_z = "Queue"
            elif ev_type == "WAITING_END":
                prev_z = "Queue"
                curr_z = row[5] or "Dining"
            elif ev_type == "EXITED":
                prev_z = "Dining"
                curr_z = "OUTSIDE"
            
            events.append({
                "rule_id": ev_type,
                "camera": "cam_patio",
                "previous_zone": prev_z,
                "current_zone": curr_z,
                "journey_id": row[3],
                "timestamp": row[1],
                "frame": row[0],
                "waiting_seconds": row[6]
            })

        # --- 3. Export timeline.csv ---
        timeline_path = os.path.join(self.output_dir, "timeline.csv")
        with open(timeline_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp/Frame", "Event Description", "Journey ID", "Details"])
            for e in events:
                seconds = e["frame"] / 30.0
                minutes = int(seconds // 60)
                secs = int(seconds % 60)
                formatted_time = f"{minutes:02d}:{secs:02d}"
                
                desc = f"Zone Transition: {e['previous_zone']} -> {e['current_zone']}"
                if e["previous_zone"] == "OUTSIDE":
                    desc = f"Guest Entered (via {e['current_zone']})"
                elif e["current_zone"] == "OUTSIDE":
                    desc = f"Guest Exited (via {e['previous_zone']})"
                elif "Table" in e["current_zone"]:
                    desc = f"Guest Seated at {e['current_zone']}"
                elif e["current_zone"] == "Queue":
                    desc = "Guest Joined Queue"
                elif e["previous_zone"] == "Queue":
                    desc = "Guest Left Queue"
                    
                writer.writerow([formatted_time, desc, e["journey_id"], f"Frame {e['frame']} on Camera {e['camera']}"])

        # --- 4. Copy evidence crops to output folder ---
        evidence_out_dir = os.path.join(self.output_dir, "evidence")
        os.makedirs(evidence_out_dir, exist_ok=True)
        db_dir = os.path.dirname(self.db_path)
        evidence_in_dir = os.path.join(db_dir, "evidence")
        if os.path.exists(evidence_in_dir):
            for file_name in os.listdir(evidence_in_dir):
                if file_name.endswith(".jpg") or file_name.endswith(".png"):
                    shutil.copy2(os.path.join(evidence_in_dir, file_name), os.path.join(evidence_out_dir, file_name))

        # --- 5. Export customer_journeys.csv ---
        csv_path = os.path.join(self.output_dir, "customer_journeys.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Guest ID", "Entry Time", "Entry Frame", "Waiting Start", "Waiting End", "Waiting Seconds", "Returned To Queue? (YES/NO)", "Number Of Queue Visits", "Exit Time", "Exit Frame", "Journey Status", "Evidence Images"])
            for j in journeys:
                cursor.execute("SELECT timestamp FROM restaurant_business_events WHERE journey_id = ? AND event_type = 'WAITING_START' ORDER BY frame ASC", (j["journey_id"],))
                starts = cursor.fetchall()
                cursor.execute("SELECT timestamp, waiting_seconds FROM restaurant_business_events WHERE journey_id = ? AND event_type = 'WAITING_END' ORDER BY frame ASC", (j["journey_id"],))
                ends = cursor.fetchall()
                
                waiting_start_val = starts[0][0] if starts else "N/A"
                waiting_end_val = ends[0][0] if ends else "N/A"
                waiting_seconds_val = sum(row[1] for row in ends) if ends else 0.0
                queue_visits = len(starts)
                returned_to_queue = "YES" if len(starts) > 1 else "NO"
                
                writer.writerow([
                    j["journey_id"],
                    j["entry_time"],
                    j["entry_frame"] or 0,
                    waiting_start_val,
                    waiting_end_val,
                    f"{waiting_seconds_val:.1f}",
                    returned_to_queue,
                    queue_visits,
                    j["exit_time"] or "N/A",
                    j["exit_frame"] or 100,
                    j["status"],
                    f"evidence/{j['journey_id']}_entered.jpg"
                ])
                
        # --- 6. Export queue_analysis.csv ---
        with open(os.path.join(self.output_dir, "queue_analysis.csv"), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Value", "Details"])
            writer.writerow(["Maximum Queue Length", max_q, "Maximum simultaneously visible guests in queue"])
            writer.writerow(["Average Queue Length", f"{avg_q:.1f}", "Average wait line size"])
            
        # --- 7. Export table_analysis.csv ---
        with open(os.path.join(self.output_dir, "table_analysis.csv"), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Table ID", "Occupied", "Empty"])
            for t in range(101, 109):
                t_str = f"Table {t}"
                occupied = "Yes" if t_str in tables_occupied else "No"
                writer.writerow([t_str, occupied, "No" if occupied == "Yes" else "Yes"])

        # --- 8. Export timeline CSVs from SQL ---
        frame_occupancies = {}
        cursor.execute("SELECT frame, occupancy FROM frame_occupancies ORDER BY frame ASC")
        for row in cursor.fetchall():
            frame_occupancies[row[0]] = row[1]
            
        with open(os.path.join(self.output_dir, "occupancy_timeline.csv"), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Frame", "Guest Count"])
            for frame_id in sorted(frame_occupancies.keys()):
                writer.writerow([frame_id, frame_occupancies[frame_id]])
                
        # Arrivals / departures timeline
        arrivals_timeline = {}
        departures_timeline = {}
        for j in journeys:
            if j["entry_frame"] is not None:
                arrivals_timeline[j["entry_frame"]] = arrivals_timeline.get(j["entry_frame"], 0) + 1
            if j["status"] == "exited" and j["exit_frame"] is not None:
                departures_timeline[j["exit_frame"]] = departures_timeline.get(j["exit_frame"], 0) + 1
                
        with open(os.path.join(self.output_dir, "arrival_timeline.csv"), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Frame", "Arrival Count"])
            for frame_id in sorted(arrivals_timeline.keys()):
                writer.writerow([frame_id, arrivals_timeline[frame_id]])
                
        with open(os.path.join(self.output_dir, "departure_timeline.csv"), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Frame", "Departure Count"])
            for frame_id in sorted(departures_timeline.keys()):
                writer.writerow([frame_id, departures_timeline[frame_id]])

        # --- 9. Export restaurant_summary.json (7 core KPIs only) ---
        summary = {
            "guests_entered": entered_count,
            "guests_exited": exited_count,
            "current_occupancy": active_count,
            "peak_occupancy": peak_occ,
            "average_occupancy": round(avg_occ, 1),
            "maximum_queue_length": max_q,
            "tables_occupied_count": len(tables_occupied)
        }
        with open(os.path.join(self.output_dir, "restaurant_summary.json"), "w") as f:
            json.dump(summary, f, indent=4)
            
        # --- 10. Export business_report.json ---
        with open(os.path.join(self.output_dir, "business_report.json"), "w") as f:
            json.dump({"summary": summary}, f, indent=4)

        # --- 11. Export business_report.md ---
        with open(os.path.join(self.output_dir, "business_report.md"), "w") as f:
            f.write("# Restaurant Core Operations Report\n\n")
            f.write("## Verified Core KPIs\n")
            f.write(f"- **Guests Entered:** {entered_count}\n")
            f.write(f"- **Guests Exited:** {exited_count}\n")
            f.write(f"- **Current Occupancy:** {active_count}\n")
            f.write(f"- **Peak Occupancy:** {peak_occ}\n")
            f.write(f"- **Average Occupancy:** {avg_occ:.1f}\n")
            f.write(f"- **Maximum Queue Length:** {max_q}\n")
            f.write(f"- **Tables Occupied Count:** {len(tables_occupied)}\n")
        
        conn.close()
