# Aurika Phase 18: Pilot Deployment Report

**Deployment ID:** `PDRV-65D3356F`
**Restaurant:** Aurika Pilot Bistro & Bar (Bistro-54) (San Francisco, CA (Production Flagship))
**Status:** `ONLINE` | **Active Cameras:** 6/6

## 1. System Topology & RTSP Stream Configuration
Aurika was deployed across 6 live RTSP camera streams monitoring Dining Room North/South, Queue Entrance, Patio West, Kitchen Pass, and Bar Lounge.
```
[RTSP Streams (1080p@30fps)] ---> [Edge Inference Node (NVIDIA TensorRT)] ---> [Redis State Bus] ---> [Digital Twin / Decision Engine]
```

## 2. Camera Calibration & Acceptance Results
| Camera ID | FOV Coverage | Blind Spot Area | Homography Error | Status |
|---|---|---|---|---|
| `CAM_DINING_PRIMARY` | 94.5% | 1.2 sqm | 1.15 px | `ACCEPTED_PRODUCTION_READY` |
| `CAM_DINING_SECONDARY` | 88.2% | 3.8 sqm | 1.85 px | `ACCEPTED_WITH_WARNINGS` |
| `CAM_QUEUE_WAITING` | 94.5% | 1.2 sqm | 1.15 px | `ACCEPTED_PRODUCTION_READY` |
| `CAM_PATIO_OUTDOOR` | 88.2% | 3.8 sqm | 1.85 px | `ACCEPTED_WITH_WARNINGS` |

## 3. Privacy & Security Compliance Audit
**Overall Compliance:** `FULL_ENTERPRISE_COMPLIANCE` (6/6 rules verified).
- **CCTV Video Retention Policy:** `72 Hours Max (Automated Purge)` (COMPLIANT)
- **Structured Telemetry & Graph Snapshots:** `90 Days Max` (COMPLIANT)
- **Facial Embedding ReID Vectorization:** `Non-reversible 512-d float array` (COMPLIANT)
- **Role-Based Access Control (RBAC):** `Strict Operator/Manager separation` (COMPLIANT)
- **API Token Authentication & Audit Logs:** `OAuth2 JWT with immutable audit trail` (COMPLIANT)
- **Data-in-Transit & Data-at-Rest Encryption:** `TLS 1.3 / AES-256-GCM` (COMPLIANT)
