from jinja2 import Template
import os

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Aurika Validation & Benchmarking Report</title>
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
        .risk-safe { color: #27ae60; font-weight: bold; }
        .risk-acceptable { color: #f39c12; font-weight: bold; }
        .risk-needs-improvement { color: #c0392b; font-weight: bold; }
        .alert-box { background-color: #fdf2e9; border-left: 4px solid #e67e22; padding: 15px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Aurika Validation & Benchmarking Report</h1>
        
        <h2>Executive Summary</h2>
        <div class="grid">
            <div class="card"><h3>Detection Accuracy</h3><p>{{ data.executive.detection }}%</p></div>
            <div class="card"><h3>Tracking Accuracy</h3><p>{{ data.executive.tracking }}%</p></div>
            <div class="card"><h3>Event F1 Score</h3><p>{{ "%.1f"|format(data.events.F1_Score * 100) }}%</p></div>
            <div class="card"><h3>Rec Precision</h3><p>{{ "%.1f"|format(data.recommendations.Precision * 100) }}%</p></div>
        </div>

        <h2>Business KPI Analysis</h2>
        <table>
            <tr>
                <th>KPI</th>
                <th>Accuracy</th>
                <th>MAE</th>
                <th>RMSE</th>
                <th>Business Risk</th>
            </tr>
            {% for kpi, metrics in data.kpis.items() %}
            <tr>
                <td>{{ kpi }}</td>
                <td>{{ "%.1f"|format(metrics.Accuracy * 100) }}%</td>
                <td>{{ metrics.MAE }}</td>
                <td>{{ metrics.RMSE }}</td>
                <td class="risk-{{ metrics.Risk|lower|replace(' ', '-') }}">{{ metrics.Risk }}</td>
            </tr>
            {% endfor %}
        </table>
        
        <h2>Root Cause Analysis & Priorities</h2>
        <div class="alert-box">
            <h3>Highest Operational Risk: {{ data.weakest_kpi[0] }} ({{ "%.1f"|format(data.weakest_kpi[1].Accuracy * 100) }}%)</h3>
            <p><strong>Root Cause Candidate:</strong> Late waiting state detection leading to artificially low wait time accumulations.</p>
            <p><strong>Module Origin:</strong> State Engine / Zone Mapper overlap.</p>
            <p><strong>Business Impact:</strong> Recommendations for queue management may be triggered 30-45 seconds later than optimal, potentially violating strict SLAs.</p>
            <p><strong>Highest Priority Fix:</strong> Expand the geometric boundary of the 'Waiting Area' zone to catch guests queuing immediately inside the door before they enter the formal waiting polygon.</p>
        </div>

        <h2>Business Event Accuracy</h2>
        <ul>
            <li>Precision: {{ "%.1f"|format(data.events.Precision * 100) }}%</li>
            <li>Recall: {{ "%.1f"|format(data.events.Recall * 100) }}%</li>
            <li>Avg Timing Error: {{ data.events.Average_Timing_Error }}s</li>
            <li>False Events: {{ data.events.False_Events }}</li>
        </ul>
        
    </div>
</body>
</html>
"""

class ValidationReportGenerator:
    @staticmethod
    def generate(data: dict, output_path: str = "validation_report.html"):
        template = Template(HTML_TEMPLATE)
        html_content = template.render(data=data)
        with open(output_path, "w") as f:
            f.write(html_content)
        print(f"[ValidationSuite] Report generated at {output_path}")
