# Aurika Enterprise Dashboard Component Guide
**UI Component Reference & Usage Manual v1.0.0**

## 1. Overview
The dashboard is constructed using modular, reusable React functional components styled with TailwindCSS utility classes and custom design tokens defined in `src/index.css`.

## 2. Shared Layout & Shell Components
### `<MainLayout />` (`src/layouts/MainLayout.tsx`)
- **Purpose**: Wraps all page routes with responsive navigation, sticky header bar, notification panel, and keyboard shortcut event listeners.
- **Props**: None (uses `Outlet` from `react-router-dom`).
- **Features**:
  - Auto-collapses sidebar on screens `< 768px`.
  - Integrates WebSocket connection state indicator (Green pinging badge for connected; Amber for simulation fallback).
  - Popover alert center showing top unread system alerts with severity badges.

## 3. Page Components
### `<LiveDashboard />` (`src/pages/LiveDashboard.tsx`)
- **Purpose**: Primary enterprise monitoring dashboard.
- **Key Sections**:
  - **KPI Summary Grid**: 4 cards displaying Occupancy rate with animated progress bar, Queue length with wait time estimates, Active vs Available table counts, and Back-of-House load indicators.
  - **Recommendation Center Preview**: Renders top unacknowledged DOE operational interventions with expected benefit metrics and evidence trails. Includes an interactive `Execute Action` button guarded by RBAC permissions.
  - **Live Alert Stream**: Right-hand column displaying recent system anomalies and sensor notifications.

### `<LiveFloorPlan />` (`src/pages/LiveFloorPlan.tsx`)
- **Purpose**: Real-time surveillance grid and seating management layout.
- **Interactivity**: Clicking any table marker selects the entity and populates the **Table Telemetry Inspector** panel on the right.
- **Mutations**: Operators can mutate table state (`AVAILABLE`, `OCCUPIED`, `RESERVED`, `DIRTY`) directly via control buttons.

### `<DigitalTwinView />` (`src/pages/DigitalTwinView.tsx`)
- **Purpose**: Restaurant Digital Twin inspection and state replay.
- **Features**: Interactive timeline scrubber input (`0%` opening to `100%` live present state) and live JSON state exporter.

### `<IdentityView />` (`src/pages/IdentityView.tsx`)
- **Purpose**: Canonical Identity Memory Engine database viewer.
- **Features**: Real-time search filtering across VIP guests, regular customers, and staff members, accompanied by visual spatial trajectory timelines.

### `<GlobalGraphView />` (`src/pages/GlobalGraphView.tsx`)
- **Purpose**: Interactive relationship graph powered by React Flow.
- **Node Types**: Styled custom nodes representing Guests (`#7e22ce`), Tables (`#0f766e`), Waiters (`#0369a1`), and POS Terminals (`#b45309`).

### `<AnalyticsView />`, `<ExperimentDashboard />`, & `<BenchmarkDashboard />`
- **Purpose**: Rendering historical KPI charts via `Chart.js` (`react-chartjs-2`) and scientific evaluation leaderboards across SOTA trackers.
