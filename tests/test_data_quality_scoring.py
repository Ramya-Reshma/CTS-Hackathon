import json
import sys
import pandas as pd
import pytest
from pathlib import Path

# Add project roots
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "ML") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "ML"))
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))

from ML.data_quality import calculate_scores_and_risk, run_quality_checks, RULES
from backend.database import SessionLocal, init_db
from backend.services.result_service import save_analysis_run, get_run_statistics


def test_data_quality_weighted_aggregation_5_dimensions():
    """Verify that Overall Data Quality Score equals the weighted sum of 5 dimensions including Timeliness."""
    mock_rules = [
        {"rule_id": "R001", "dimension": "Completeness", "failure_rate_pct": 4.0, "severity": "High", "status": "FAILED"},
        {"rule_id": "R004", "dimension": "Validity", "failure_rate_pct": 2.0, "severity": "High", "status": "FAILED"},
        {"rule_id": "R002", "dimension": "Uniqueness", "failure_rate_pct": 0.0, "severity": "Critical", "status": "PASSED"},
        {"rule_id": "R005", "dimension": "Consistency", "failure_rate_pct": 5.0, "severity": "High", "status": "FAILED"},
        {"rule_id": "R015", "dimension": "Timeliness", "failure_rate_pct": 10.0, "severity": "High", "status": "FAILED"},
    ]
    df = pd.DataFrame({"Record_ID": ["MC1", "MC2", "MC3", "MC4", "MC5"]})
    
    report = calculate_scores_and_risk(mock_rules, df)
    dim_scores = report["dimension_scores"]

    # Completeness avg failure: 4.0 -> score = 96.0
    assert dim_scores["Completeness"] == 96.0
    # Validity avg failure: 2.0 -> score = 98.0
    assert dim_scores["Validity"] == 98.0
    # Uniqueness avg failure: 0.0 -> score = 100.0
    assert dim_scores["Uniqueness"] == 100.0
    # Consistency avg failure: 5.0 -> score = 95.0
    assert dim_scores["Consistency"] == 95.0
    # Timeliness avg failure: 10.0 -> score = 90.0
    assert dim_scores["Timeliness"] == 90.0

    # Expected weighted score (Completeness: 25%, Validity: 25%, Consistency: 20%, Uniqueness: 20%, Timeliness: 10%):
    # 0.25 * 96.0 + 0.25 * 98.0 + 0.20 * 95.0 + 0.20 * 100.0 + 0.10 * 90.0
    expected_score = round(0.25 * 96.0 + 0.25 * 98.0 + 0.20 * 95.0 + 0.20 * 100.0 + 0.10 * 90.0, 2)
    assert report["overall_quality_score"] == expected_score
    assert report["overall_quality_score"] == 96.5


def test_result_service_single_source_of_truth_and_recalculates_authoritative_score(tmp_path):
    """Verify backend get_run_statistics recalculates the exact authoritative overall score even if old score was 67.0."""
    init_db()

    dim_scores = {
        "Completeness": 97.0,
        "Validity": 99.5,
        "Consistency": 95.2,
        "Uniqueness": 100.0,
        "Timeliness": 100.0
    }
    # Expected: 0.25*97 + 0.25*99.5 + 0.20*95.2 + 0.20*100 + 0.10*100 = 24.25 + 24.875 + 19.04 + 20.0 + 10.0 = 98.165 -> 98.16
    expected_score = round(0.25 * 97.0 + 0.25 * 99.5 + 0.20 * 95.2 + 0.20 * 100.0 + 0.10 * 100.0, 2)

    report_path = tmp_path / "final_anomaly_report.json"
    report_path.write_text(json.dumps([]), encoding="utf-8")

    # Simulate old JSON having 67.0 stored
    quality_path = tmp_path / "quality_report.json"
    quality_path.write_text(
        json.dumps({
            "overall_quality_score": 67.0,
            "overall_risk_level": "FAIL",
            "dimension_scores": dim_scores
        }),
        encoding="utf-8"
    )

    db = SessionLocal()
    try:
        run = save_analysis_run(db, filename="dq_test.csv", report_json_path=str(report_path), status="completed")
        stats = get_run_statistics(db, run.id)

        # Must be dynamically corrected to authoritative score
        assert stats["overall_data_quality_score"] == expected_score
        assert stats["overall_data_quality_score"] > 95.0
        assert stats["dimension_scores"]["Timeliness"] == 100.0
        assert stats["overall_risk_level"] == "LOW"
    finally:
        db.close()
