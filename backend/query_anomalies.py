"""
Query the anomaly database directly
"""
import sqlite3
import json

def get_anomaly_data(limit=100, severity=None):
    """Query anomaly results from database"""
    conn = sqlite3.connect('uc10_anomalies.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM anomaly_results"
    params = []
    
    if severity:
        query += " WHERE severity = ?"
        params.append(severity)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    results = []
    for row in rows:
        result = dict(row)
        if result['full_record']:
            result['full_record'] = json.loads(result['full_record'])
        results.append(result)
    
    conn.close()
    return results

if __name__ == "__main__":
    # Example: Get recent anomalies
    print("📊 RECENT ANOMALIES (Last 10):")
    data = get_anomaly_data(limit=10)
    for item in data:
        print(f"\n{item['record_id']} - {item['severity']} (Confidence: {item['confidence']})")
    
    # Example: Get only HIGH severity
    print("\n\n🔴 HIGH SEVERITY ANOMALIES (First 10):")
    high_severity = get_anomaly_data(limit=10, severity='HIGH')
    for item in high_severity:
        print(f"\n{item['record_id']} - {item['severity']}")
        if item['full_record']:
            print(f"   Details: {json.dumps(item['full_record'], indent=2)}")
