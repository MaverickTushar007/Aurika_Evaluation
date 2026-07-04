import math

class MetricComparator:
    """Computes MAE, RMSE, and MAPE for numerical KPI comparisons."""
    @staticmethod
    def compute_mae(y_true, y_pred):
        if not y_true: return 0.0
        return sum(abs(t - p) for t, p in zip(y_true, y_pred)) / len(y_true)
        
    @staticmethod
    def compute_rmse(y_true, y_pred):
        if not y_true: return 0.0
        return math.sqrt(sum((t - p)**2 for t, p in zip(y_true, y_pred)) / len(y_true))
        
    @staticmethod
    def compute_mape(y_true, y_pred):
        if not y_true: return 0.0
        errors = [abs((t - p) / t) for t, p in zip(y_true, y_pred) if t != 0]
        return (sum(errors) / len(errors)) * 100 if errors else 0.0
