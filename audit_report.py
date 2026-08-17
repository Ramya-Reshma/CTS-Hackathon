#!/usr/bin/env python
"""
Comprehensive audit of the 50/50 anomaly issue.
"""
import json
from pathlib import Path

# Load the final anomaly report
report_path = Path("log/final_anomaly_report.json")
data = json.loads(report_path.read_text())

total = len(data)
actual_anomalies = sum(1 for r in data if r.get('ML_Is_Anomalous', False))
normal_records = total - actual_anomalies

iso_anomalies = sum(1 for r in data if r.get('ISO_Is_Anomaly', False))
corr_anomalies = sum(1 for r in data if r.get('Correlation_Anomaly', False))
qs_anomalies = sum(1 for r in data if r.get('Quantity_Supply_Anomaly', False))

print("="*80)
print("COMPREHENSIVE AUDIT: 50-ROW TEST")
print("="*80)

print(f"\nTOTAL INPUT RECORDS: {total}")
print(f"ACTUAL ANOMALIES (ML_Is_Anomalous=true): {actual_anomalies}")
print(f"NORMAL RECORDS: {normal_records}")

print(f"\n" + "="*80)
print("SIGNAL BREAKDOWN")
print("="*80)
print(f"  ISO anomalies: {iso_anomalies}")
print(f"  Correlation anomalies: {corr_anomalies}")
print(f"  Quantity/Supply anomalies: {qs_anomalies}")

print(f"\n" + "="*80)
print("ANOMALY SIGNAL COUNT DISTRIBUTION")
print("="*80)
for count in range(4):
    records_with_count = sum(1 for r in data if r.get('ML_Anomaly_Signal_Count', 0) == count)
    print(f"  {count} signals: {records_with_count} records")

print(f"\n" + "="*80)
print("ANOMALIES BY SIGNAL COUNT")
print("="*80)
for count in range(1, 4):
    anomalies = [r for r in data if r.get('ML_Anomaly_Signal_Count', 0) == count and r.get('ML_Is_Anomalous')]
    if anomalies:
        print(f"  {count} signals: {len(anomalies)} actual anomalies")

print(f"\n" + "="*80)
print("FIRST 20 RECORDS WITH DETAILS")
print("="*80)
for idx, r in enumerate(data[:20], 1):
    anomaly_flag = "ANOMALY" if r.get('ML_Is_Anomalous') else "NORMAL"
    print(f"{idx:2}. {r['Record_ID']:15} {anomaly_flag:8} Signals={r.get('ML_Anomaly_Signal_Count', 0)} ISO={r.get('ISO_Is_Anomaly'):5} Corr={r.get('Correlation_Anomaly'):5} QS={r.get('Quantity_Supply_Anomaly'):5}")

print(f"\n" + "="*80)
print("ROOT CAUSE ANALYSIS")
print("="*80)
print(f"\nBUG IDENTIFIED:")
print(f"  Backend function result_service.py save_analysis_run() loads final_anomaly_report.json")
print(f"  It treats ALL {total} records in the file as anomalies")
print(f"  BUT the file actually contains ALL records with anomaly flags")
print(f"  The file should ONLY store records where ML_Is_Anomalous = true")
print(f"\nCORRECT VALUES SHOULD BE:")
print(f"  total_anomalies: {actual_anomalies}")
print(f"  Not: {total}")

print(f"\n" + "="*80)
print("ANOMALY RECORDS (ACTUAL)")
print("="*80)
for r in data:
    if r.get('ML_Is_Anomalous'):
        print(f"  {r['Record_ID']}: {r['Record_Type']} - Signals={r['ML_Anomaly_Signal_Count']}")

print(f"\n" + "="*80)
print("FIX REQUIRED")
print("="*80)
print(f"\n1. In result_service.py, function save_analysis_run():")
print(f"   CHANGE: anomalies = report_data (which contains ALL records)")
print(f"   TO:      anomalies = [r for r in report_data if r.get('ML_Is_Anomalous')]")
print(f"\n2. Then count becomes {actual_anomalies} instead of {total}")
print(f"\n3. This will fix the frontend to show correct total")
