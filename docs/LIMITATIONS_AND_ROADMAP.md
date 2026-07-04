# Limitations and Roadmap

Aurika v1.0 establishes a pristine, production-ready architecture. However, to maintain absolute honesty regarding system capabilities, the following limitations are explicitly documented.

## Current Limitations

1. **Single-Camera Identity**: The system currently relies on continuous tracker IDs. If a guest walks off-camera and returns, they are tracked as a new `Visit`.
2. **No Cross-Camera Re-ID**: Tracking cannot seamlessly hand off guests between overlapping camera fields of view.
3. **Appearance-Only Staff Identification**: Staff are identified using color thresholding (e.g., detecting uniforms). This can yield false positives if a guest wears an identical color.
4. **Static Zones**: Zones are drawn as static 2D polygons on the frame. If the camera is bumped or moved, the zones must be manually recalibrated.
5. **No POS/Reservation Integration**: The system does not yet link computer-vision metrics with actual Point of Sale revenue or OpenTable reservation data.
6. **No Forecasting**: Intelligence is purely real-time and reactive. It does not yet predict queue lengths 30 minutes into the future.

## Future Roadmap

### v1.1: Multi-Camera Re-ID
- Integration of Deep SORT / OSNet to generate cross-camera appearance embeddings, allowing the `VisitManager` to stitch fractured tracks into singular guest journeys.

### v1.2: POS & KDS Integration
- Webhooks to listen to Toast POS or Kitchen Display Systems. This will allow the `StateEngine` to validate transitions (e.g., moving a guest from WAITING to DINING exactly when the host marks the table as seated in the POS).

### v2.0: Predictive Intelligence
- Implementing a time-series forecasting model that consumes historical `RestaurantSnapshots` to alert managers *before* a queue forms.
