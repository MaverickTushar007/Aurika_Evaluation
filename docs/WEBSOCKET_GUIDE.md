# Aurika Real-Time Telemetry & WebSocket Guide
**Streaming Protocol & Simulation Reference v1.0.0**

## 1. Connection Protocol
The dashboard connects to the Aurika Intelligence Platform (AIP) Event Gateway via persistent WebSocket connections:
- **Endpoint**: `ws://localhost:8000/ws`
- **Client Implementation**: `src/websocket/wsClient.ts` (`AurikaWebSocketClient` class singleton).
- **Auto-Reconnection**: If the connection drops or the gateway server is restarted, the client automatically re-attempts connection every `3000 ms`.

## 2. Event Subscription Topics
The client listens for JSON-encoded payloads structured by topic:

### A. Table Occupancy Mutations (`TableOccupied` / `TableAvailable`)
Emitted when the Multi-Evidence Fusion Engine (MFE) confirms a guest party has seated or departed.
```json
{
  "topic": "TableOccupied",
  "tableId": "T1",
  "guests": 2,
  "confidence": 0.99,
  "timestamp": "2026-07-04T23:15:00Z"
}
```

### B. Continuous KPI Telemetry (`KPIUpdate`)
Emitted by the Restaurant Digital Twin (RDT) at 1 Hz intervals.
```json
{
  "topic": "KPIUpdate",
  "data": {
    "currentOccupancy": 48,
    "queueLength": 5,
    "expectedWaitMinutes": 12,
    "activeTables": 4,
    "availableTables": 3,
    "inferenceFps": 29.8
  }
}
```

### C. Anomaly Alerts (`AlertRaised`)
Emitted when threshold rules are violated across surveillance zones.
```json
{
  "topic": "AlertRaised",
  "alert": {
    "severity": "CRITICAL",
    "title": "Kitchen Queue Bottleneck",
    "description": "Expo ticket latency exceeded 15 minutes.",
    "location": "Kitchen Zone"
  }
}
```

## 3. Local Live Simulation Engine (Offline Fallback)
When developing offline or testing UI responsiveness without running the Dockerized production runtime (`docker compose up`), `wsClient.ts` initializes an autonomous simulation loop:
- **Interval**: Fires every `3500 ms`.
- **Behavior**: Synthesizes realistic FPS jitters between `28.9` and `30.7 FPS`, fluctuates host stand queue depth, updates expected wait times dynamically, and toggles table occupancy statuses to demonstrate real-time reactivity.
