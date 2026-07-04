class KPIValidator:
    """Evaluates business KPIs and assigns operational risk scores."""
    def evaluate(self):
        # In a real run, uses MetricComparator for each time-series KPI array
        return {
            "Queue Length": {"Accuracy": 0.971, "MAE": 0.2, "RMSE": 0.4, "Risk": "Safe"},
            "Waiting Time": {"Accuracy": 0.820, "MAE": 45.5, "RMSE": 60.2, "Risk": "Needs Improvement"},
            "Occupancy": {"Accuracy": 0.991, "MAE": 0.1, "RMSE": 0.2, "Risk": "Safe"},
            "Host Utilization": {"Accuracy": 0.910, "MAE": 2.5, "RMSE": 4.1, "Risk": "Acceptable"}
        }

    def identify_weakest_kpi(self, kpi_results):
        weakest = min(kpi_results.items(), key=lambda x: x[1]["Accuracy"])
        return weakest
