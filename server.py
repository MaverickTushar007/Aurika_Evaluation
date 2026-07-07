import http.server
import socketserver
import json
import os
import sqlite3
from datetime import datetime, timezone

PORT = 8080
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
        import sys
        import traceback
        import urllib.parse
        print(f"REQUEST START - Path: {self.path}", flush=True)
        try:
            print("1 entered do_GET", flush=True)
            parsed_url = urllib.parse.urlparse(self.path)
            print("2 parsed URL", flush=True)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            print(f"Query parameters: {query_params}", flush=True)
            
            req_path = parsed_url.path
            
            if req_path == "/api/runs":
                print("Checking path: /api/runs", flush=True)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                
                runs = []
                print(f"Checking if {RUNS_DIR} exists", flush=True)
                exists = os.path.exists(RUNS_DIR)
                print(f"Checked if {RUNS_DIR} exists: {exists}", flush=True)
                if exists:
                    print(f"Listing directory {RUNS_DIR}", flush=True)
                    dirs = os.listdir(RUNS_DIR)
                    print(f"Listed directory {RUNS_DIR}: {dirs}", flush=True)
                    for d in dirs:
                        full_d = os.path.join(RUNS_DIR, d)
                        print(f"Checking if {full_d} is directory", flush=True)
                        is_dir = os.path.isdir(full_d)
                        print(f"Checked if {full_d} is directory: {is_dir}", flush=True)
                        if is_dir:
                            runs.append(d)
                response = json.dumps(sorted(runs))
                print(f"Writing response: {response}", flush=True)
                self.wfile.write(response.encode('utf-8'))
                print("REQUEST END - /api/runs complete", flush=True)
                return
                
            elif req_path.startswith("/api/run/"):
                print("Checking path: /api/run/", flush=True)
                run_name = req_path.split("/")[-1]
                run_path = os.path.join(RUNS_DIR, run_name)
                
                print(f"Checking if run_path {run_path} exists", flush=True)
                exists = os.path.exists(run_path)
                print(f"Checked: {exists}", flush=True)
                if not exists:
                    self.send_response(404)
                    self.end_headers()
                    print("REQUEST END - Run not found", flush=True)
                    return
                    
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                
                journeys_path = os.path.join(run_path, "journeys_explainable.json")
                journeys = []
                print(f"Checking if journeys_path {journeys_path} exists", flush=True)
                j_exists = os.path.exists(journeys_path)
                print(f"Checked journeys_path exists: {j_exists}", flush=True)
                if j_exists:
                    print(f"Opening journeys_path {journeys_path}", flush=True)
                    with open(journeys_path, "r") as f:
                        print(f"Loading json journeys_path", flush=True)
                        journeys = json.load(f)
                        print(f"Loaded json journeys_path", flush=True)
                        
                kpis_path = os.path.join(run_path, "kpis_evidence.json")
                kpis = {}
                print(f"Checking if kpis_path {kpis_path} exists", flush=True)
                k_exists = os.path.exists(kpis_path)
                print(f"Checked kpis_path exists: {k_exists}", flush=True)
                if k_exists:
                    print(f"Opening kpis_path {kpis_path}", flush=True)
                    with open(kpis_path, "r") as f:
                        print(f"Loading json kpis_path", flush=True)
                        kpis = json.load(f)
                        print(f"Loaded json kpis_path", flush=True)
                        
                evidence_dir = os.path.join(run_path, "evidence")
                thumbnails = []
                print(f"Checking if evidence_dir {evidence_dir} exists", flush=True)
                ev_exists = os.path.exists(evidence_dir)
                print(f"Checked evidence_dir exists: {ev_exists}", flush=True)
                if ev_exists:
                    print(f"Listing evidence_dir {evidence_dir}", flush=True)
                    files = os.listdir(evidence_dir)
                    print(f"Listed evidence_dir: {files}", flush=True)
                    thumbnails = [f for f in files if f.endswith(".jpg")]
                    
                response = json.dumps({
                    "run": run_name,
                    "journeys": journeys,
                    "kpis": kpis,
                    "thumbnails": thumbnails
                })
                print(f"Writing response for /api/run/", flush=True)
                self.wfile.write(response.encode('utf-8'))
                print("REQUEST END - /api/run/ complete", flush=True)
                return
                
            elif req_path.startswith("/dashboard/"):
                print("Checking path: /dashboard/", flush=True)
                
                run_param = query_params.get("run", [None])[0]
                print(f"Parsed run param: {run_param}", flush=True)
                if run_param:
                    run_path = os.path.join(RUNS_DIR, run_param)
                else:
                    print("Getting latest run dir", flush=True)
                    run_path = self.get_latest_run_dir()
                    print(f"Got latest run dir: {run_path}", flush=True)
                    
                if not run_path:
                    self.send_response(404)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "No active runs found"}).encode('utf-8'))
                    print("REQUEST END - No active runs found", flush=True)
                    return
                    
                state_file = os.path.join(run_path, "live_state.json")
                state_data = {}
                print(f"Checking if state_file {state_file} exists", flush=True)
                st_exists = os.path.exists(state_file)
                print(f"Checked state_file exists: {st_exists}", flush=True)
                if st_exists:
                    try:
                        print(f"Opening state_file {state_file}", flush=True)
                        with open(state_file, "r") as f:
                            print("Loading json state_file", flush=True)
                            state_data = json.load(f)
                            print("Loaded json state_file", flush=True)
                    except Exception as e:
                        print(f"Error loading state file: {e}", flush=True)
                        traceback.print_exc()
                        
                endpoint = req_path
                print(f"Endpoint requested: {endpoint}", flush=True)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                print("Sent headers", flush=True)
                
                if endpoint == "/dashboard/live":
                    response = json.dumps(state_data)
                elif endpoint == "/dashboard/kpis":
                    response = json.dumps(state_data.get("kpis", {}))
                elif endpoint == "/dashboard/alerts":
                    response = json.dumps(state_data.get("alerts", []))
                elif endpoint == "/dashboard/tables":
                    response = json.dumps(state_data.get("tables", []))
                elif endpoint == "/dashboard/staff":
                    response = json.dumps({
                        "staff_currently_visible": state_data.get("staff_currently_visible", 0),
                        "staff_currently_serving": state_data.get("staff_currently_serving", 0)
                    })
                elif endpoint == "/dashboard/timeline":
                    response = json.dumps(state_data.get("timeline", []))
                elif endpoint == "/dashboard/journeys":
                    journeys_path = os.path.join(run_path, "journeys_explainable.json")
                    journeys = []
                    print(f"Checking if journeys_path {journeys_path} exists", flush=True)
                    je_exists = os.path.exists(journeys_path)
                    print(f"Checked journeys_path exists: {je_exists}", flush=True)
                    if je_exists:
                        try:
                            print(f"Opening journeys_path {journeys_path}", flush=True)
                            with open(journeys_path, "r") as f:
                                print("Loading json journeys_path", flush=True)
                                journeys = json.load(f)
                                print("Loaded json journeys_path", flush=True)
                        except Exception as e:
                            print(f"Error loading journeys explainable: {e}", flush=True)
                            traceback.print_exc()
                    response = json.dumps(journeys)
                else:
                    response = json.dumps({"error": "Unknown endpoint"})
                    
                print(f"Writing response", flush=True)
                self.wfile.write(response.encode('utf-8'))
                print("REQUEST END - /dashboard/ complete", flush=True)
                return

            print("Delegating to super().do_GET()", flush=True)
            super().do_GET()
            print("super().do_GET() completed", flush=True)
            
        except Exception as e:
            print(f"EXCEPTION IN do_GET: {e}", flush=True)
            traceback.print_exc()
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def get_latest_run_dir(self):
        print("get_latest_run_dir START", flush=True)
        try:
            print(f"Checking if {RUNS_DIR} exists", flush=True)
            if not os.path.exists(RUNS_DIR):
                print(f"{RUNS_DIR} does not exist", flush=True)
                return None
            print(f"Listing directory {RUNS_DIR}", flush=True)
            files = os.listdir(RUNS_DIR)
            print(f"Listed directory {RUNS_DIR}: {files}", flush=True)
            subdirs = [os.path.join(RUNS_DIR, d) for d in files]
            subdirs = [d for d in subdirs if os.path.isdir(d)]
            if not subdirs:
                print("No subdirectories found", flush=True)
                return None
            print("Sorting subdirectories by mtime", flush=True)
            subdirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            print(f"Sorted subdirectories: {subdirs}", flush=True)
            return subdirs[0]
        except Exception as e:
            print(f"Exception in get_latest_run_dir: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return None

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
