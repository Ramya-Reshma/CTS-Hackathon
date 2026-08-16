#!/usr/bin/env python
"""
Batch RCA runner for all anomalous records in final_anomaly_report.json
"""

import json
import sys
import subprocess
from pathlib import Path
from typing import List

def get_anomalous_records(report_path: str) -> List[str]:
    """Extract Record_IDs of all anomalous records."""
    with open(report_path, 'r') as f:
        report = json.load(f)
    
    anomalous_records = []
    for record in report:
        if record.get('ML_Is_Anomalous', False):
            record_id = record.get('Record_ID')
            if record_id:
                anomalous_records.append(record_id)
    
    return anomalous_records

def run_rca_for_record(record_id: str) -> bool:
    """Run RCA for a single record."""
    try:
        print(f"\n{'='*70}")
        print(f"Running RCA for: {record_id}")
        print(f"{'='*70}")
        
        result = subprocess.run(
            [sys.executable, "-m", "UC10_Anomaly_Monitor.main", record_id],
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✓ RCA completed successfully for {record_id}")
            return True
        else:
            print(f"✗ RCA failed for {record_id} (exit code: {result.returncode})")
            return False
    except Exception as e:
        print(f"✗ Error running RCA for {record_id}: {e}")
        return False

def main():
    report_path = "log/final_anomaly_report.json"
    
    if not Path(report_path).exists():
        print(f"Error: {report_path} not found")
        sys.exit(1)
    
    print("Extracting anomalous records from final_anomaly_report.json...")
    anomalous_records = get_anomalous_records(report_path)
    
    if not anomalous_records:
        print("No anomalous records found!")
        sys.exit(0)
    
    print(f"Found {len(anomalous_records)} anomalous records:")
    for record_id in anomalous_records:
        print(f"  - {record_id}")
    
    print(f"\n{'='*70}")
    print(f"Starting batch RCA processing ({len(anomalous_records)} records)...")
    print(f"{'='*70}\n")
    
    successful = 0
    failed = 0
    
    for i, record_id in enumerate(anomalous_records, 1):
        print(f"\n[{i}/{len(anomalous_records)}] Processing {record_id}...")
        if run_rca_for_record(record_id):
            successful += 1
        else:
            failed += 1
    
    print(f"\n{'='*70}")
    print(f"BATCH RCA PROCESSING COMPLETE")
    print(f"{'='*70}")
    print(f"Total:      {len(anomalous_records)}")
    print(f"Successful: {successful}")
    print(f"Failed:     {failed}")
    print(f"{'='*70}")
    
    # Check generated RCA reports
    log_dir = Path("log")
    rca_files = list(log_dir.glob("rca_*.json"))
    print(f"\nRCA reports in log folder: {len(rca_files)}")
    for rca_file in sorted(rca_files):
        print(f"  - {rca_file.name}")
    
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
