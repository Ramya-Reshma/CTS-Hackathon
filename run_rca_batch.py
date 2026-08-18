"""
Batch RCA runner for all anomalous records in final_anomaly_report.json.
Generates log/final_analysis_report.json containing structured RCA results.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

from UC10_Anomaly_Monitor.rca import evidence_builder, rag, agent
from UC10_Anomaly_Monitor.config import settings


def get_anomalous_records(report_path: str) -> List[str]:
    """Extract Record_IDs of all anomalous records."""
    with open(report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    anomalous_records = []
    for record in report:
        if record.get('ML_Is_Anomalous', False) or record.get('ISO_Is_Anomaly', False):
            record_id = record.get('Record_ID')
            if record_id and record_id not in anomalous_records:
                anomalous_records.append(record_id)
    
    return anomalous_records


def run_rca_for_record(record_id: str, report_path: str = None) -> Dict[str, Any]:
    """Run RCA for a single record and return the structured result."""
    try:
        print(f"  Running RCA for {record_id}...", end=" ", flush=True)
        
        ev = evidence_builder.build_evidence(record_id, report_path=report_path)
        similar_cases = rag.retrieve_similar_cases(ev, limit=5)

        a = agent.RCAAgent()
        rca_report = a.run_rag_rca(ev, historical_cases=similar_cases)
        result = rca_report.model_dump()
        
        print("[OK]")
        return {"success": True, "record_id": record_id, "data": result}
    
    except Exception as e:
        print(f"[FAILED] ({e})")
        return {"success": False, "record_id": record_id, "error": str(e)}


def main():
    repo_root = Path(__file__).resolve().parent
    report_path = str(repo_root / "log" / "final_anomaly_report.json")
    output_path = repo_root / "log" / "final_analysis_report.json"
    consolidated_path = repo_root / "log" / "rca_consolidated_report.json"
    
    if not Path(report_path).exists():
        print(f"Error: {report_path} not found")
        sys.exit(1)
    
    print("="*70)
    print("BATCH RCA PROCESSING - EVIDENCE BUILDER + RAG + BEDROCK")
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
    print(f"{'='*70}\n")
    
    analyses = []
    successful = 0
    failed = 0
    
    for i, record_id in enumerate(anomalous_records, 1):
        print(f"[{i:3d}/{len(anomalous_records)}]", end=" ")
        rca_result = run_rca_for_record(record_id, report_path=report_path)
        
        if rca_result["success"]:
            analyses.append(rca_result["data"])
            successful += 1
            
            # Also save individual record file for backward compatibility
            indiv_file = repo_root / "log" / f"rca_{record_id}.json"
            with open(indiv_file, "w", encoding="utf-8") as f:
                json.dump(rca_result["data"], f, indent=2)
        else:
            failed += 1

    # Save final analysis report
    final_output = {
        "analyses": analyses
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=2)

    with open(consolidated_path, 'w', encoding='utf-8') as f:
        json.dump(analyses, f, indent=2)
    
    print(f"\n{'='*70}")
    print("RCA PROCESSING COMPLETE")
    print(f"{'='*70}")
    print(f"Total Anomalies: {len(anomalous_records)}")
    print(f"Successful:       {successful}")
    print(f"Failed:           {failed}")
    print(f"Final Report:     {output_path}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
