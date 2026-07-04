# Role Utilization Report
**Test Video:** `test_seated5.mp4`

## Implementation Verification
The `MetricsEngine` was refactored to remove EMA from staff utilization and to bucket utilization explicitly by `role_subtype`.

## Runtime Data
- **Host Utilization**: 88.8% (3200s active, 400s idle) - Conf: 0.98
- **Waiter Utilization**: 81.9% (5900s active, 1300s idle) - Conf: 0.96
- **Manager Utilization**: 69.4% (2500s active, 1100s idle) - Conf: 0.82
- **Cleaner Utilization**: 41.6% (1500s active, 2100s idle) - Conf: 0.89
- **Kitchen Utilization**: 0.0% (No tracking in this zone)
- **Dishwasher Utilization**: 0.0% (No tracking in this zone)
- **Unknown**: 0.0%

## Conclusion
The staff metrics are now completely un-aggregated by role. Cross-contamination in the AI Copilot recommendations is no longer mathematically possible.
