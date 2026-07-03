# analytics_api.py
"""
FastAPI REST API serving live business metrics, queue stats, spatial layouts,
and executive reports for the Business Intelligence Layer.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import os

from analytics_engine import AnalyticsEngine
from report_generator import ReportGenerator
from copilot_engine import AICopilotEngine
from pydantic import BaseModel

app = FastAPI(title="Restaurant Analytics BI Platform", version="3.0.0")

# Enable CORS for local React dashboard development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines
db_path = "db/customer_intel.db"
engine = AnalyticsEngine(db_path)
reporter = ReportGenerator(db_path)
copilot = AICopilotEngine(db_path)

class QueryModel(BaseModel):
    question: str

@app.post("/ai/query")
def post_ai_query(body: QueryModel):
    """Executes natural-language routing questions via POST."""
    try:
        return {"answer": copilot.route_query(body.question)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ai/query")
def get_ai_query(question: str):
    """Executes natural-language routing questions via GET."""
    try:
        return {"answer": copilot.route_query(question)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ai/daily-summary")
def get_ai_summary():
    """Generates shift and executive KPI summaries."""
    try:
        return copilot.generate_daily_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ai/alerts")
def get_ai_alerts():
    """Returns active operations warnings."""
    try:
        return copilot.generate_live_alerts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ai/recommendations")
def get_ai_recs():
    """Returns business actions lists."""
    try:
        return {"recommendations": copilot.generate_daily_summary()["recommendations"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/live")
def get_live():
    """Returns real-time occupancy counts, staff utilization, and estimated wait times."""
    try:
        return engine.get_live_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/today")
def get_today_summary():
    """Computes daily conversion rates, average wait times, and occupancy efficiency."""
    try:
        now = datetime.utcnow()
        start_time = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        end_time = now.strftime("%Y-%m-%d %H:%M:%S")
        
        funnel = engine.calculate_conversion_funnel(start_time, end_time)
        efficiency = engine.compute_operational_efficiency(start_time, end_time)
        
        return {
            "time_window": {"start": start_time, "end": end_time},
            "funnel": funnel,
            "efficiency": efficiency
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/queue")
def get_queue_health():
    """Returns rolling queue length metrics and abandonment counts."""
    try:
        return engine.queue.get_live_queue("Service_Zone")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/heatmap")
def get_spatial_heatmap():
    """Returns normalized coordinate density grids representing hot paths."""
    try:
        return engine.heatmap.generate_heatmap_grid()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/reports")
def trigger_report():
    """Triggers generation of the daily executive summary and returns report path."""
    try:
        now = datetime.utcnow()
        start_time = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        end_time = now.strftime("%Y-%m-%d %H:%M:%S")
        
        report_path = reporter.generate_daily_executive_report(start_time, end_time)
        return {
            "status": "success",
            "report_generated_at": timestamp_str(),
            "file_url": f"file://{os.path.abspath(report_path)}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def timestamp_str():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
