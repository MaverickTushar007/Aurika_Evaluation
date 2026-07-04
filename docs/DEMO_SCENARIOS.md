# Demo Scenarios

These scripted scenarios are designed to showcase Aurika to prospective clients. They follow the core **Observe -> Evaluate -> Decide** workflow.

## Scenario 1: Normal Operations
**Setup**: The restaurant is below 50% capacity, queues are empty.
**Observe**: Tracker seamlessly classifies staff and guests.
**Evaluate**: `MetricsEngine` reports low queue times, `ROSE` calculates a Health Score of 100/100.
**Decide**: The Operational Intelligence Layer outputs: "No active alerts. Operations nominal."
**Copilot Demo**:
- *User*: "What operational issues require attention?"
- *Copilot*: "There are no operational issues requiring attention. The restaurant health is 100/100, operating smoothly."

## Scenario 2: Lunch Rush
**Setup**: Sudden influx of 8 guests into the Waiting Area. Staff utilization hits 99%.
**Observe**: Tracker identifies large clusters in the "Waiting Area" polygon.
**Evaluate**: Wait times exceed the 10-minute SLA. Health Score drops to 60/100.
**Decide**: `OperationalIntelligenceLayer` generates `QUEUE_SLA_BREACH` and `HOST_OVERLOADED`.
**Copilot Demo**:
- *User*: "Which recommendation has the highest priority?"
- *Copilot*: "The highest priority recommendation is to 'Deploy second host or open additional waiting area'."
- *User*: "Why was this generated?"
- *Copilot*: "This recommendation was generated because: Rule QUEUE_SLA_BREACH triggered by average_wait_time. The evidence shows average_wait_time = 720.0s."

## Scenario 3: Operational Bottleneck
**Setup**: A tracking glitch or pipeline error forces an illegal state transition (e.g., WAITING -> EXITED).
**Observe**: The `StateEngine` catches the invalid transition and publishes a `SystemDiagnosticEvent`.
**Evaluate**: `ROSE` captures the diagnostic event, degrading the system health score.
**Decide**: `OperationalIntelligenceLayer` issues a HIGH severity alert for System Instability.
**Copilot Demo**:
- *User*: "Why is the restaurant health low?"
- *Copilot*: "The health is degraded due to active system diagnostic alerts regarding illegal state transitions."
