import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from database import SessionLocal, init_db
from models import AnomalyResult
from services.result_service import save_analysis_run, get_run_statistics


def test_save_analysis_run_uses_synthesis_fields_as_display_source(tmp_path):
    init_db()

    report_path = tmp_path / "final_anomaly_report.json"
    report_path.write_text(
        json.dumps([
            {
                "Record_ID": "TEST123",
                "Record_Type": "PHARMACY_CLAIM",
                "ML_Is_Anomalous": True,
                "ML_Anomaly_Signal_Count": 1,
                "ISO_Is_Anomaly": True,
                "ISO_Severity_0to1": 0.15,
                "Correlation_Anomaly": False,
                "Quantity_Supply_Anomaly": False,
                "Stat_Zscore_Anomaly": False,
                "Stat_IQR_Anomaly": False,
            }
        ]),
        encoding="utf-8",
    )

    synthesis_path = tmp_path / "final_anomaly_synthesis_report.json"
    synthesis_path.write_text(
        json.dumps({
            "anomalies": [
                {
                    "Record ID": "TEST123",
                    "Type": "PHARMACY_CLAIM",
                    "Anomaly": "Provider",
                    "Severity": "HIGH",
                    "Primary Signal": "Provider high zero-pay rate",
                    "Likely Root Cause": "Root cause example",
                    "Recommended Action": "Take corrective action",
                    "_metadata": {"confidence": 0.92},
                }
            ]
        }),
        encoding="utf-8",
    )

    repo_root = Path(__file__).resolve().parents[1]
    quality_path = repo_root / "log" / "quality_report.json"
    quality_path.write_text(
        json.dumps({"overall_quality_score": 83.5, "overall_risk_level": "MEDIUM"}),
        encoding="utf-8",
    )

    db = SessionLocal()
    try:
        run = save_analysis_run(db, filename="sample.csv", report_json_path=str(report_path), status="completed")
        result = db.query(AnomalyResult).filter(AnomalyResult.run_id == run.id).first()

        assert result is not None
        assert result.severity == "HIGH"
        assert result.anomaly_type == "Provider"
        assert result.primary_signal == "Provider high zero-pay rate"

        stats = get_run_statistics(db, run.id)
        assert stats["overall_data_quality_score"] == 83.5
        assert stats["overall_risk_level"] == "MEDIUM"
    finally:
        db.close()
