# Aurika Version 2.0: Prioritized Engineering Roadmap

Derived exclusively from real operational evidence, incident logs, and operator feedback gathered during the Phase 18 Pilot Deployment.

## Priority 1: Instantaneous Group Surge Compensation (V2-01)
- **Evidence:** Incident `INC-2026-004` (Bus tour queue surge caused temporary 30m forecast MAPE spike).
- **Action:** Incorporate real-time optical group sizing into the queue entrance predictor to dynamically adjust wait-time models within 5 seconds of crowd arrival.

## Priority 2: Multi-Angle Fill Camera Calibration Support (V2-02)
- **Evidence:** Calibration Test `BLIND-SPOT-02` on Patio West showed 3.8 sqm unmonitored floor area.
- **Action:** Extend homography coordinate mapping in `multi_camera/` to support up to 4 wide-angle fish-eye fill cameras per zone without increasing edge GPU memory overhead.

## Priority 3: Interactive Hostess Booth/Table Constraint Filtering (V2-03)
- **Evidence:** Shadow Mode disagreement analysis (`SHADOW-003`) showed 11.5% override rate due to table type preferences.
- **Action:** Add real-time constraint toggle badges (Booth, Window, High-Top, Quiet Zone) to the Enterprise Dashboard Decision Engine UI.

## Priority 4: Zero-Touch TCP/RTSP Fallback Buffering (V2-04)
- **Evidence:** Incident `INC-2026-002` (Temporary Wi-Fi packet loss on outdoor patio stream).
- **Action:** Implement a 5-second circular frame buffer in the edge ingestion adapter to prevent track fragmentation during transient network jitter.
