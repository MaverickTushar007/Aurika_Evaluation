# Configuration Guide

Aurika is designed to be configurable by operations managers, not just software engineers. All critical business logic is abstracted into declarative JSON files.

## 1. Rules Configuration (`configs/rules.json`)
The Operational Intelligence layer reads this file to determine when to trigger alerts and recommendations.

### Schema
- `rule_id`: Unique identifier for the rule.
- `severity`: INFO, WARNING, HIGH, or CRITICAL.
- `priority`: Integer (1 is highest priority).
- `conditions`:
  - `metric`: The exact metric name matching an attribute in the `RestaurantSnapshot`.
  - `operator`: ">", "<", or "==".
  - `threshold`: The value to compare against.
- `recommendation_template`: The action and impact text to display.

**Example: Queue SLA Breach**
```json
{
  "rule_id": "QUEUE_SLA_BREACH",
  "severity": "CRITICAL",
  "priority": 1,
  "conditions": {
    "metric": "average_wait_time",
    "operator": ">",
    "threshold": 300
  },
  "recommendation_template": {
    "action": "Deploy second host or open additional waiting area",
    "impact": "Reduces queue time and prevents guest abandonment"
  }
}
```

## 2. Zone Configuration (`configs/zones.json`)
Zones map pixel coordinates to semantic restaurant areas.

**Format**:
```json
{
    "Entrance": [[0, 0], [200, 0], [200, 1080], [0, 1080]],
    "Waiting Area": [[482, 0], [800, 0], [800, 400], [482, 400]]
}
```
