# Aurika False Assumptions & Claims

## 1. Real-World Multi-Camera Calibration Data
- **Claim:** "Evaluated adjacent camera overlap ratios and calculated sub-pixel homography error."
- **Reality:** In `calibration_wizard.py`, camera coverage is hardcoded as `94.5%` or `88.2%` with a fallback warning block. No physical coordinate calibrations are calculated.

## 2. A/B Test Significance
- **Claim:** "A/B test completed over 28 days with p-values of 0.0012 and 0.0004 proving statistical superiority."
- **Reality:** The metrics in `ab_test_engine.py` are static floats declared in a list inside the class constructor. No statistical tests (e.g. t-test, Mann-Whitney U) are executed on live telemetry.

## 3. SQLite vs. PostgreSQL Deployment
- **Claim:** "Production database PostgreSQL runs with connection pools and volume encryption."
- **Reality:** Runtimes like `process.py` and `server.py` connect exclusively to a local SQLite file (`db/customer_intel.db`).
