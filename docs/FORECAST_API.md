# Predictive Intelligence & Forecasting API Reference

## Overview
The **Forecast API Service** (`predictive_engine/api/forecast_service.py`) exposes predictive telemetry, what-if simulations, and multi-format reporting to enterprise clients and the operational dashboard.

---

## 1. Get Live Operational Forecasts
**Endpoint**: `GET /api/v1/forecast/now`  
**Description**: Returns multi-horizon projections (`+5m`, `+10m`, `+30m`, `+60m`) across arrivals, occupancy, queue dynamics, staff workload, proactive alerts, and capacity plans.

### Response Payload
```json
{
  "status": "SUCCESS",
  "horizons": [5, 10, 30, 60],
  "arrivals": {
    "30": {
      "expected_arrival_rate_per_hour": 35.0,
      "rush_hour_probability": 0.65,
      "party_size_distribution": { "1_guest": 10.0, "2_guests": 45.0, "3_to_4_guests": 30.0, "5_plus_guests": 15.0 }
    }
  },
  "queue": {
    "30": {
      "predicted_queue_length": 14.5,
      "avg_waiting_time_minutes": 18.2,
      "overflow_probability": 0.12,
      "is_bottleneck_predicted": false
    }
  },
  "proactive_alerts": [
    {
      "alert_id": "alert-queue-30m-1720120000",
      "alert_type": "QUEUE_BOTTLENECK",
      "severity": "WARNING",
      "horizon_minutes": 30,
      "title": "Impending Queue Bottleneck (+30m)",
      "description": "Host queue is predicted to reach 26 waiting guests in 30 minutes.",
      "recommended_action": "Deploy secondary seating host immediately."
    }
  ]
}
```

---

## 2. Execute What-If Scenario Simulation
**Endpoint**: `POST /api/v1/simulate/what-if`  
**Description**: Executes an interactive simulation by applying perturbation parameters to current baseline telemetry.

### Request Body
```json
{
  "scenario_type": "SURGE_30_GUESTS",
  "base_arrival_rate": 35.0,
  "active_waiters": 6,
  "custom_arrival_delta": 30.0
}
```

### Response Payload
```json
{
  "status": "SUCCESS",
  "simulation_result": {
    "scenario_name": "SURGE_30_GUESTS",
    "perturbation_description": "Sudden customer arrival surge: +30 guests/hour arrival rate.",
    "predicted_queue": {
      "30": { "predicted_queue_length": 28.5, "avg_waiting_time_minutes": 34.0 }
    }
  }
}
```

---

## 3. Generate & Export Operational Forecast Report
**Endpoint**: `GET /api/v1/forecast/report?report_type=HOURLY_FORECAST&format=PDF`  
**Description**: Generates an executive forecast report and exports to `JSON`, `CSV`, or `PDF`/`HTML`.

### Parameters
- `report_type`: `HOURLY_FORECAST`, `DAILY_SUMMARY`, or `PEAK_HOUR_ANALYSIS`
- `format`: `JSON`, `CSV`, or `PDF`
- `output_filepath`: Optional file path on the server for PDF/HTML output saving.

### Response Payload
```json
{
  "status": "SUCCESS",
  "format": "PDF",
  "filepath": "/tmp/aurika_forecast_report.pdf",
  "success": true
}
```
