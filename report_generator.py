# report_generator.py
"""
Report Generator: Compiles styled HTML executive summary reports
consolidating business metrics, conversions, and space utilization.
"""

import os
from datetime import datetime

from analytics_engine import AnalyticsEngine

class ReportGenerator:
    def __init__(self, db_path: str = "db/customer_intel.db", output_dir: str = "monitoring/reports"):
        self.analytics = AnalyticsEngine(db_path)
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_daily_executive_report(self, start_time: str, end_time: str) -> str:
        """
        Compiles and saves a styled HTML dashboard report.
        """
        metrics = self.analytics.get_live_metrics()
        funnel = self.analytics.calculate_conversion_funnel(start_time, end_time)
        efficiency = self.analytics.compute_operational_efficiency(start_time, end_time)
        heatmap = self.analytics.heatmap.generate_heatmap_grid(start_time, end_time)
        
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Daily Executive Report - Restaurant Analytics</title>
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #0f172a;
            color: #f8fafc;
            margin: 0;
            padding: 40px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: #1e293b;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 4px 30px rgba(0,0,0,0.3);
        }}
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 5px;
            background: linear-gradient(to right, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .timestamp {{
            color: #94a3b8;
            font-size: 0.9rem;
            margin-bottom: 40px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 40px;
        }}
        .card {{
            background: #334155;
            padding: 24px;
            border-radius: 12px;
            border-left: 5px solid #38bdf8;
        }}
        .card.alt {{
            border-left-color: #818cf8;
        }}
        .card h3 {{
            margin-top: 0;
            color: #cbd5e1;
        }}
        .metric-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #ffffff;
        }}
        .funnel-step {{
            display: flex;
            justify-content: space-between;
            background: #1e293b;
            padding: 12px;
            margin-bottom: 8px;
            border-radius: 6px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Executive Performance Report</h1>
        <div class="timestamp">Generated on {timestamp} (Window: {start_time} to {end_time})</div>
        
        <div class="grid">
            <div class="card">
                <h3>Operational Efficiency Score</h3>
                <div class="metric-value">{efficiency["operational_efficiency_score"]}%</div>
                <p>Combines checkout wait times, abandonment metrics, and staff utilization indices.</p>
            </div>
            <div class="card alt">
                <h3>Capacity & Space Utilization</h3>
                <div class="metric-value">{efficiency["space_utilization_percent"]}%</div>
                <p>Percent of store dining seating used relative to peak limits.</p>
            </div>
        </div>

        <h2>Checkout & Service Conversion Funnel</h2>
        <div class="funnel-step">
            <span>1. Store Entrances (Unique Visitors)</span>
            <strong>{funnel["entrances"]}</strong>
        </div>
        <div class="funnel-step">
            <span>2. Queue checkouts (Service Zone Entry)</span>
            <strong>{funnel["checkout_attempts"]} ({funnel["checkout_conversion"]}% conversion)</strong>
        </div>
        <div class="funnel-step">
            <span>3. Completed Transactions (Served Guests)</span>
            <strong>{funnel["transactions"]} ({funnel["service_conversion"]}% service conversion)</strong>
        </div>

        <h2 style="margin-top:40px;">Customer Service & Queue Health</h2>
        <div class="grid">
            <div class="card">
                <h3>Average Wait Duration</h3>
                <div class="metric-value">{efficiency["avg_dwell_time_seconds"]}s</div>
            </div>
            <div class="card alt">
                <h3>Queue Abandonment Rate</h3>
                <div class="metric-value">{efficiency["abandonment_rate"]}%</div>
            </div>
        </div>
    </div>
</body>
</html>
"""
        filepath = os.path.join(self.output_dir, "daily_executive_report.html")
        with open(filepath, "w") as f:
            f.write(html_content)
        return filepath
