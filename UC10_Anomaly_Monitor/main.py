import sys
import json
from pathlib import Path

from UC10_Anomaly_Monitor.rca import evidence_builder, rag, agent
from UC10_Anomaly_Monitor.config import settings


def run_rca_for_record(record_id: str, report_path: str = None) -> dict:
    """Run full evidence extraction, RAG retrieval, and LLM RCA for a single record."""
    print(f"Building compact evidence for record: {record_id}...")
    ev = evidence_builder.build_evidence(record_id, report_path=report_path)

    print("Retrieving top 5 relevant healthcare anomaly cases via RAG...")
    similar_cases = rag.retrieve_similar_cases(ev, limit=5)
    print(f"Retrieved {len(similar_cases)} knowledge records.")

    print("Executing RCA Agent with Bedrock / LLM...")
    rca_agent = agent.RCAAgent()
    analysis = rca_agent.run_rag_rca(ev, historical_cases=similar_cases)
    
    return analysis.model_dump()


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m UC10_Anomaly_Monitor.main <RECORD_ID>")
        sys.exit(1)

    record_id = sys.argv[1]
    result = run_rca_for_record(record_id)
    
    # Save outputs to log/ directory
    log_dir = Path(__file__).resolve().parents[1] / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Save individual record report
    indiv_file = log_dir / f"rca_{record_id}.json"
    with open(indiv_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    
    # 2. Save final_analysis_report.json (standard artifact)
    final_file = log_dir / "final_analysis_report.json"
    with open(final_file, "w", encoding="utf-8") as f:
        json.dump({"analyses": [result]}, f, indent=2)

    print("\n" + "="*60)
    print("FINAL RCA ANALYSIS RESULT:")
    print("="*60)
    print(json.dumps(result, indent=2))
    print("="*60)
    print(f"[OK] Individual report saved to: {indiv_file}")
    print(f"[OK] Final analysis report saved to: {final_file}")


if __name__ == "__main__":
    main()
