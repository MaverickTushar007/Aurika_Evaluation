# Aurika Phase 15: Predictive Intelligence & Forecasting Engine

## Overview
The **Predictive Intelligence & Forecasting Engine** (`predictive_engine/`) equips Project Aurika with predictive foresight, enabling the platform to shift from reactive monitoring ("What is happening now?") to proactive management ("What will happen in the next 5, 10, 30, and 60 minutes?").

## Architecture
The Predictive Engine operates as an overlay intelligence layer that ingests historical telemetry from the Restaurant Digital Twin (RDT), Multi-Evidence Fusion Engine (MFE), and Global Identity Graph (GIG) without modifying their internal architectures.

```
+-----------------------------------------------------------------------------------+
|                           PREDICTIVE ENGINE OVERLAY                               |
+-----------------------------------------------------------------------------------+
|  [Arrival Engine] -> [Queue Theory M/M/c] -> [Occupancy Engine] -> [Staff Load]   |
|         |                     |                      |                   |        |
|         v                     v                      v                   v        |
|  [Time Series HW]    [Anomaly Forecaster]    [Turnover Optim.]   [Capacity Plan]  |
+-----------------------------------------------------------------------------------+
                                   |
         +-------------------------+-------------------------+
         |                         |                         |
         v                         v                         v
+-------------------+     +-------------------+     +-------------------+
|  Decision Engine  |     |   Digital Twin    |     | Live Dashboard    |
|  Proactive Alerts |     | Future World State|     | /forecast View    |
+-------------------+     +-------------------+     +-------------------+
```

## Core Subsystems
1. **Time-Series Engine (`forecasting/`)**: Implements Holt's Double Exponential Smoothing with trend damping and 95% confidence intervals across standard operational horizons (`+5m`, `+10m`, `+30m`, `+60m`).
2. **Arrival Prediction (`arrival_prediction/`)**: Analyzes Poisson arrival inflows, party size distributions (solos, couples, families, banquets), and rush hour probabilities.
3. **Queue Forecasting (`queue_prediction/`)**: Projects lobby waiting times and overflow risks using M/M/c queueing theory and Erlang C formulations.
4. **Occupancy & Table Utilization (`occupancy_prediction/`)**: Prohibits dining room saturation by predicting zone-level guest densities and table utilization percentages.
5. **Staff Workload Forecasting (`staff_prediction/`)**: Translates projected foot traffic into workload stress indices (0–100%) for waiters, kitchen cooks, cashiers, and bussers.
6. **Proactive Anomaly Forecaster (`alert_prediction/`)**: Issues early-warning alerts for impending queue bottlenecks, table shortages, overcrowding, and service delays.
7. **Capacity Planning (`capacity_planning/`)**: Synthesizes forecasts into prescriptive recommendations (extra staff staging, table allocation ratios, SMS virtual queue triggers).
8. **What-If Scenario Simulator (`simulation/`)**: Executes interactive Monte Carlo perturbation tests (customer surges, staff attrition, sensor failures, section closures).

## Zero-Rewrite Downstream Adapters
- **DOE Proactive Adapter**: Enriches current operational actions with predictive justifications or urgent overrides when future bottlenecks are identified.
- **RDT Future State Adapter**: Embeds multi-horizon `future_world_state` trajectories and predicted bottleneck logs into real-time Digital Twin state payloads.
- **Forecast API Service**: Exposes REST/JSON endpoints (`/api/v1/forecast/now`, `/api/v1/simulate/what-if`) and multi-format reporting (`JSON`, `CSV`, `PDF`).
