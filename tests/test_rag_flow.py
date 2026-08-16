import json
import os
import tempfile

from UC10_Anomaly_Monitor.rca.rag import generate_rag_recommendation


def test_generate_rag_recommendation_for_duration_reject():
    current = {
        "incident_id": "PH201432",
        "record_type": "PHARMACY_CLAIM",
        "severity": "MEDIUM",
        "summary": "",
        "anomaly_signals": {},
        "evidence": [
            "statistical: {'zscore': False, 'iqr': False}",
            "isolation_forest: {'is_anomaly': True, 'raw_score': -0.14466701096706058, 'severity_0to1': 1.0}",
            "correlation: {'anomaly': False, 'residual': -6.8379620913456165, 'quantity_supply_residual': -2.739367041676701}"
        ],
        "observed_facts": [
            "status: REJECTED",
            "denial_reason: 88_DUR_REJECT",
            "auth_required_flag: Y",
            "days_supply: 90",
            "quantity_dispensed: 101",
            "billed_amount: 257151.103687372",
            "allowed_amount: 2122.63",
            "paid_amount: 2122.63",
            "ml_signal_count: 1"
        ],
        "possible_causes": [
            "Isolation forest algorithm detected an anomaly due to abnormal feature scores",
            "Correlation analysis suggests no anomaly but residual values indicate potential discrepancy"
        ],
        "likely_root_cause": "Insufficient evidence to determine root cause.",
        "confidence": 0.5,
        "impact": "",
        "recommended_actions": [],
        "additional_checks_required": []
    }

    historical = [
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
            "correlation_anomaly": False,
            "root_cause": "Duration-based pharmacy authorization mismatch; claim exceeded allowed days-supply for the selected drug.",
            "resolution_used": "Validated policy duration override, confirmed days-supply and NDC mapping, routed to pharmacy exception review.",
            "recommended_actions": [
                "Validate days-supply against plan policy.",
                "Check if the drug authorization rules were applied correctly.",
                "Escalate to pharmacy adjudication for exception review."
            ],
            "impact": "Claim denied and delayed dispensation.",
            "confidence": 0.88
        },
        {
            "incident_id": "PH201330",
            "record_type": "PHARMACY_CLAIM",
            "status": "REJECTED",
            "denial_reason_code": "88_DUR_REJECT",
            "auth_required_flag": "Y",
            "days_supply": 85,
            "quantity_dispensed": 90,
            "billed_amount": 220000,
            "allowed_amount": 2000,
            "paid_amount": 2000,
            "iso_anomaly": True,
            "iso_severity": 0.88,
            "correlation_anomaly": False,
            "root_cause": "Pharmacy exception queue required manual review due to duration policy mismatch.",
            "resolution_used": "Reviewed prior authorization and plan rule for refill duration; approved after manual review.",
            "recommended_actions": [
                "Review prior authorization limits.",
                "Check health-plan duration rules for refill exceptions.",
                "Re-run pharmacy adjudication after policy validation."
            ],
            "impact": "Delay in dispensing and resubmission burden.",
            "confidence": 0.82
        }
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        kb_path = os.path.join(tmpdir, "kb.json")
        with open(kb_path, "w", encoding="utf-8") as f:
            json.dump({"cases": historical}, f)

        result = generate_rag_recommendation(current, kb_path=kb_path)

    assert result["likely_root_cause"]
    assert result["recommended_actions"]
    assert isinstance(result["additional_checks_required"], list)
    assert 0.0 <= float(result["confidence"]) <= 1.0
    assert any("duration" in action.lower() or "auth" in action.lower() for action in result["recommended_actions"]) 
