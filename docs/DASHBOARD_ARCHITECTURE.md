# Aurika Enterprise Operations Dashboard Architecture
**Canonical Specification v1.0.0**

## 1. System Overview & Role
The **Aurika Enterprise Operations Dashboard** (`dashboard/`) serves as the official frontend command center for Project Aurika. It transforms high-throughput computer vision surveillance telemetry, Multi-Evidence Fusion Engine (MFE) probabilistic states, Identity Memory Engine (IME) records, and Restaurant Digital Twin (RDT) world models into actionable, visual business intelligence for restaurant operators and research engineers.

```
+-------------------------------------------------------------------------+
|                  AURIKA ENTERPRISE DASHBOARD (SPA)                      |
|  React 19 • TypeScript • Vite • Zustand • TanStack Query • React Flow   |
+-------------------------------------------------------------------------+
       ^                                                 ^
       | HTTP REST / JSON                                | WebSocket Event Stream
       v                                                 v
+-------------------------------------------------------------------------+
|                 AURIKA INTELLIGENCE PLATFORM (AIP)                      |
|  FastAPI Gateway • Pub/Sub Event Bus • RBAC Auth • Storage Repository   |
+-------------------------------------------------------------------------+
       ^                                                 ^
       |                                                 |
+--------------+   +--------------+   +--------------+   +--------------+
| VIL Pipeline |   | MFE / ReID   |   | RDT Engine   |   | DOE Engine   |
+--------------+   +--------------+   +--------------+   +--------------+
```

## 2. Architectural Design Principles
1. **Zero Backend Coupling**: The frontend consumes REST APIs (`/api/v1/*`) and WebSocket streams (`ws://localhost:8000/ws`) exclusively. It does NOT implement computer vision inference, ReID algorithms, or direct database access.
2. **Deterministic State Machine**: State is partitioned into two distinct Zustand stores:
   - `useAuthStore`: Manages JWT tokens, user identities, session persistence, and Role-Based Access Control (RBAC).
   - `useWorldStore`: Manages the real-time Restaurant Digital Twin (RDT) state, active table telemetry, queue dynamics, operational recommendations, and system alerts.
3. **Resilient Offline Fallback**: In environments where the upstream AIP Gateway is offline or disconnected, `wsClient.ts` automatically transitions to an enterprise local simulation engine, synthesizing continuous queue fluctuations, table turnover events, and FPS jitters to maintain UI responsiveness and developer testing capability.

## 3. Core Module Breakdown
- **`src/layouts/MainLayout.tsx`**: The main application shell providing collapsible sidebar navigation, top status bar with live FPS telemetry, quick theme switching (Dark/Light mode), notification popover, and keyboard shortcuts (`⌘K` Map, `⌘D` Dashboard).
- **`src/pages/LiveDashboard.tsx`**: Command center aggregating real-time occupancy, host queue depth, wait times, kitchen ticket pressure, and priority DOE recommendations.
- **`src/pages/LiveFloorPlan.tsx`**: Responsive interactive surveillance grid rendering table statuses (`AVAILABLE`, `OCCUPIED`, `RESERVED`, `DIRTY`), guest counts, waiter assignments, and zone densities.
- **`src/pages/DigitalTwinView.tsx`**: RDT state inspector featuring timeline scrubbing, state replay, and JSON world export.
- **`src/pages/IdentityView.tsx`**: Searchable canonical identity database tracking VIP guests, staff, and visitors across synchronized spatial trajectories and visual embeddings.
- **`src/pages/GlobalGraphView.tsx`**: Network graph built with React Flow representing relationships between guests, staff, tables, and POS transactions.
- **`src/pages/AnalyticsView.tsx`**: Chart.js graphs modeling occupancy vs. queue volume, wait time trends, and section utilization heatmaps.
- **`src/pages/ExperimentDashboard.tsx` & `BenchmarkDashboard.tsx`**: Research laboratories comparing SOTA tracking metrics (HOTA, MOTA, IDF1, FPS, identity switches) across ByteTrack, BoT-SORT, BoxMOT, OC-SORT, and Aurika.
- **`src/pages/ReportsView.tsx` & `SettingsView.tsx`**: Business intelligence report generator with CSV/JSON/PDF exports and administrator rule configuration.

## 4. Role-Based Access Control (RBAC) Hierarchy
The dashboard enforces strict permission barriers across UI components:
| Role | Live Monitoring | Floor Plan Action | Acknowledge Recs | Config Mutations |
| :--- | :---: | :---: | :---: | :---: |
| **Administrator** | Full Access | Yes | Yes | Yes |
| **Operator** | Full Access | Yes | Yes | Read-only |
| **Research** | Full Access | Read-only | Read-only | Read-only |
| **Audit** | Full Access | Read-only | Read-only | Read-only |
| **Read-only** | Full Access | Read-only | Read-only | Read-only |
