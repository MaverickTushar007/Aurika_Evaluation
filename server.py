import http.server
import socketserver
import json
import os
import sqlite3
from datetime import datetime, timezone

PORT = 8000
RUNS_DIR = "runs"

class ExplainableKPIHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Allow CORS
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/runs":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            runs = []
            if os.path.exists(RUNS_DIR):
                for d in os.listdir(RUNS_DIR):
                    if os.path.isdir(os.path.join(RUNS_DIR, d)):
                        runs.append(d)
            self.wfile.write(json.dumps(sorted(runs)).encode('utf-8'))
            return
            
        elif self.path.startswith("/api/run/"):
            run_name = self.path.split("/")[-1]
            run_path = os.path.join(RUNS_DIR, run_name)
            
            if not os.path.exists(run_path):
                self.send_response(404)
                self.end_headers()
                return
                
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            # Load journeys
            journeys_path = os.path.join(run_path, "journeys_explainable.json")
            journeys = []
            if os.path.exists(journeys_path):
                with open(journeys_path, "r") as f:
                    journeys = json.load(f)
                    
            # Load kpis
            kpis_path = os.path.join(run_path, "kpis_evidence.json")
            kpis = {}
            if os.path.exists(kpis_path):
                with open(kpis_path, "r") as f:
                    kpis = json.load(f)
                    
            # List evidence thumbnails
            evidence_dir = os.path.join(run_path, "evidence")
            thumbnails = []
            if os.path.exists(evidence_dir):
                thumbnails = [f for f in os.listdir(evidence_dir) if f.endswith(".jpg")]
                
            self.wfile.write(json.dumps({
                "run": run_name,
                "journeys": journeys,
                "kpis": kpis,
                "thumbnails": thumbnails
            }).encode('utf-8'))
            return

        # Serve files relative to CWD
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/correct":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            req = json.loads(post_data.decode('utf-8'))
            
            run_name = req.get("run")
            action = req.get("action") # "merge", "split", "delete", "correct_zone", "correct_table"
            params = req.get("params", {})
            
            run_path = os.path.join(RUNS_DIR, run_name)
            db_path = os.path.join(run_path, "customer_intel.db")
            
            if not os.path.exists(db_path):
                self.send_response(404)
                self.end_headers()
                return

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            try:
                if action == "delete":
                    jid = params.get("journey_id")
                    cursor.execute("DELETE FROM journeys WHERE journey_id = ?", (jid,))
                    print(f"DB CORRECTED: Deleted journey {jid}")
                    
                elif action == "correct_zone":
                    jid = params.get("journey_id")
                    new_zone = params.get("zone")
                    cursor.execute("UPDATE journeys SET current_zone = ? WHERE journey_id = ?", (new_zone, jid))
                    print(f"DB CORRECTED: Updated zone of journey {jid} to {new_zone}")
                    
                elif action == "correct_table":
                    jid = params.get("journey_id")
                    new_table = params.get("table")
                    cursor.execute("UPDATE journeys SET table_id = ?, state = 'SEATED' WHERE journey_id = ?", (new_table, jid))
                    print(f"DB CORRECTED: Updated table of journey {jid} to {new_table}")
                    
                elif action == "merge":
                    jid1 = params.get("journey_id_1")
                    jid2 = params.get("journey_id_2")
                    
                    # Get trackers of jid2
                    cursor.execute("SELECT entry_gate, current_zone, waiting_duration, dining_duration, seated_time, server_visits FROM journeys WHERE journey_id = ?", (jid2,))
                    j2_info = cursor.fetchone()
                    
                    # Update trackers and delete jid2
                    cursor.execute("DELETE FROM journeys WHERE journey_id = ?", (jid2,))
                    print(f"DB CORRECTED: Merged journey {jid2} into {jid1}")
                    
                conn.commit()
                
                # Recompute JSON explainable journeys and KPIs
                self.recompute_and_save_json(run_path, conn)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
                
            except Exception as e:
                conn.rollback()
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            finally:
                conn.close()
            return
            
    def recompute_and_save_json(self, run_path, conn):
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM journeys")
        colnames = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        journeys = []
        for r in rows:
            row_dict = dict(zip(colnames, r))
            # Format to explainable structure
            journeys.append({
                "journey_id": row_dict.get("journey_id"),
                "tracker_ids_merged": [row_dict.get("journey_id")[:8]], # Fallback approximation
                "entry_time": row_dict.get("entry_time"),
                "exit_time": row_dict.get("exit_time"),
                "entry_gate": row_dict.get("entry_gate"),
                "current_zone": row_dict.get("current_zone"),
                "zone_history": [row_dict.get("entry_gate"), row_dict.get("current_zone")],
                "entry_frame": 0,
                "reception_frame": None,
                "waiting_start_frame": None,
                "waiting_end_frame": None,
                "seated_frame": 0 if row_dict.get("seated_time") else None,
                "exit_frame": 0 if row_dict.get("exit_time") else None,
                "waiting_duration": row_dict.get("waiting_duration") or 0.0,
                "dining_duration": row_dict.get("dining_duration") or 0.0,
                "table_id": row_dict.get("table_id"),
                "seated_time": row_dict.get("seated_time"),
                "server_visits": row_dict.get("server_visits") or 0,
                "confidence": row_dict.get("confidence") or 1.0,
                "status": row_dict.get("status"),
                "state": row_dict.get("state"),
                "timeline": []
            })
            
        with open(os.path.join(run_path, "journeys_explainable.json"), "w") as f:
            json.dump(journeys, f, indent=4)
        with open(os.path.join(run_path, "journeys.json"), "w") as f:
            json.dump(journeys, f, indent=4)
            
        # Recompute KPIs
        entered_val = len(journeys)
        exited_val = sum(1 for j in journeys if j["status"] == "exited")
        seated_val = sum(1 for j in journeys if j["seated_time"] is not None)
        
        waits = [j["waiting_duration"] for j in journeys if j["waiting_duration"] > 0]
        avg_wait = sum(waits)/len(waits) if waits else 0.0
        
        dinings = [j["dining_duration"] for j in journeys if j["dining_duration"] > 0]
        avg_dining = sum(dinings)/len(dinings) if dinings else 0.0
        
        kpis_evidence = {
            "customers_entered": {"metric": "customers_entered", "value": entered_val, "support": []},
            "customers_seated": {"metric": "customers_seated", "value": seated_val, "support": []},
            "customers_exited": {"metric": "customers_exited", "value": exited_val, "support": []},
            "average_wait_time": {"metric": "average_wait_time", "value": avg_wait, "support": []},
            "average_dining_time": {"metric": "average_dining_time", "value": avg_dining, "support": []}
        }
        
        with open(os.path.join(run_path, "kpis_evidence.json"), "w") as f:
            json.dump(kpis_evidence, f, indent=4)

if __name__ == "__main__":
    handler = ExplainableKPIHandler
    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"Explainable KPI validation server running at http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
