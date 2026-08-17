import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect('uc10_anomalies.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Create HTML report
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>UC10 Anomalies Database Viewer</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th { background: #007bff; color: white; padding: 12px; text-align: left; }
        td { padding: 10px; border-bottom: 1px solid #ddd; }
        tr:hover { background: #f9f9f9; }
        .stat-card { display: inline-block; margin: 10px; padding: 15px; background: #e7f3ff; border-left: 4px solid #007bff; border-radius: 4px; }
        .stat-value { font-size: 24px; font-weight: bold; color: #007bff; }
        .stat-label { color: #666; font-size: 14px; }
        .severity-HIGH { background: #fee; color: #c33; font-weight: bold; }
        .severity-MEDIUM { background: #ffe; color: #aa5; font-weight: bold; }
        .severity-LOW { background: #efe; color: #3a3; font-weight: bold; }
        .json-cell { font-family: monospace; font-size: 11px; white-space: pre-wrap; word-break: break-all; }
        .collapsible { cursor: pointer; padding: 8px; background: #f0f0f0; border: 1px solid #ddd; margin: 5px 0; border-radius: 4px; }
        .collapsible:hover { background: #e0e0e0; }
        .content { display: none; padding: 10px; background: #fafafa; border: 1px solid #ddd; border-top: none; }
        .content.show { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🗄️ UC10 Anomalies Database Viewer</h1>
        <p>Generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        
        <h2>📊 Database Statistics</h2>
"""

# Get statistics
cursor.execute("SELECT COUNT(*) as total FROM analysis_runs")
total_runs = cursor.fetchone()['total']

cursor.execute("SELECT COUNT(*) as total FROM anomaly_results")
total_anomalies = cursor.fetchone()['total']

cursor.execute("SELECT COUNT(*) as count FROM anomaly_results WHERE severity='HIGH'")
high_count = cursor.fetchone()['count']

cursor.execute("SELECT COUNT(*) as count FROM anomaly_results WHERE severity='MEDIUM'")
medium_count = cursor.fetchone()['count']

cursor.execute("SELECT COUNT(*) as count FROM anomaly_results WHERE severity='LOW'")
low_count = cursor.fetchone()['count']

html_content += f"""
        <div class="stat-card">
            <div class="stat-value">{total_runs}</div>
            <div class="stat-label">Total Analysis Runs</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{total_anomalies}</div>
            <div class="stat-label">Total Anomaly Results</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color: #c33;">{high_count}</div>
            <div class="stat-label">HIGH Severity</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color: #aa5;">{medium_count}</div>
            <div class="stat-label">MEDIUM Severity</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color: #3a3;">{low_count}</div>
            <div class="stat-label">LOW Severity</div>
        </div>
"""

# Analysis Runs Table
html_content += """
        <h2>📋 Analysis Runs</h2>
        <table>
            <tr>
                <th>Run ID</th>
                <th>Filename</th>
                <th>Created At</th>
                <th>Total Records</th>
                <th>Anomalies Detected</th>
                <th>Status</th>
            </tr>
"""

cursor.execute("SELECT id, filename, created_at, total_records, anomaly_count, processing_status FROM analysis_runs ORDER BY created_at DESC")
for row in cursor.fetchall():
    html_content += f"""
            <tr>
                <td><code>{row['id']}</code></td>
                <td>{row['filename']}</td>
                <td>{row['created_at']}</td>
                <td>{row['total_records']}</td>
                <td>{row['anomaly_count']}</td>
                <td><strong>{row['processing_status']}</strong></td>
            </tr>
"""

html_content += """
        </table>
"""

# Anomaly Results Summary
html_content += """
        <h2>🔍 Anomaly Results (Sample - Top 50)</h2>
        <table>
            <tr>
                <th>Record ID</th>
                <th>Type</th>
                <th>Severity</th>
                <th>Priority</th>
                <th>Confidence</th>
                <th>Created At</th>
            </tr>
"""

cursor.execute("SELECT record_id, record_type, severity, priority, confidence, created_at FROM anomaly_results ORDER BY created_at DESC LIMIT 50")
for row in cursor.fetchall():
    severity_class = f"severity-{row['severity']}"
    html_content += f"""
            <tr>
                <td><code>{row['record_id']}</code></td>
                <td>{row['record_type']}</td>
                <td class="{severity_class}">{row['severity']}</td>
                <td>{row['priority']}</td>
                <td>{row['confidence']:.2f}</td>
                <td>{row['created_at']}</td>
            </tr>
"""

html_content += """
        </table>
        
        <h2>📊 Severity Distribution</h2>
        <table>
            <tr>
                <th>Severity Level</th>
                <th>Count</th>
                <th>Percentage</th>
            </tr>
"""

html_content += f"""
            <tr>
                <td class="severity-HIGH">HIGH</td>
                <td>{high_count}</td>
                <td>{(high_count/total_anomalies*100):.2f}%</td>
            </tr>
            <tr>
                <td class="severity-MEDIUM">MEDIUM</td>
                <td>{medium_count}</td>
                <td>{(medium_count/total_anomalies*100):.2f}%</td>
            </tr>
            <tr>
                <td class="severity-LOW">LOW</td>
                <td>{low_count}</td>
                <td>{(low_count/total_anomalies*100):.2f}%</td>
            </tr>
"""

html_content += """
        </table>
    </div>
    
    <script>
        // Add collapsible functionality if needed
    </script>
</body>
</html>
"""

# Write HTML file
with open('database_viewer.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("✅ HTML viewer created: database_viewer.html")
print(f"📊 Total Anomalies: {total_anomalies}")
print(f"   HIGH: {high_count} ({high_count/total_anomalies*100:.1f}%)")
print(f"   MEDIUM: {medium_count} ({medium_count/total_anomalies*100:.1f}%)")
print(f"   LOW: {low_count} ({low_count/total_anomalies*100:.1f}%)")

conn.close()
