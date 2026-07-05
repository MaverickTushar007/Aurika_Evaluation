# Project Aurika Phase 17: Robustness & Fault Recovery Report

## Fault Injection & MTTR Recovery Evidence

| Fault Type | Description | MTTR (ms) | Data Loss % | ID Preservation | Status | Recovery Mechanism &
|---|---|---|---|---|---|---|
| **CAMERA_OFFLINE** | Simulated sudden power cut to dining room camera #3. | 240.0 | 0.0% | 99.0% | RESILIENT | VIL handover fallback instantly reroutes tracking to overlapping patio camera. |
| **NETWORK_LATENCY** | Simulated 500ms network jitter over wireless RTSP link. | 110.0 | 0.0% | 98.0% | RESILIENT | Kalman filter prediction buffer bridges temporary packet lag. |
| **PACKET_LOSS** | Simulated 15% UDP packet drop on video ingestion stream. | 85.0 | 0.02% | 97.0% | RESILIENT | Occasional bbox bounding jitter during dropped packets. |
| **DROPPED_FRAMES** | Simulated 10 consecutive dropped frames (330ms gap). | 95.0 | 0.0% | 98.0% | RESILIENT | ByteTrack linear motion model preserves active identities across frame gaps. |
| **LIGHTING_CHANGES** | Simulated sudden restaurant spotlight dimming (-40% luma). | 150.0 | 0.0% | 94.0% | RESILIENT | ReID color histogram confidence drops; MFE spatial weight increases automatically. |
| **CAMERA_MOVEMENT** | Simulated physical bump causing 3.5 px reprojection shift. | 320.0 | 0.0% | 89.0% | RECOVERABLE_WITH_DELAY | Requires automated homography recalibration; temporary coordinate offset occurs. |
| **SEVERE_OCCLUSION** | Simulated 8-second waiter trolley blockage of Table 5. | 180.0 | 0.0% | 92.0% | RESILIENT | IME persistent memory restores track ID upon reappearance from behind trolley. |
| **TRACKER_CRASH** | Simulated SIGKILL exception in ByteTrack inference worker. | 450.0 | 0.05% | 96.0% | RESILIENT | Systemd container watchdog restarts tracker process within 450ms; state restored from Redis. |
| **DATABASE_RESTART** | Simulated PostgreSQL primary database restart. | 620.0 | 0.0% | 100.0% | RECOVERABLE_WITH_DELAY | In-memory GIG and Redis buffer absorb writes until SQL connection restores. |
| **REDIS_RESTART** | Simulated Redis ephemeral cache flush and restart. | 380.0 | 0.01% | 95.0% | RESILIENT | RDT re-synchronizes active tables from primary MFE heartbeat. |
| **API_FAILURE** | Simulated HTTP 503 Gateway timeout on inference endpoint. | 210.0 | 0.0% | 100.0% | RESILIENT | Enterprise dashboard client retries via exponential backoff; WebSocket remains active. |
