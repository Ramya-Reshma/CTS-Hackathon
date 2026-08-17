#!/usr/bin/env python
"""Test the file upload with fixed normalization"""

import requests

print("[TEST] Uploading dataset (testing fixed boolean normalization)...")
try:
    with open('Data/claims_pharmacy_auth_monitor_dataset_final.xlsx', 'rb') as f:
        files = {'file': f}
        resp = requests.post('http://localhost:8000/api/analyze', files=files, timeout=300)

    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"\n✅ SUCCESS - Pipeline executed without encoder errors!")
        print(f"Run ID: {data.get('run_id')}")
        print(f"Total Records: {data.get('total_records')}")
        print(f"Total Anomalies: {data.get('total_anomalies')}")
        print(f"Severity: HIGH={data.get('severity_summary', {}).get('high')}, MEDIUM={data.get('severity_summary', {}).get('medium')}, LOW={data.get('severity_summary', {}).get('low')}")
        print(f"Message: {data.get('message')}")
    else:
        print(f"\n❌ ERROR Status {resp.status_code}")
        print(f"Response: {resp.text[:1000]}")
        
except Exception as e:
    print(f"❌ Exception: {e}")
