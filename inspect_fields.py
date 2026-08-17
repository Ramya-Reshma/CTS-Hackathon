import json

data = json.load(open('log/final_anomaly_report.json'))
r = data[0]

print("=== FIELDS IN A SAMPLE RECORD ===\n")
for k in sorted(r.keys()):
    v = r[k]
    if isinstance(v, (int, float)):
        print(f"  {k:40} {v}")
    else:
        print(f"  {k:40} {str(v)[:40]}")

print("\n=== ML SIGNAL FIELDS IN 8 ANOMALIES ===\n")
anomalies = [r for r in data if r.get('ML_Is_Anomalous')]
for anomaly in anomalies:
    print(f"{anomaly['Record_ID']:15} ML_Anomaly_Signal_Count={anomaly.get('ML_Anomaly_Signal_Count')} Signals={anomaly.get('ML_Signal_Names', [])}")
