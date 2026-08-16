import sys
import json
from pathlib import Path

from UC10_Anomaly_Monitor.rca import evidence_builder, rag, agent
from UC10_Anomaly_Monitor.config import settings


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m UC10_Anomaly_Monitor.main <RECORD_ID>")
        sys.exit(1)

    record_id = sys.argv[1]
    ev = evidence_builder.build_evidence(record_id)
    historical_kb = str(Path(settings.JSON_REPORT_PATH).parent / "historical_resolution_cases.json")

    # Step 1: Retrieve similar historical cases by record type + denial reason + anomaly pattern
    similar_cases = rag.retrieve_similar_cases(ev, kb_path=historical_kb, limit=5)

    # Step 2: Prefer the LLM-powered RCA flow when it is configured; otherwise fall back to the local retrieval summary
    try:
        a = agent.RCAAgent()
        rca_report = a.run_rag_rca(ev, historical_cases=similar_cases, kb_path=historical_kb)
        out = rca_report.model_dump_json(indent=2)
    except Exception as e:
        print(f"LLM RCA path unavailable ({e}); using local retrieval-based fallback.")
        recommendation = rag.generate_rag_recommendation(ev, kb_path=historical_kb)
        out = json.dumps(recommendation, indent=2)

    # Save result
    log_dir = Path(settings.JSON_REPORT_PATH).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    out_path = log_dir / f"rca_{record_id}.json"
    out_path.write_text(out)
    print(out)
    print(f"RCA report saved to: {out_path}")


if __name__ == "__main__":
    main()
