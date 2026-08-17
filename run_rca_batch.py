#!/usr/bin/env python
"""
Batch RCA runner for all anomalous records in final_anomaly_report.json
Appends all results to a single consolidated JSON file
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

from UC10_Anomaly_Monitor.rca import evidence_builder, rag, agent
from UC10_Anomaly_Monitor.config import settings


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


def run_rca_for_record(record_id: str) -> Dict[str, Any]:
    """Run RCA for a single record and return the result."""
    try:
        print(f"  Running RCA for {record_id}...", end=" ", flush=True)
        
        ev = evidence_builder.build_evidence(record_id)
        historical_kb = str(Path(settings.JSON_REPORT_PATH).parent / "historical_resolution_cases.json")

        # Retrieve similar historical cases
        similar_cases = rag.retrieve_similar_cases(ev, kb_path=historical_kb, limit=5)

        # Run RCA with LLM (Bedrock primary, LM Studio fallback)
        try:
            a = agent.RCAAgent()
            rca_report = a.run_rag_rca(ev, historical_cases=similar_cases, kb_path=historical_kb)
            result = json.loads(rca_report.model_dump_json())
        except Exception as e:
            print(f"LLM RCA failed ({e}); using fallback...", end=" ", flush=True)
            recommendation = rag.generate_rag_recommendation(ev, kb_path=historical_kb)
            result = recommendation
        
        result['record_id'] = record_id
        print("✓")
        return {"success": True, "record_id": record_id, "data": result}
    
    except Exception as e:
        print(f"✗ ({e})")
        return {"success": False, "record_id": record_id, "error": str(e)}


def main():
    report_path = "log/final_anomaly_report.json"
    output_path = "log/rca_consolidated_report.json"
    
    if not Path(report_path).exists():
        print(f"Error: {report_path} not found")
        sys.exit(1)
    
    print("="*70)
    print("BATCH RCA PROCESSING - CONSOLIDATED OUTPUT")
    print("="*70)
    
    print("\nExtracting anomalous records from final_anomaly_report.json...")
    anomalous_records = get_anomalous_records(report_path)
    
    if not anomalous_records:
        print("No anomalous records found!")
        sys.exit(0)
    
    print(f"Found {len(anomalous_records)} anomalous records:")
    for i, record_id in enumerate(anomalous_records[:10], 1):
        print(f"  {i}. {record_id}")
    if len(anomalous_records) > 10:
        print(f"  ... and {len(anomalous_records) - 10} more")
    
    print(f"\n{'='*70}")
    print(f"Starting RCA processing ({len(anomalous_records)} records)...")
    print(f"Output will be saved to: {output_path}")
    print(f"{'='*70}\n")
    
    # Process all records
    results = []
    successful = 0
    failed = 0
    
    for i, record_id in enumerate(anomalous_records, 1):
        print(f"[{i:3d}/{len(anomalous_records)}]", end=" ")
        rca_result = run_rca_for_record(record_id)
        
        if rca_result["success"]:
            results.append(rca_result["data"])
            successful += 1
        else:
            results.append({
                "record_id": record_id,
                "error": rca_result.get("error", "Unknown error")
            })
            failed += 1
    
    # Save consolidated results
    log_dir = Path(settings.JSON_REPORT_PATH).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = log_dir / "rca_consolidated_report.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"RCA PROCESSING COMPLETE")
    print(f"{'='*70}")
    print(f"Total:       {len(anomalous_records)}")
    print(f"Successful:  {successful}")
    print(f"Failed:      {failed}")
    print(f"Output file: {output_file}")
    print(f"Total size:  {output_file.stat().st_size / 1024:.2f} KB")
    print(f"{'='*70}")
    
    # Summary
    print(f"\n✓ All RCA results consolidated into: {output_file}")
    
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
