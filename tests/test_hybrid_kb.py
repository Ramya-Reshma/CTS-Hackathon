import json
import os
import tempfile

from UC10_Anomaly_Monitor.rca.hybrid_kb import HistoricalCaseKB


def test_hybrid_kb_prioritizes_duration_denial_similarity():
    cases = [
        {
            "incident_id": "PH201771",
            "record_type": "PHARMACY_CLAIM",
            "status": "REJECTED",
            "denial_reason_code": "88_DUR_REJECT",
            "auth_required_flag": "Y",
            "days_supply": 92,
            "quantity_dispensed": 96,
            "billed_amount": 248000,
            "allowed_amount": 2100,
            "paid_amount": 2100,
            "iso_anomaly": True,
            "iso_severity": 0.95,
            "root_cause": "Duration-based pharmacy authorization mismatch.",
            "resolution_used": "Validated the plan duration rule and routed to pharmacy exception review.",
            "recommended_actions": [
                "Validate days-supply against the plan policy."
            ],
            "confidence": 0.88
        },
        {
            "incident_id": "PA300123",
            "record_type": "PRIOR_AUTH",
            "status": "APPROVED",
            "denial_reason_code": "",
            "auth_required_flag": "N",
            "days_supply": 14,
            "quantity_dispensed": 5,
            "billed_amount": 1800,
            "allowed_amount": 1700,
            "paid_amount": 1700,
            "iso_anomaly": False,
            "iso_severity": 0.1,
            "root_cause": "No anomaly.",
            "resolution_used": "Default approved case.",
            "recommended_actions": [
                "No action needed."
            ],
            "confidence": 0.9
        }
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        kb_path = os.path.join(tmpdir, "cases.json")
        with open(kb_path, "w", encoding="utf-8") as f:
            json.dump({"cases": cases}, f)

        kb = HistoricalCaseKB(kb_path=kb_path)
        current = {
            "incident_id": "PH201432",
            "record_type": "PHARMACY_CLAIM",
            "status": "REJECTED",
            "denial_reason_code": "88_DUR_REJECT",
            "auth_required_flag": "Y",
            "days_supply": 90,
            "quantity_dispensed": 101,
            "billed_amount": 257151.10,
            "allowed_amount": 2122.63,
            "paid_amount": 2122.63,
            "iso_anomaly": True,
            "iso_severity": 1.0,
            "evidence": [
                "statistical: {'zscore': False, 'iqr': False}",
                "isolation_forest: {'is_anomaly': True, 'raw_score': -0.14466701096706058, 'severity_0to1': 1.0}",
                "correlation: {'anomaly': False, 'residual': -6.8379620913456165, 'quantity_supply_residual': -2.739367041676701}"
            ]
        }

        hits = kb.search(current, limit=3)

    assert hits
    assert hits[0]["incident_id"] == "PH201771"
    assert hits[0]["score"] > 0.4
