# Capacity Planning & Operational Resource Allocation

## Overview
The **Capacity Planner** (`capacity_planning/capacity_planner.py`) translates predictive telemetry into prescriptive, actionable resource management plans across 5, 10, 30, and 60-minute horizons.

## Resource Allocation Strategies

### 1. Dynamic Staffing Adjustments
The engine continuously compares forecasted foot traffic against staff workload indices:
- **Waiter Workload Index**: When predicted guest volume exceeds $15\text{ guests/waiter}$ (index $\ge 90\%$), the system recommends staging $+1$ to $+3$ standby waiters.
- **Busser Demand**: When departing guest rates exceed $25\text{ tables/hr}$, expedited busing alerts are dispatched to clear tables within 3 minutes.
- **Kitchen Workload**: When order arrival velocity pushes kitchen load $\ge 85\%$, recommendation is issued to open the secondary prep station.

### 2. Party Size Table Allocation Strategy
By forecasting party size distributions (`ArrivalPredictionEngine`), the planner optimizes floor layout ratios before guests arrive:
- **Couples / 2-Top Priority**: During lunch rushes (11:00–14:00) where couple/solo dining exceeds 60%, the system advises splitting modular 4-top tables into 2-tops.
- **Large Banquet Allocation**: During dinner rushes (18:00–21:00), 20% of peripheral dining sections are reserved and merged for parties of 5+ guests.

### 3. Queue Limits & Overflow Protocols
- **Standard Seating**: Maintained when average wait times are $< 25\text{ minutes}$.
- **SMS Virtual Waitlist Activation**: Recommended immediately when predicted wait times exceed $35\text{ minutes}$ or queue length hits $30\text{ parties}$, preventing physical lobby congestion.
- **Overflow Patio Seating**: Recommended when dining room table utilization hits $95\%$.
- **Temporary Section Closure**: Advised during off-peak afternoon lulls when table utilization drops $< 25\%$ across $+30\text{m}$ horizons, conserving HVAC and labor costs.
