import requests
import json

BASE = "http://localhost:8000/api/auto-resolve"

print("=================================================================")
print("TESTING CROSS-LAYER PARITY ON REPRESENTATIVE RECORDS")
print("=================================================================")

# Test 1: TEST_0045 (Multi-signal: ML Anomaly + SLA Breached + DQ Pass)
t_0045 = {
    "run_id": "RUN-20260817200117-2ae592c6",
    "record_id": "TEST_0045",
    "issue_type": "ANOMALY_DETECTION_STATISTICAL_FLAG",
    "issue_description": "Record TEST_0045 flagged by detection engine (Isolation Forest Anomaly, Severity: MEDIUM).",
    "evidence": [
        {"source": "SOURCE_RECORD", "field": "Record_ID", "value": "TEST_0045", "authority": "SOURCE"},
        {"source": "SLA_ENGINE", "field": "SLA_Status", "value": "BREACHED", "authority": "BACKEND"},
        {"source": "ISOLATION_FOREST", "field": "ISO_Score", "value": -0.0589, "authority": "BACKEND"}
    ],
    "root_cause": "unusual relationship or multivariate feature combination learned by the anomaly model.",
    "context_data": {"layer": "ANOMALY_DETECTION"}
}
r1 = requests.post(f"{BASE}/evaluate", json=t_0045).json()
print("\n[RECORD TEST_0045] Multi-Signal Anomaly + SLA")
print("  Layer:", r1.get("layer"))
print("  Issue Type:", r1.get("issue_type"))
print("  Decision:", r1.get("decision_state"))
print("  Auto-Fix Eligible:", r1.get("auto_fix_eligible"))
assert r1.get("layer") == "ANOMALY_DETECTION"
assert r1.get("decision_state") == "NO_ACTION_REQUIRED"
assert r1.get("auto_fix_eligible") is False
print("  => PASSED [OK] (Does NOT collapse into fake Data Quality)")

# Test 2: TEST_0043 (Pure ML Anomaly)
t_0043 = {
    "run_id": "RUN-20260817200117-2ae592c6",
    "record_id": "TEST_0043",
    "issue_type": "ANOMALY_DETECTION_STATISTICAL_FLAG",
    "issue_description": "Record TEST_0043 flagged by Isolation Forest.",
    "evidence": [
        {"source": "SOURCE_RECORD", "field": "Record_ID", "value": "TEST_0043", "authority": "SOURCE"},
        {"source": "ISOLATION_FOREST", "field": "ISO_Score", "value": -0.0612, "authority": "BACKEND"}
    ],
    "root_cause": "Multivariate feature outlier.",
    "context_data": {"layer": "ANOMALY_DETECTION"}
}
r2 = requests.post(f"{BASE}/evaluate", json=t_0043).json()
print("\n[RECORD TEST_0043] Isolation Forest Anomaly")
print("  Layer:", r2.get("layer"))
print("  Decision:", r2.get("decision_state"))
assert r2.get("layer") == "ANOMALY_DETECTION"
assert r2.get("decision_state") == "NO_ACTION_REQUIRED"
print("  => PASSED [OK]")

# Test 3: TEST_0023 (Pure SLA Breach)
t_0023 = {
    "run_id": "RUN-20260817200117-2ae592c6",
    "record_id": "TEST_0023",
    "issue_type": "SLA_BREACH_EXPOSURE",
    "issue_description": "Statutory turnaround SLA deadline breached for TEST_0023 (3.4 days vs 2.0 target).",
    "evidence": [
        {"source": "SOURCE_RECORD", "field": "Record_ID", "value": "TEST_0023", "authority": "SOURCE"},
        {"source": "SLA_ENGINE", "field": "SLA_Status", "value": "BREACHED", "authority": "BACKEND"}
    ],
    "root_cause": "Processing queue backlog.",
    "context_data": {"layer": "SLA"}
}
r3 = requests.post(f"{BASE}/evaluate", json=t_0023).json()
print("\n[RECORD TEST_0023] SLA Breach")
print("  Layer:", r3.get("layer"))
print("  Decision:", r3.get("decision_state"))
print("  Proposed Action:", r3.get("proposed_action"))
assert r3.get("layer") == "SLA"
assert r3.get("decision_state") == "MANUAL_REVIEW_REQUIRED"
assert r3.get("proposed_action") == "MANUAL_REVIEW"
print("  => PASSED [OK] (Operational SLA breach routed to supervisory review, not fake DQ)")

# Test 4: MC100034 (Real Missing Source Field)
t_mc100034 = {
    "run_id": "RUN-20260817200117-2ae592c6",
    "record_id": "MC100034",
    "issue_type": "DATA_QUALITY_MISSING_SOURCE_FIELD",
    "issue_description": "Required Provider NPI is NULL in source record.",
    "evidence": [
        {"source": "SOURCE_RECORD", "field": "Provider_NPI", "value": None, "authority": "SOURCE"}
    ],
    "root_cause": "Omission at origin billing submission.",
    "context_data": {"layer": "DATA_QUALITY"}
}
r4 = requests.post(f"{BASE}/evaluate", json=t_mc100034).json()
print("\n[RECORD MC100034] Genuine Data Quality Issue")
print("  Layer:", r4.get("layer"))
print("  Decision:", r4.get("decision_state"))
print("  Proposed Action:", r4.get("proposed_action"))
assert r4.get("layer") == "DATA_QUALITY"
assert r4.get("decision_state") == "MANUAL_REVIEW_REQUIRED"
print("  => PASSED [OK] (No fabrication permitted)")

print("\n=================================================================")
print("ALL CROSS-LAYER RECORD PARITY CHECKS PASSED SUCCESSFULLY!")
print("=================================================================")
