import os
from datetime import datetime
from typing import List
from jinja2 import Template

from restaurant_analytics.restaurant_state import RestaurantSnapshot
from restaurant_analytics.operational_intelligence import OperationalDecision

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Aurika Executive Report - {{ snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</title>
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        h2 { color: #2980b9; margin-top: 30px; }
        .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }
        .card { background: #ecf0f1; padding: 15px; border-radius: 6px; text-align: center; }
        .card h3 { margin: 0; font-size: 14px; color: #7f8c8d; text-transform: uppercase; }
        .card p { margin: 10px 0 0 0; font-size: 24px; font-weight: bold; color: #2c3e50; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; color: #333; }
        .critical { color: #e74c3c; font-weight: bold; }
        .high { color: #e67e22; font-weight: bold; }
        .warning { color: #f1c40f; font-weight: bold; }
        .info { color: #3498db; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Aurika Executive Operational Report</h1>
        <p><strong>Generated:</strong> {{ snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S') }} UTC</p>
        
        <h2>Restaurant Summary</h2>
        <div class="grid">
            <div class="card">
                <h3>Health Score</h3>
                <p>{{ "%.1f"|format(snapshot.health_score) }}/100</p>
            </div>
            <div class="card">
                <h3>Occupancy</h3>
                <p>{{ snapshot.current_occupancy }}</p>
            </div>
            <div class="card">
                <h3>Queue Length</h3>
                <p>{{ snapshot.current_queue_length }}</p>
            </div>
            <div class="card">
                <h3>Avg Wait Time</h3>
                <p>{{ "%.1f"|format(snapshot.average_wait_time / 60) }} min</p>
            </div>
        </div>

        <h2>Zone Statistics</h2>
        <table>
            <tr>
                <th>Zone</th>
                <th>Current Guests</th>
                <th>Avg Dwell (s)</th>
                <th>Peak Dwell (s)</th>
                <th>Congestion</th>
            </tr>
            {% for zone_name, zone in snapshot.zone_status.items() %}
            <tr>
                <td>{{ zone_name }}</td>
                <td>{{ zone.current_guests }}</td>
                <td>{{ "%.1f"|format(zone.average_dwell) }}</td>
                <td>{{ "%.1f"|format(zone.peak_dwell) }}</td>
                <td class="{{ zone.congestion_level|lower }}">{{ zone.congestion_level }}</td>
            </tr>
            {% endfor %}
        </table>

        <h2>Operational Decisions Generated</h2>
        <table>
            <tr>
                <th>Priority</th>
                <th>Severity</th>
                <th>Title</th>
                <th>Recommended Action</th>
                <th>Confidence</th>
            </tr>
            {% for decision in decisions %}
            <tr>
                <td>{{ decision.priority }}</td>
                <td class="{{ decision.severity|lower }}">{{ decision.severity }}</td>
                <td>{{ decision.title }}</td>
                <td>{{ decision.recommended_action }}</td>
                <td>{{ "%.1f"|format(decision.confidence * 100) }}%</td>
            </tr>
            {% else %}
            <tr>
                <td colspan="5">No operational decisions were triggered.</td>
            </tr>
            {% endfor %}
        </table>
        
        <h2>System Health</h2>
        <p><strong>Status:</strong> {{ snapshot.system_status }}</p>
        <p><strong>Overall Tracking & Domain Confidence:</strong> {{ "%.1f"|format(snapshot.overall_confidence * 100) }}%</p>
        {% if snapshot.current_alerts %}
        <ul>
            {% for alert in snapshot.current_alerts %}
            <li>{{ alert }}</li>
            {% endfor %}
        </ul>
        {% endif %}
    </div>
</body>
</html>
"""

class ExecutiveReportGenerator:
    """Generates an end-of-day or ad-hoc HTML Executive Report."""
    
    @staticmethod
    def generate(snapshot: RestaurantSnapshot, decisions: List[OperationalDecision], output_path: str = "executive_report.html"):
        template = Template(HTML_TEMPLATE)
        html_content = template.render(
            snapshot=snapshot,
            decisions=decisions
        )
        with open(output_path, "w") as f:
            f.write(html_content)
        print(f"[ReportGenerator] Executive report generated at {output_path}")
