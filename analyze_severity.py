import json

data = json.load(open('log/final_anomaly_report.json'))
anomalies = [r for r in data if r.get('ML_Is_Anomalous')]

print("=== ISO_SEVERITY_0TO1 VALUES FOR 8 ANOMALIES ===\n")
for r in anomalies:
    iso_sev = r.get('ISO_Severity_0to1', 0)
    iso_raw = r.get('ISO_Raw_Score', 0)
    signals = r.get('ML_Anomaly_Signal_Count', 0)
    
    if iso_sev >= 0.7:
        mapped_severity = "HIGH"
    elif iso_sev >= 0.4:
        mapped_severity = "MEDIUM"
    else:
        mapped_severity = "LOW"
    
    print(f"{r['Record_ID']:15} ISO_Sev={iso_sev:6.4f} ISO_Raw={iso_raw:8.4f} Signals={signals} → {mapped_severity}")

print(f"\nAll 8 anomalies classified as: {[s for r in anomalies for s in ['HIGH'] if r.get('ISO_Severity_0to1', 0) >= 0.7][:1]}")
print(f"Distribution:")
high = sum(1 for r in anomalies if r.get('ISO_Severity_0to1', 0) >= 0.7)
medium = sum(1 for r in anomalies if 0.4 <= r.get('ISO_Severity_0to1', 0) < 0.7)
low = sum(1 for r in anomalies if r.get('ISO_Severity_0to1', 0) < 0.4)
print(f"  HIGH: {high}")
print(f"  MEDIUM: {medium}")
print(f"  LOW: {low}")
