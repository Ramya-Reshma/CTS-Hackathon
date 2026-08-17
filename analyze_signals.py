import json

data = json.load(open('log/final_anomaly_report.json'))
anomalies = [r for r in data if r.get('ML_Is_Anomalous')]

print("=== ANOMALY SIGNALS FOR 8 ANOMALIES ===\n")

# Identify signal fields
signal_fields = [k for k in anomalies[0].keys() if 'Anomaly' in k and k != 'ML_Is_Anomalous']
print(f"Signal fields: {signal_fields}\n")

for anomaly in anomalies:
    record_id = anomaly['Record_ID']
    signals_triggered = []
    residuals = {}
    
    for field in signal_fields:
        if anomaly.get(field):
            signals_triggered.append(field.replace('_Anomaly', ''))
            # Get the corresponding residual
            residual_field = field.replace('Anomaly', 'Residual')
            if residual_field in anomaly:
                residuals[field.replace('_Anomaly', '')] = anomaly[residual_field]
    
    print(f"{record_id:15} Count={anomaly.get('ML_Anomaly_Signal_Count')} Signals: {signals_triggered}")
    for sig, res in residuals.items():
        print(f"                  {sig}: residual={res:.2f}")
