# Aurika Implementation Gaps & Missing Logic

## 1. Missing WebSockets Ingestion In APIs
- **Gap:** The React dashboard UI makes a WebSocket connection request to `ws://localhost:8000/ws`.
- **Reality:** No `@app.websocket` route exists in `server.py`, `api/main.py`, or `analytics_api.py`. The connection is instantly refused, forcing the dashboard to run in fallback client-side simulation.

## 2. Empty Decision Engine evaluation
- **Gap:** The operational loops do not run `DecisionEngine.evaluate_state()` because it is left unimplemented as a `pass` stub.

## 3. Disconnected Pilot Subsystem
- **Gap:** The newly added `pilot/` directory has no code pathways connecting it to the FastAPI servers in `api/` or `analytics_api.py`. It is a detached module that runs only via the offline Python script `run_pilot_deployment.py`.
