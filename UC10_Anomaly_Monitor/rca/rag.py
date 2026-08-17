import json
import os
from typing import Any, Dict, List, Optional
from UC10_Anomaly_Monitor.rca.vector_kb import ChromaCaseKB
from UC10_Anomaly_Monitor.rca import prompts, schemas


def retrieve_similar_cases(
    current_record: Dict[str, Any],
    kb_path: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Retrieve top-K similar healthcare anomaly knowledge records using the RAG knowledge base.
    Prioritizes ChromaDB vector retrieval with all-MiniLM-L6-v2 embeddings.
    """
    kb = ChromaCaseKB(kb_path=kb_path)
    hits = kb.search(current_record, limit=limit)
    return hits


def build_rag_prompt(
    current_evidence: Dict[str, Any],
    retrieved_knowledge: List[Dict[str, Any]]
) -> str:
    """
    Construct the final user prompt separating CURRENT ANOMALY and RETRIEVED KNOWLEDGE.
    """
    ev_json = json.dumps(current_evidence, indent=2, ensure_ascii=False)
    kb_json = json.dumps(retrieved_knowledge, indent=2, ensure_ascii=False)
    
    return prompts.USER_PROMPT_TEMPLATE.format(
        current_evidence=ev_json,
        retrieved_knowledge=kb_json
    )


def generate_rag_recommendation(
    current_evidence: Dict[str, Any],
    kb_path: Optional[str] = None,
    limit: int = 5
) -> schemas.RCAAnalysis:
    """
    Deterministic rule-based fallback when LLM endpoints are unavailable.
    Constructs a defensible RCA strictly derived from available evidence.
    """
    similar = retrieve_similar_cases(current_evidence, kb_path=kb_path, limit=limit)
    
    rec_id = current_evidence.get("record_id") or "UNKNOWN"
    rec_type = current_evidence.get("record_type") or "CLAIM"
    
    iso = current_evidence.get("isolation_forest", {})
    corr = current_evidence.get("correlation", {})
    stat = current_evidence.get("statistical", {})
    fin = current_evidence.get("financials", {})
    sup = current_evidence.get("supply", {})
    dq = current_evidence.get("data_quality", [])
    
    iso_anomaly = iso.get("is_anomaly", False)
    iso_raw = iso.get("raw_score")
    iso_sev = iso.get("severity_0to1", 0.0)
    
    corr_anomaly = corr.get("anomaly", False)
    corr_res = corr.get("residual")
    qs_anomaly = corr.get("quantity_supply_anomaly", False)
    qs_res = corr.get("quantity_supply_residual")
    
    zscore = stat.get("zscore_anomaly", False)
    iqr = stat.get("iqr_anomaly", False)
    affected = stat.get("affected_fields", [])
    
    signal_count = current_evidence.get("ml_signal_count", 0)

    # 1. Determine priority
    if (iso_sev and iso_sev >= 0.8) or signal_count >= 2:
        priority = "HIGH"
    elif iso_anomaly or corr_anomaly or qs_anomaly or (iso_sev and iso_sev >= 0.5):
        priority = "MEDIUM"
    else:
        priority = "LOW"

    # 2. Determine anomaly type
    if qs_anomaly:
        anomaly_type = "Quantity/Supply Anomaly"
    elif corr_anomaly:
        anomaly_type = "Correlation Anomaly"
    elif iso_anomaly:
        anomaly_type = f"{rec_type.replace('_', ' ').title()} Multivariate Anomaly"
    elif affected:
        anomaly_type = "Statistical Distribution Outlier"
    else:
        anomaly_type = "Healthcare Anomaly"

    # 3. Formulate root_cause (WHY the system flagged the record)
    rc_parts = []
    if iso_anomaly:
        rc_parts.append(f"Isolation Forest flagged the record as anomalous with raw score {iso_raw} and severity {iso_sev}.")
    else:
        rc_parts.append("Isolation Forest did not flag an anomaly.")

    if corr_anomaly:
        rc_parts.append(f"Correlation analysis flagged an anomaly between Paid and Allowed amount with residual {corr_res}.")
    elif corr_res is not None:
        rc_parts.append(f"Correlation analysis did not classify the record as anomalous, although the residual was {corr_res}.")

    if qs_anomaly:
        rc_parts.append(f"Quantity vs Days Supply check flagged an anomaly with residual {qs_res}.")

    if not zscore and not iqr:
        rc_parts.append("Z-score and IQR statistical checks did not detect an anomaly.")
    elif affected:
        rc_parts.append(f"Statistical checks identified outliers in {', '.join(affected)}.")

    root_cause_explanation = f"The record was flagged with an ML anomaly signal count of {signal_count}. " + " ".join(rc_parts)

    # 4. Formulate observed facts
    facts = [
        f"The record is a {rec_type} with ID {rec_id}."
    ]
    if current_evidence.get("provider", {}).get("provider_npi"):
        facts.append(f"The provider NPI is {current_evidence['provider']['provider_npi']}.")
    if current_evidence.get("beneficiary", {}).get("beneficiary_id"):
        facts.append(f"The beneficiary ID is {current_evidence['beneficiary']['beneficiary_id']}.")
    if fin.get("billed") is not None:
        facts.append(f"Financial parameters: Billed=${fin.get('billed')}, Paid=${fin.get('paid')}, Allowed=${fin.get('allowed')}.")
    if sup.get("quantity_dispensed") is not None or sup.get("days_supply") is not None:
        facts.append(f"Supply parameters: Quantity Dispensed={sup.get('quantity_dispensed')}, Days Supply={sup.get('days_supply')}.")
    if iso_anomaly:
        facts.append(f"Isolation Forest flagged an anomaly (score={iso_raw}, severity={iso_sev}).")
    if corr_res is not None:
        facts.append(f"Correlation residual between Paid and Allowed is {corr_res} (flag={corr_anomaly}).")
    if qs_res is not None:
        facts.append(f"Quantity Dispensed vs Days Supply residual is {qs_res} (flag={qs_anomaly}).")

    # 5. Formulate possible causes and likely root cause based on retrieved knowledge
    possible_causes = []
    likely_root_cause = "Insufficient evidence to determine root cause."
    actions = []

    if similar:
        for s in similar[:3]:
            if s.get("Root_Cause"):
                possible_causes.append(f"Domain precedent ({s.get('Anomaly_Name', 'Pattern')}): {s['Root_Cause']}")
            if s.get("Recommended_Fix"):
                actions.append(s["Recommended_Fix"])
        
        # Grounding check: Only attribute likely root cause if pattern strictly matches
        top_match = similar[0]
        if top_match.get("similarity", 0) >= 0.75 and top_match.get("Root_Cause"):
            likely_root_cause = top_match["Root_Cause"]

    if not possible_causes:
        possible_causes = [
            "Data entry, coding, or source mapping discrepancy may contribute to the anomaly.",
            "Provider billing pattern or clinical utilization variance may explain the deviation.",
            "Plan authorization or policy rules may require validation."
        ]

    if not actions:
        actions = [
            "Validate provider master data, billing records, and clinical documentation.",
            "Verify pricing, allowed amount formulas, and contractual discount schedules.",
            "Review historical claims submitted by this provider for pattern persistence.",
            "Confirm drug quantity dispensed against authorized days supply."
        ]

    return schemas.RCAAnalysis(
        priority=priority,
        record_id=rec_id,
        anomaly_type=anomaly_type,
        root_cause=root_cause_explanation,
        observed_facts=facts,
        possible_causes=possible_causes,
        likely_root_cause=likely_root_cause,
        recommended_actions=actions[:5]
    )
