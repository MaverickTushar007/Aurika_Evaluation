# What-If Scenario Simulation Guide

## Overview
The **What-If Simulation Engine** (`simulation/what_if_engine.py`) allows restaurant operators and research scientists to test operational resilience against sudden disruptions or demand surges without risking real-time operations.

## Available Simulation Presets
1. **`SURGE_30_GUESTS` (Customer Arrival Surge)**:
   - *Perturbation*: Adds $+30\text{ guests/hr}$ to baseline arrival rate and an immediate $+15$ party jump in the host queue.
   - *Use Case*: Evaluating whether current waitstaff and table turnover rates can absorb sudden tour bus arrivals or event discharges.
2. **`WAITER_LEAVES` (Staff Attrition / Shift Loss)**:
   - *Perturbation*: Reduces active waitstaff count by $-1$ waiter during peak dining hours.
   - *Use Case*: Testing workload saturation indices and identifying when service delays will cascade into table turnaround bottlenecks.
3. **`CAMERA_FAILS` (Surveillance Sensor Failure)**:
   - *Perturbation*: Simulates loss of 1 primary surveillance camera, increasing tracking uncertainty and queue estimation buffers.
   - *Use Case*: Validating multi-camera handover resilience and blind-spot coverage warnings.
4. **`CLOSE_VIP_SECTION` (Dining Section Closure)**:
   - *Perturbation*: Reduces total facility seating capacity by $-30\text{ seats}$ (e.g., closing VIP dining for private banquets).
   - *Use Case*: Checking dining room saturation rates and queue overflow probabilities when operating at reduced capacity.
5. **`CUSTOM` (Interactive Slider Overrides)**:
   - *Perturbation*: Custom combinations of arrival rate deltas ($-30$ to $+60$), waiter staff deltas ($-3$ to $+3$), and seating capacity modifications.

## Executing Simulations via Python API
```python
from predictive_engine.simulation.what_if_engine import WhatIfSimulationEngine

sim = WhatIfSimulationEngine()
result = sim.simulate_scenario(
    scenario_type="SURGE_30_GUESTS",
    base_arrival_rate=35.0,
    active_waiters=6
)

print(f"Scenario: {result.scenario_name}")
print(f"30m Queue Forecast: {result.predicted_queue[30].predicted_queue_length} parties")
print(f"Generated Alerts: {len(result.generated_alerts)}")
```
