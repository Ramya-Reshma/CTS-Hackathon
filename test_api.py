#!/usr/bin/env python
"""Test the UC10 API upload endpoint"""

import requests
import json
import time

def test_api():
    # Test health check
    print("[TEST] Checking health endpoint...")
    try:
        resp = requests.get('http://localhost:8000/api/health')
        print(f"Health: {resp.json()}")
    except Exception as e:
        print(f"ERROR: {e}")
        return
    
    # Test file upload
    print("\n[TEST] Uploading file...")
    try:
        with open('Data/claims_pharmacy_auth_monitor_dataset_final.xlsx', 'rb') as f:
            files = {'file': f}
            resp = requests.post('http://localhost:8000/api/analyze', files=files, timeout=300)
        
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.text}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"\n✅ SUCCESS")
            print(f"Run ID: {data.get('run_id')}")
            print(f"Total Anomalies: {data.get('total_anomalies')}")
            print(f"Status: {data.get('status')}")
            print(f"Message: {data.get('message')}")
        else:
            print(f"\n❌ ERROR Status {resp.status_code}")
            
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_api()
