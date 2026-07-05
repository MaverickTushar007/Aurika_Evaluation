# Environmental & Model Drift Detection Engine

The Drift Detection Monitor (`continuous_learning/drift_detection/`) continuously evaluates real-world operational telemetry against production baselines to detect distribution shift and model decay.

## Monitored Drift Dimensions
1. **Camera Spatial Drift (`CAMERA_DRIFT`)**:
   - Detects physical camera movement, vibration, or mount sagging by measuring reprojection error divergence ($\ge 25\%$ over baseline).
2. **Illumination & Lighting Shifts (`LIGHTING_DRIFT`)**:
   - Monitors average frame luma and contrast across day/night cycles or sudden exposure failures.
3. **Seasonal Demand Skew (`SEASONAL_SHIFT`)**:
   - Tracks long-term guest arrival volume variance vs historical Poisson baselines.
4. **Occupancy Variance (`OCCUPANCY_SHIFT`)**:
   - Monitors table utilization percentage and dining room density spikes.
5. **Customer Behavior Shifts (`CUSTOMER_BEHAVIOR`)**:
   - Identifies party size distribution changes and linger time variance.
6. **Prediction Error Degradation (`PREDICTION_ERROR`)**:
   - Monitors rolling MAPE and RMSE on queue wait time and occupancy forecasts. A MAPE increase $>25\%$ triggers an automated alert.
7. **Model Precision Decay (`MODEL_DEGRADATION`)**:
   - Identifies tracking ID switch spikes or ReID embedding precision drop ($>10\%$ drop below baseline).

## Automated Remediation Workflow
- **`WARNING` Severity**: Emits a dashboard alert and schedules an automated regression benchmark.
- **`CRITICAL` Severity**: Flags immediate drift report, triggers urgent automated dataset curation via `MultiFormatDatasetBuilder`, and alerts operators to review candidate training samples.
