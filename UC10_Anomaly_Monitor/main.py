import sys
import json
from UC10_Anomaly_Monitor.rca import evidence_builder, agent
from UC10_Anomaly_Monitor.config import settings
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m UC10_Anomaly_Monitor.main <RECORD_ID>")
        sys.exit(1)

    record_id = sys.argv[1]
    ev = evidence_builder.build_evidence(record_id)

    a = agent.RCAAgent()
    rca_report = a.run_rca(ev)

    # Print JSON to stdout and save to log/rca_<id>.json
    # Pydantic v2: use model_dump_json
    try:
        out = rca_report.model_dump_json(indent=2)
    except Exception:
        out = json.dumps(rca_report.model_dump(), indent=2)
    print(out)

    # Save
    log_dir = Path(settings.JSON_REPORT_PATH).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    out_path = log_dir / f"rca_{record_id}.json"
    out_path.write_text(out)
    print(f"RCA report saved to: {out_path}")


if __name__ == "__main__":
    main()
