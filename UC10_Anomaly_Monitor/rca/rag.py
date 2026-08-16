import json
import os
from typing import Any, Dict, List

from UC10_Anomaly_Monitor.rca.hybrid_kb import HistoricalCaseKB
from UC10_Anomaly_Monitor.rca.vector_kb import ChromaCaseKB


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _extract_record_fields(record: Dict[str, Any]) -> Dict[str, Any]:
    fields = {
        "incident_id": record.get("incident_id") or record.get("Record_ID") or "",
        "record_type": record.get("record_type") or record.get("Record_Type") or "",
        "status": record.get("status") or record.get("Status") or "",
        "denial_reason_code": record.get("denial_reason_code") or record.get("Denial_Reason_Code") or record.get("denial_reason") or "",
        "auth_required_flag": record.get("auth_required_flag") or record.get("Auth_Required_Flag") or "",
        "days_supply": record.get("days_supply") or record.get("Days_Supply"),
        "quantity_dispensed": record.get("quantity_dispensed") or record.get("Quantity_Dispensed"),
        "billed_amount": record.get("billed_amount") or record.get("Billed_Amount"),
        "allowed_amount": record.get("allowed_amount") or record.get("Allowed_Amount"),
        "paid_amount": record.get("paid_amount") or record.get("Paid_Amount"),
        "iso_anomaly": record.get("iso_anomaly") or record.get("ISO_Is_Anomaly") or False,
        "iso_severity": record.get("iso_severity") or record.get("ISO_Severity_0to1") or 0.0,
        "correlation_anomaly": record.get("correlation_anomaly") or record.get("Correlation_Anomaly") or False,
        "quantity_supply_anomaly": record.get("quantity_supply_anomaly") or record.get("Quantity_Supply_Anomaly") or False,
        "ml_signal_count": record.get("ml_signal_count") or record.get("ML_Anomaly_Signal_Count") or 0,
    }
    return fields


def _to_float(value: Any) -> float:
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _similarity_score(current: Dict[str, Any], historical: Dict[str, Any]) -> float:
    score = 0.0
    current_f = _extract_record_fields(current)
    hist_f = _extract_record_fields(historical)

    if current_f["record_type"] and hist_f["record_type"] and current_f["record_type"] == hist_f["record_type"]:
        score += 0.3
    if current_f["status"] and hist_f["status"] and current_f["status"] == hist_f["status"]:
        score += 0.2
    if current_f["denial_reason_code"] and hist_f["denial_reason_code"] and current_f["denial_reason_code"] == hist_f["denial_reason_code"]:
        score += 0.25
    if current_f["auth_required_flag"] and hist_f["auth_required_flag"] and current_f["auth_required_flag"] == hist_f["auth_required_flag"]:
        score += 0.1

    for field in ["days_supply", "quantity_dispensed", "billed_amount", "allowed_amount", "paid_amount"]:
        cur = _to_float(current_f.get(field))
        h = _to_float(hist_f.get(field))
        if cur > 0 and h > 0:
            ratio = min(cur, h) / max(cur, h)
            score += 0.05 * ratio

    if bool(current_f["iso_anomaly"]) == bool(hist_f["iso_anomaly"]):
        score += 0.05
    if bool(current_f["correlation_anomaly"]) == bool(hist_f["correlation_anomaly"]):
        score += 0.05
    if bool(current_f["quantity_supply_anomaly"]) == bool(hist_f["quantity_supply_anomaly"]):
        score += 0.05

    return min(score, 1.0)


def _load_historical_cases(kb_path: str | None = None) -> List[Dict[str, Any]]:
    if kb_path is None:
        candidate_paths = [
            os.path.join(os.getcwd(), "Data", "historical_resolution_cases.json"),
            os.path.join(os.getcwd(), "log", "historical_resolution_cases.json"),
            os.path.join(os.path.dirname(__file__), "..", "..", "Data", "historical_resolution_cases.json"),
        ]
        for path in candidate_paths:
            if os.path.exists(path):
                kb_path = path
                break

    if kb_path is None or not os.path.exists(kb_path):
        return []

    with open(kb_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, dict):
        if "cases" in payload:
            return payload["cases"]
        if "historical_cases" in payload:
            return payload["historical_cases"]
        return [payload]
    if isinstance(payload, list):
        return payload
    return []


def retrieve_similar_cases(current_record: Dict[str, Any], kb_path: str | None = None, limit: int = 5) -> List[Dict[str, Any]]:
    vector_kb = ChromaCaseKB(kb_path=kb_path)
    vector_hits = vector_kb.search(current_record, limit=limit)
    if vector_hits:
        return vector_hits

    kb = HistoricalCaseKB(kb_path=kb_path)
    hits = kb.search(current_record, limit=limit)
    if hits:
        return hits

    historical = _load_historical_cases(kb_path)
    if not historical:
        return []

    scored = []
    for case in historical:
        score = _similarity_score(current_record, case)
        scored.append({"case": case, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return [item["case"] for item in scored[:limit] if item["score"] > 0.0]


def build_rag_context(current_record: Dict[str, Any], historical_cases: List[Dict[str, Any]]) -> str:
    current = json.dumps(current_record, ensure_ascii=False, indent=2)
    recent = []
    for i, case in enumerate(historical_cases, start=1):
        recent.append({
            "rank": i,
            "incident_id": case.get("incident_id") or case.get("Record_ID") or "",
            "record_type": case.get("record_type") or case.get("Record_Type") or "",
            "status": case.get("status") or case.get("Status") or "",
            "denial_reason_code": case.get("denial_reason_code") or case.get("Denial_Reason_Code") or case.get("denial_reason") or "",
            "auth_required_flag": case.get("auth_required_flag") or case.get("Auth_Required_Flag") or "",
            "days_supply": case.get("days_supply") or case.get("Days_Supply"),
            "quantity_dispensed": case.get("quantity_dispensed") or case.get("Quantity_Dispensed"),
            "iso_anomaly": case.get("iso_anomaly") or case.get("ISO_Is_Anomaly") or False,
            "iso_severity": case.get("iso_severity") or case.get("ISO_Severity_0to1") or 0.0,
            "root_cause": case.get("root_cause") or "",
            "resolution_used": case.get("resolution_used") or case.get("resolution") or "",
            "recommended_actions": case.get("recommended_actions") or case.get("recommendations") or [],
            "impact": case.get("impact") or "",
            "confidence": case.get("confidence") or 0.0,
        })

    return json.dumps({
        "current_anomaly": json.loads(current),
        "similar_historical_cases": recent,
    }, ensure_ascii=False, indent=2)


def _extract_denial_reason(current_record: Dict[str, Any]) -> str:
    for key in ["denial_reason_code", "Denial_Reason_Code", "denial_reason"]:
        val = current_record.get(key)
        if val:
            return str(val)

    for item in current_record.get("evidence", []) or []:
        if isinstance(item, str) and "denial" in item.lower():
            return item
    return ""


def build_rag_prompt(current_record: Dict[str, Any], historical_cases: List[Dict[str, Any]]) -> str:
    current_json = json.dumps(current_record, ensure_ascii=False, indent=2)
    historical_json = json.dumps(historical_cases, ensure_ascii=False, indent=2)
    return (
        "You are an RCA agent for healthcare claims anomalies. "
        "Use the current anomaly record and the historical similar cases to recommend the best solution.\n\n"
        f"CURRENT ANOMALY:\n{current_json}\n\n"
        f"HISTORICAL SIMILAR CASES:\n{historical_json}\n\n"
        "Instructions:\n"
        "1. Compare record type, denial reason, status, and anomaly pattern.\n"
        "2. Explain the likely root cause using the most relevant historical precedent.\n"
        "3. Recommend concrete actions that match the historical resolution pattern.\n"
        "4. Include additional checks when evidence is not conclusive.\n"
        "5. Return valid JSON only, matching the RCA schema.\n"
        "6. If evidence remains weak, keep likely_root_cause as 'Insufficient evidence to determine root cause.'"
    )


def generate_rag_recommendation(current_record: Dict[str, Any], kb_path: str | None = None, limit: int = 5) -> Dict[str, Any]:
    similar = retrieve_similar_cases(current_record, kb_path=kb_path, limit=limit)
    context = build_rag_context(current_record, similar)

    denial_reason = _extract_denial_reason(current_record)
    record_type = current_record.get("record_type") or current_record.get("Record_Type") or ""
    severity = current_record.get("severity") or "MEDIUM"

    if not similar:
        likely_root_cause = "Insufficient evidence to determine root cause."
        actions = [
            "Validate the claim status and denial reason against plan policy.",
            "Check whether the drug quantity and days-supply align with the provisioned authorization.",
            "Escalate to pharmacy adjudication or prior-authorization review for manual validation."
        ]
        extras = [
            "Confirm whether the denial reason code is consistent with payer policy.",
            "Review claim support documents and authorization notes.",
            "Compare this record against similar claims in the same drug category."
        ]
        confidence = 0.55
        recommendation = {
            "incident_id": current_record.get("incident_id") or current_record.get("Record_ID") or "",
            "record_type": record_type,
            "severity": severity,
            "summary": "No comparable historical resolution was found for this anomaly; follow standard validation flow.",
            "anomaly_signals": current_record.get("anomaly_signals") or {},
            "evidence": current_record.get("evidence") or [],
            "observed_facts": current_record.get("observed_facts") or [],
            "possible_causes": current_record.get("possible_causes") or [],
            "likely_root_cause": likely_root_cause,
            "confidence": confidence,
            "impact": current_record.get("impact") or "Potential delay or rejection of medication dispensation.",
            "recommended_actions": actions,
            "additional_checks_required": extras,
        }
        return recommendation

    roots = []
    actions = []
    extras = []
    for case in similar:
        if case.get("root_cause"):
            roots.append(case.get("root_cause"))
        if case.get("recommended_actions"):
            actions.extend(case.get("recommended_actions", []))
        if case.get("resolution_used"):
            extras.append(case.get("resolution_used"))

    if not actions:
        actions = [
            "Validate authorization and days-supply against payer policy.",
            "Check whether the denial reason code matches the adjudication logic.",
            "Escalate to pharmacy exception review for manual evaluation."
        ]

    dedup_actions = []
    seen = set()
    for item in actions:
        key = item.lower().strip()
        if key and key not in seen:
            dedup_actions.append(item)
            seen.add(key)

    probable_root = (
        roots[0]
        if roots
        else "Historical cases suggest a policy or adjudication mismatch in the pharmacy claim workflow."
    )

    confidence = min(0.95, 0.6 + (len(similar) * 0.06))
    if denial_reason:
        probable_root = f"Historical matches for {record_type} records rejected with {denial_reason} suggest a policy or adjudication mismatch in the rule engine, especially around duration and authorization checks."

    recommendation = {
        "incident_id": current_record.get("incident_id") or current_record.get("Record_ID") or "",
        "record_type": record_type,
        "severity": severity,
        "summary": f"Matched {len(similar)} similar historical {record_type.lower()} cases with the same rejection pattern.",
        "anomaly_signals": current_record.get("anomaly_signals") or {},
        "evidence": current_record.get("evidence") or [],
        "observed_facts": current_record.get("observed_facts") or [],
        "possible_causes": current_record.get("possible_causes") or [
            "Anomaly in multivariate pharmacy claim features.",
            "Plan duration/authorization policy mismatch."
        ],
        "likely_root_cause": probable_root,
        "confidence": round(confidence, 2),
        "impact": current_record.get("impact") or "Possible medication delay or resubmission burden caused by claim rejection.",
        "recommended_actions": dedup_actions[:6],
        "additional_checks_required": [
            "Check if the claim was denied under a duration-policy rule instead of a true data-quality error.",
            "Validate the drug authorization and days-supply against payer policy."
        ] + extras[:2],
    }

    recommendation["rag_context"] = context
    return recommendation
