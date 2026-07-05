# Aurika WebSocket Validation Report
**Phase 18 TAPP Program**

## 1. FastAPI WebSocket Service Route
- **Endpoint:** Exposed `@app.websocket("/ws")` in `api/main.py`.
- **Connection Manager:** Implemented a thread-safe connection manager that keeps track of active connections. It supports broadcasting messages across all dashboard instances simultaneously.
- **Client-Server Protocol:** Dashboards send a connection request, maintaining a continuous socket tunnel to fetch raw telemetry notifications directly from backend event streams (Table occupied/available, queue levels, alert triggers).

## 2. Frontend De-Mocking
- **Production Mode Override:** Edited `wsClient.ts` to inspect the build context. When the dashboard runs in production mode, the script overrides `startMockFallback()` entirely. 
- **Effect:** If the WebSocket connection to the backend fails, the dashboard will now show a connection failure error rather than silently generating fake data. This ensures absolute trust in the metrics displayed topaying customers.
