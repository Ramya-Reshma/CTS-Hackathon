import requests
import json

BASE = "http://localhost:8000/api/auto-resolve"

print("================================================================")
print("RUNNING 12 CROSS-LAYER AUTO-RESOLUTION AGENT VALIDATION TESTS")
print("================================================================")

# TEST 1: Safe missing derived field
print("\n[TEST 1] Safe missing derived feature (Source inputs available)")
t1_payload = {
    "run_id": "RUN-TEST-001",
    "record_id": "PH201432",
    "issue_type": "DATA_QUALITY_MISSING_DERIVABLE_FEATURE",
    "issue_description": "Derived metric Allowed_To_Billed_Ratio is unpopulated.",
    "evidence": [
        {"source": "RAW_CSV", "field": "Billed_Amount", "value": 150.0, "authority": "SOURCE"},
        {"source": "RAW_CSV", "field": "Allowed_Amount", "value": 120.0, "authority": "SOURCE"},
    ],
    "root_cause": "Derived field calculation omitted during ingestion batch.",
    "context_data": {"source_inputs_available": True}
}
r1_eval = requests.post(f"{BASE}/evaluate", json=t1_payload).json()
print("  Eval Decision:", r1_eval.get("decision_state"), "| Action:", r1_eval.get("proposed_action"))
assert r1_eval.get("auto_fix_eligible") is True
r1_exec = requests.post(f"{BASE}/execute", json={
    "run_id": "RUN-TEST-001",
    "record_id": "PH201432",
    "issue_id": r1_eval.get("issue_id"),
    "issue_type": "DATA_QUALITY_MISSING_DERIVABLE_FEATURE",
    "action_id": r1_eval.get("proposed_action"),
    "context_data": {"layer": "DATA_QUALITY"}
}).json()
print("  Exec Status:", r1_exec.get("status"), "| Validation:", r1_exec.get("validation_status"))
assert r1_exec.get("status") == "AUTO_FIXED"
print("  => TEST 1 PASSED [OK]")

# TEST 2: Missing value with no authoritative source
print("\n[TEST 2] Missing value with NO authoritative source (e.g. Missing Provider NPI)")
t2_payload = {
    "run_id": "RUN-TEST-001",
    "record_id": "MC100034",
    "issue_type": "DATA_QUALITY_MISSING_SOURCE_FIELD",
    "issue_description": "Provider NPI is NULL across all source files.",
    "evidence": [
        {"source": "SOURCE_DATA", "field": "Provider_NPI", "value": None, "authority": "SOURCE"},
        {"source": "RAG_POLICY", "field": "HIPAA_Rule", "value": "NPI format is 10 digits", "authority": "RAG"}
    ],
    "root_cause": "Provider NPI omitted at origin by billing submitter.",
}
r2_eval = requests.post(f"{BASE}/evaluate", json=t2_payload).json()
print("  Eval Decision:", r2_eval.get("decision_state"), "| Action:", r2_eval.get("proposed_action"))
assert r2_eval.get("auto_fix_eligible") is False
assert r2_eval.get("decision_state") == "MANUAL_REVIEW_REQUIRED"
print("  => TEST 2 PASSED [OK] (No fabrication permitted)")

# TEST 3: Duplicate with deterministic duplicate rule
print("\n[TEST 3] Duplicate with deterministic duplicate rule")
t3_payload = {
    "run_id": "RUN-TEST-001",
    "record_id": "PH201432_DUP",
    "issue_type": "FEATURE_ENGINEERING_DUPLICATE_RECORD",
    "issue_description": "Exact byte-for-byte duplicate encounter submitted twice.",
    "evidence": [
        {"source": "SOURCE_DATA", "field": "Record_ID", "value": "PH201432", "authority": "SOURCE"},
        {"source": "VALIDATION_ENGINE", "field": "Duplicate_Count", "value": 2, "authority": "VALIDATION"}
    ],
    "root_cause": "Batch resent by clearinghouse.",
    "context_data": {"duplicate_retention_deterministic": True}
}
r3_eval = requests.post(f"{BASE}/evaluate", json=t3_payload).json()
print("  Eval Decision:", r3_eval.get("decision_state"), "| Action:", r3_eval.get("proposed_action"))
assert r3_eval.get("auto_fix_eligible") is True
r3_exec = requests.post(f"{BASE}/execute", json={
    "run_id": "RUN-TEST-001",
    "record_id": "PH201432_DUP",
    "issue_id": r3_eval.get("issue_id"),
    "issue_type": "FEATURE_ENGINEERING_DUPLICATE_RECORD",
    "action_id": r3_eval.get("proposed_action"),
    "context_data": {"layer": "FEATURE_ENGINEERING"}
}).json()
print("  Exec Status:", r3_exec.get("status"), "| Validation:", r3_exec.get("validation_status"))
assert r3_exec.get("status") == "AUTO_FIXED"
print("  => TEST 3 PASSED [OK]")

# TEST 4: Duplicate where retention is ambiguous
print("\n[TEST 4] Duplicate where retention is ambiguous")
t4_payload = {
    "run_id": "RUN-TEST-001",
    "record_id": "MC500112",
    "issue_type": "FEATURE_ENGINEERING_DUPLICATE_RECORD",
    "issue_description": "Multiple encounters with conflicting claim line items.",
    "evidence": [
        {"source": "SOURCE_DATA", "field": "Record_ID", "value": "MC500112", "authority": "SOURCE"},
    ],
    "root_cause": "Split billing conflict.",
    "context_data": {"duplicate_retention_deterministic": False}
}
r4_eval = requests.post(f"{BASE}/evaluate", json=t4_payload).json()
print("  Eval Decision:", r4_eval.get("decision_state"), "| Action:", r4_eval.get("proposed_action"))
assert r4_eval.get("auto_fix_eligible") is False
assert r4_eval.get("decision_state") == "MANUAL_REVIEW_REQUIRED"
print("  => TEST 4 PASSED [OK]")

# TEST 5: Missing SLA serialization
print("\n[TEST 5] Missing SLA serialization (Engine calculation exists)")
t5_payload = {
    "run_id": "RUN-TEST-001",
    "record_id": "PH00022",
    "issue_type": "SERIALIZATION_MISSING_SLA_OUTPUT",
    "issue_description": "SLA engine produced BREACHED (3.5 days vs 2 days target) but final artifact has NULL SLA.",
    "evidence": [
        {"source": "SLA_ENGINE", "field": "SLA_Status", "value": "BREACHED", "authority": "BACKEND"},
        {"source": "INTEGRITY_CHECK", "field": "Final_SLA_Field", "value": None, "authority": "VALIDATION"}
    ],
    "root_cause": "Serialization mapper dropped SLA column before API persistence.",
    "context_data": {"authoritative_result_available": True}
}
r5_eval = requests.post(f"{BASE}/evaluate", json=t5_payload).json()
print("  Eval Decision:", r5_eval.get("decision_state"), "| Action:", r5_eval.get("proposed_action"))
assert r5_eval.get("auto_fix_eligible") is True
r5_exec = requests.post(f"{BASE}/execute", json={
    "run_id": "RUN-TEST-001",
    "record_id": "PH00022",
    "issue_id": r5_eval.get("issue_id"),
    "issue_type": "SERIALIZATION_MISSING_SLA_OUTPUT",
    "action_id": r5_eval.get("proposed_action"),
    "context_data": {"layer": "SLA"}
}).json()
print("  Exec Status:", r5_exec.get("status"), "| Validation:", r5_exec.get("validation_status"))
assert r5_exec.get("status") == "AUTO_FIXED"
print("  => TEST 5 PASSED [OK]")

# TEST 6: Statistical anomaly classification only (Anomalies are not errors)
print("\n[TEST 6] Statistical anomaly detection flag only")
t6_payload = {
    "run_id": "RUN-TEST-001",
    "record_id": "PA90211",
    "issue_type": "ANOMALY_DETECTION_STATISTICAL_FLAG",
    "issue_description": "Isolation Forest flagged record as anomalous (z-score=3.8).",
    "evidence": [
        {"source": "ISOLATION_FOREST", "field": "Score", "value": -0.72, "authority": "BACKEND"}
    ],
    "root_cause": "High dollar amount outlier relative to peer group.",
}
r6_eval = requests.post(f"{BASE}/evaluate", json=t6_payload).json()
print("  Eval Decision:", r6_eval.get("decision_state"), "| Action:", r6_eval.get("proposed_action"))
assert r6_eval.get("auto_fix_eligible") is False
assert r6_eval.get("decision_state") == "NO_ACTION_REQUIRED"
print("  => TEST 6 PASSED [OK] (Anomaly signal preserved intact)")

# TEST 7: Missing anomaly result with deterministic rerun
print("\n[TEST 7] Missing anomaly result with deterministic rerun")
t7_payload = {
    "run_id": "RUN-TEST-001",
    "record_id": "MC400199",
    "issue_type": "ANOMALY_RESULT_MISSING",
    "issue_description": "Scoring worker timed out on single claim record.",
    "evidence": [
        {"source": "ANOMALY_ENGINE", "field": "Evaluated", "value": False, "authority": "BACKEND"}
    ],
    "root_cause": "Worker transient timeout.",
}
r7_eval = requests.post(f"{BASE}/evaluate", json=t7_payload).json()
print("  Eval Decision:", r7_eval.get("decision_state"), "| Action:", r7_eval.get("proposed_action"))
assert r7_eval.get("auto_fix_eligible") is True
r7_exec = requests.post(f"{BASE}/execute", json={
    "run_id": "RUN-TEST-001",
    "record_id": "MC400199",
    "issue_id": r7_eval.get("issue_id"),
    "issue_type": "ANOMALY_RESULT_MISSING",
    "action_id": r7_eval.get("proposed_action"),
    "context_data": {"layer": "ANOMALY_DETECTION"}
}).json()
print("  Exec Status:", r7_exec.get("status"), "| Validation:", r7_exec.get("validation_status"))
assert r7_exec.get("status") == "AUTO_FIXED"
print("  => TEST 7 PASSED [OK]")

# TEST 8: Missing anomaly result with simulated failed validation (Rollback test)
print("\n[TEST 8] Missing anomaly result with failed validation -> ROLLBACK")
r8_exec = requests.post(f"{BASE}/execute", json={
    "run_id": "RUN-TEST-001",
    "record_id": "MC400199",
    "issue_id": "ISSUE-FAIL-01",
    "issue_type": "ANOMALY_RESULT_MISSING",
    "action_id": "RERUN_EXISTING_ANOMALY_CALCULATION",
    "context_data": {"layer": "ANOMALY_DETECTION", "simulate_validation_failure": True}
}).json()
print("  Exec Status:", r8_exec.get("status"), "| Validation:", r8_exec.get("validation_status"))
assert r8_exec.get("status") == "FIX_FAILED_ROLLED_BACK"
assert r8_exec.get("validation_status") == "FAIL"
print("  => TEST 8 PASSED [OK] (Reverted cleanly)")

# TEST 9: Final output missing SLA results (Propagation check)
print("\n[TEST 9] Final output missing SLA results (Propagation recovery)")
t9_payload = {
    "run_id": "RUN-TEST-001",
    "record_id": "PH00045",
    "issue_type": "SERIALIZATION_MISSING_SLA_OUTPUT",
    "issue_description": "Final output is missing SLA results while Stage 3 SLA engine holds 5 breaches.",
    "evidence": [
        {"source": "SLA_STAGE_3", "field": "Breach_Count", "value": 5, "authority": "BACKEND"},
        {"source": "FINAL_STAGE_4", "field": "SLA_Results", "value": 0, "authority": "VALIDATION"}
    ],
    "root_cause": "Downstream pipeline gap.",
    "context_data": {"authoritative_result_available": True}
}
r9_eval = requests.post(f"{BASE}/evaluate", json=t9_payload).json()
assert r9_eval.get("auto_fix_eligible") is True
print("  Eval Decision:", r9_eval.get("decision_state"), "| Action:", r9_eval.get("proposed_action"))
print("  => TEST 9 PASSED [OK]")

# TEST 10: LLM attempts to propose fabricated clinical value
print("\n[TEST 10] LLM attempts to fabricate clinical code / NPI")
t10_payload = {
    "run_id": "RUN-TEST-001",
    "record_id": "MC771122",
    "issue_type": "DATA_QUALITY_MISSING_SOURCE_FIELD",
    "issue_description": "Missing diagnosis code.",
    "evidence": [
        {"source": "LLM_INFERENCE", "field": "Proposed_Diagnosis", "value": "E11.9 (Type 2 Diabetes)", "authority": "LLM"}
    ],
    "root_cause": "Source omission.",
}
r10_eval = requests.post(f"{BASE}/evaluate", json=t10_payload).json()
assert r10_eval.get("auto_fix_eligible") is False
assert r10_eval.get("decision_state") == "MANUAL_REVIEW_REQUIRED"
print("  Eval Decision:", r10_eval.get("decision_state"), "| Rationale:", r10_eval.get("eligibility_reason")[:60] + "...")
print("  => TEST 10 PASSED [OK] (Fabricated LLM values blocked)")

# TEST 11: RAG recommending unsupported modification
print("\n[TEST 11] RAG recommending unsupported modification")
t11_payload = {
    "run_id": "RUN-TEST-001",
    "record_id": "PA10293",
    "issue_type": "DATA_QUALITY_MISSING_SOURCE_FIELD",
    "issue_description": "Missing Authorization Approval Date.",
    "evidence": [
        {"source": "RAG_KB", "field": "Guideline", "value": "Approval is typically 3 days after submission", "authority": "RAG"}
    ],
    "root_cause": "External auth system sync failure.",
}
r11_eval = requests.post(f"{BASE}/evaluate", json=t11_payload).json()
assert r11_eval.get("auto_fix_eligible") is False
assert r11_eval.get("decision_state") == "MANUAL_REVIEW_REQUIRED"
print("  Eval Decision:", r11_eval.get("decision_state"))
print("  => TEST 11 PASSED [OK] (RAG policy context cannot fabricate source timestamps)")

# TEST 12: Post-fix validation audit check
print("\n[TEST 12] Audit Trail Verification")
history = requests.get(f"{BASE}/history?run_id=RUN-TEST-001").json()
print("  Total Audit Records Logged:", len(history))
assert len(history) >= 4
statuses = [h["status"] for h in history]
print("  Logged Execution Statuses:", statuses)
assert "AUTO_FIXED" in statuses
assert "FIX_FAILED_ROLLED_BACK" in statuses
print("  => TEST 12 PASSED [OK] (Complete audit trail verified)")

print("\n================================================================")
print("ALL 12 CROSS-LAYER AUTO-RESOLUTION TESTS COMPLETED SUCCESSFULLY!")
print("================================================================")
