"""
Export final_anomaly_synthesis_report.json to CSV format.

Columns: Priority, Record ID, Type, Anomaly, Severity, Primary Signal, Likely Root Cause, Recommended Action
"""

import json
import csv
from pathlib import Path


def export_to_csv(
    input_path: str = "log/final_anomaly_synthesis_report.json",
    output_path: str = "log/final_anomaly_synthesis_report.csv"
) -> int:
    """Export JSON synthesis report to CSV format."""
    
    print(f"Loading synthesis report from {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    anomalies = data.get("anomalies", [])
    print(f"Found {len(anomalies)} anomaly records")
    
    # Define columns in order
    columns = [
        "Priority",
        "Record ID",
        "Type",
        "Anomaly",
        "Severity",
        "Primary Signal",
        "Likely Root Cause",
        "Recommended Action",
        "Confidence",
        "Impact",
        "Additional Checks Required",
    ]
    
    # Write CSV
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        
        for anomaly in anomalies:
            metadata = anomaly.get("_metadata", {})
            additional_checks = ", ".join(metadata.get("additional_checks", []))
            
            row = {
                "Priority": anomaly.get("Priority", ""),
                "Record ID": anomaly.get("Record ID", ""),
                "Type": anomaly.get("Type", ""),
                "Anomaly": anomaly.get("Anomaly", ""),
                "Severity": anomaly.get("Severity", ""),
                "Primary Signal": anomaly.get("Primary Signal", ""),
                "Likely Root Cause": anomaly.get("Likely Root Cause", ""),
                "Recommended Action": anomaly.get("Recommended Action", ""),
                "Confidence": metadata.get("confidence", ""),
                "Impact": metadata.get("impact", ""),
                "Additional Checks Required": additional_checks,
            }
            writer.writerow(row)
    
    print(f"[OK] Exported {len(anomalies)} records to {output_path}")
    return len(anomalies)


if __name__ == "__main__":
    try:
        count = export_to_csv()
        print(f"[SUCCESS] Export complete: {count} anomaly records")
    except FileNotFoundError as e:
        print(f"[ERROR] File not found: {e}")
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
