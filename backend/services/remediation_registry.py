"""
Controlled Issue Taxonomy and Allowlisted Remediation Registry for the MEDLYTICS Auto-Resolution Agent.
Defines:
- 14-Layer Issue Taxonomy
- 5-Level Evidence Authority Hierarchy
- Explicitly Allowlisted Remediation Operations with Strict Preconditions & Risk Levels
"""

from typing import Dict, List, Any, Optional
from enum import Enum


class EvidenceAuthority(str, Enum):
    """5-Level Evidence Authority Hierarchy (Level 1 is highest authority)."""
    SOURCE = "SOURCE"          # Level 1: Original source data (CSV, XLSX, DB raw records)
    BACKEND = "BACKEND"        # Level 2: Authoritative engine calculations (SLA, Anomaly, DQ, FE)
    VALIDATION = "VALIDATION"  # Level 3: Existing deterministic validation & integrity results
    RAG = "RAG"                # Level 4: Retrieved knowledge base policies & context
    LLM = "LLM"                # Level 5: AI diagnostic reasoning (Lowest authority; cannot fabricate)


class IssueLayer(str, Enum):
    """14 Monitored Pipeline Layers."""
    SOURCE_DATA = "SOURCE_DATA"
    DATA_QUALITY = "DATA_QUALITY"
    PREPROCESSING = "PREPROCESSING"
    FEATURE_ENGINEERING = "FEATURE_ENGINEERING"
    ANOMALY_DETECTION = "ANOMALY_DETECTION"
    ISOLATION_FOREST = "ISOLATION_FOREST"
    CORRELATION_ANALYSIS = "CORRELATION_ANALYSIS"
    QUANTITY_SUPPLY_ANALYSIS = "QUANTITY_SUPPLY_ANALYSIS"
    SLA = "SLA"
    PIPELINE_INTEGRITY = "PIPELINE_INTEGRITY"
    FINAL_OUTPUT = "FINAL_OUTPUT"
    EVIDENCE_BUILDER = "EVIDENCE_BUILDER"
    RAG_RETRIEVAL = "RAG_RETRIEVAL"
    ROOT_CAUSE_ANALYSIS = "ROOT_CAUSE_ANALYSIS"
    RECOMMENDATION_ENGINE = "RECOMMENDATION_ENGINE"


# Controlled Issue Taxonomy
ISSUE_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "DATA_QUALITY_MISSING_DERIVABLE_FEATURE": {
        "layer": IssueLayer.DATA_QUALITY.value,
        "subtype": "MISSING_DERIVABLE_FEATURE",
        "description": "A derived metric/feature is missing but its authoritative source components exist.",
        "allowed_actions": ["RECOMPUTE_EXISTING_FEATURE", "REPROCESS_RECORD_USING_EXISTING_PIPELINE"],
        "requires_evidence": [EvidenceAuthority.SOURCE.value],
    },
    "DATA_QUALITY_MISSING_SOURCE_FIELD": {
        "layer": IssueLayer.DATA_QUALITY.value,
        "subtype": "MISSING_SOURCE_FIELD",
        "description": "Required source field (e.g. NPI, Member ID) missing with no authoritative source.",
        "allowed_actions": ["MANUAL_REVIEW"],
        "requires_evidence": [EvidenceAuthority.SOURCE.value],
    },
    "FEATURE_ENGINEERING_MISSING_DERIVED_FEATURE": {
        "layer": IssueLayer.FEATURE_ENGINEERING.value,
        "subtype": "MISSING_DERIVED_FEATURE",
        "description": "Engineered feature column missing in downstream artifact.",
        "allowed_actions": ["RECOMPUTE_EXISTING_FEATURE"],
        "requires_evidence": [EvidenceAuthority.SOURCE.value, EvidenceAuthority.BACKEND.value],
    },
    "FEATURE_ENGINEERING_DUPLICATE_RECORD": {
        "layer": IssueLayer.FEATURE_ENGINEERING.value,
        "subtype": "DUPLICATE_RECORD",
        "description": "Deterministic duplicate detected matching exact primary identity.",
        "allowed_actions": ["REMOVE_CONFIRMED_DUPLICATE", "MANUAL_REVIEW"],
        "requires_evidence": [EvidenceAuthority.SOURCE.value, EvidenceAuthority.VALIDATION.value],
    },
    "SERIALIZATION_MISSING_SLA_OUTPUT": {
        "layer": IssueLayer.FINAL_OUTPUT.value,
        "subtype": "RESULT_DROPPED_BEFORE_API",
        "description": "Authoritative SLA calculation exists in backend engine but is unpropagated to final output.",
        "allowed_actions": ["RESTORE_MISSING_SERIALIZED_RESULT", "REBUILD_FINAL_OUTPUT"],
        "requires_evidence": [EvidenceAuthority.BACKEND.value, EvidenceAuthority.VALIDATION.value],
    },
    "SERIALIZATION_MISSING_ANOMALY_RESULT": {
        "layer": IssueLayer.FINAL_OUTPUT.value,
        "subtype": "MISSING_ANOMALY_RESULT",
        "description": "Anomaly evaluation exists in backend ML artifacts but is missing in final serialized output.",
        "allowed_actions": ["RESTORE_MISSING_SERIALIZED_RESULT", "RERUN_EXISTING_ANOMALY_CALCULATION"],
        "requires_evidence": [EvidenceAuthority.BACKEND.value, EvidenceAuthority.VALIDATION.value],
    },
    "ANOMALY_DETECTION_STATISTICAL_FLAG": {
        "layer": IssueLayer.ANOMALY_DETECTION.value,
        "subtype": "STATISTICAL_ANOMALY_SIGNAL",
        "description": "Legitimate ML statistical outlier or Isolation Forest anomaly (Analytical detection, not a system error).",
        "allowed_actions": ["NO_ACTION", "MANUAL_REVIEW"],
        "requires_evidence": [EvidenceAuthority.BACKEND.value],
    },
    "CORRELATION_ANALYSIS_DISCREPANCY": {
        "layer": IssueLayer.CORRELATION_ANALYSIS.value,
        "subtype": "CORRELATION_BREAK_SIGNAL",
        "description": "Calculated regression residual exceeds 3.0 standard deviations.",
        "allowed_actions": ["NO_ACTION", "MANUAL_REVIEW"],
        "requires_evidence": [EvidenceAuthority.BACKEND.value],
    },
    "PIPELINE_INTEGRITY_STAGE_RECORD_DROP": {
        "layer": IssueLayer.PIPELINE_INTEGRITY.value,
        "subtype": "STAGE_RECORD_DROP",
        "description": "Record count discrepancy detected between pipeline stages.",
        "allowed_actions": ["REPROCESS_RECORD_USING_EXISTING_PIPELINE", "REBUILD_FINAL_OUTPUT", "MANUAL_REVIEW"],
        "requires_evidence": [EvidenceAuthority.VALIDATION.value],
    },
    "RAG_EVIDENCE_UNLINKED_CASE": {
        "layer": IssueLayer.RAG_RETRIEVAL.value,
        "subtype": "MISSING_KB_LINKAGE",
        "description": "Contextual historical case study retrieval unpopulated in analysis report.",
        "allowed_actions": ["RETRIGGER_EXISTING_RAG_RETRIEVAL", "REGENERATE_EXISTING_EVIDENCE"],
        "requires_evidence": [EvidenceAuthority.RAG.value],
    },
}


# Controlled Remediation Registry
REMEDIATION_REGISTRY: Dict[str, Dict[str, Any]] = {
    "RESTORE_MISSING_SERIALIZED_RESULT": {
        "action_id": "RESTORE_MISSING_SERIALIZED_RESULT",
        "name": "Restore Missing Serialized Result",
        "description": "Propagate authoritative backend engine calculation to the final persistent artifact.",
        "allowed_issue_types": ["SERIALIZATION", "FINAL_OUTPUT", "SLA", "ANOMALY_DETECTION"],
        "required_evidence": [EvidenceAuthority.BACKEND.value, EvidenceAuthority.VALIDATION.value],
        "preconditions": [
            "Authoritative backend result exists in stage artifact.",
            "Record_ID matches exactly between backend artifact and target.",
            "No conflicting authoritative source exists.",
        ],
        "risk_level": "LOW",
        "reversible": True,
    },
    "RECOMPUTE_EXISTING_FEATURE": {
        "action_id": "RECOMPUTE_EXISTING_FEATURE",
        "name": "Recompute Existing Derived Feature",
        "description": "Re-execute existing deterministic feature engineering transformation function using raw source inputs.",
        "allowed_issue_types": ["FEATURE_ENGINEERING", "DATA_QUALITY"],
        "required_evidence": [EvidenceAuthority.SOURCE.value],
        "preconditions": [
            "All prerequisite source input columns exist and are non-null.",
            "Transformation function is a pre-existing deterministic backend method.",
            "No fabricated or synthetic values are supplied.",
        ],
        "risk_level": "LOW",
        "reversible": True,
    },
    "REAPPLY_EXISTING_SCHEMA_MAPPING": {
        "action_id": "REAPPLY_EXISTING_SCHEMA_MAPPING",
        "name": "Reapply Existing Schema Mapping",
        "description": "Re-run schema normalization and column naming standardizer.",
        "allowed_issue_types": ["PREPROCESSING", "DATA_QUALITY"],
        "required_evidence": [EvidenceAuthority.SOURCE.value, EvidenceAuthority.VALIDATION.value],
        "preconditions": [
            "Source column corresponds deterministically to canonical schema specification.",
        ],
        "risk_level": "LOW",
        "reversible": True,
    },
    "REMOVE_CONFIRMED_DUPLICATE": {
        "action_id": "REMOVE_CONFIRMED_DUPLICATE",
        "name": "Remove Confirmed Exact Duplicate",
        "description": "Deduplicate identical claim/auth record where all primary key and payload fields match.",
        "allowed_issue_types": ["FEATURE_ENGINEERING", "DATA_QUALITY", "SOURCE_DATA"],
        "required_evidence": [EvidenceAuthority.SOURCE.value, EvidenceAuthority.VALIDATION.value],
        "preconditions": [
            "Deterministic duplicate rule matches exact Record_ID, Timestamp, and Payload.",
            "Authoritative retention policy clearly designates the master record.",
        ],
        "risk_level": "MEDIUM",
        "reversible": True,
    },
    "REPROCESS_RECORD_USING_EXISTING_PIPELINE": {
        "action_id": "REPROCESS_RECORD_USING_EXISTING_PIPELINE",
        "name": "Reprocess Record via Pipeline",
        "description": "Re-feed the valid source record through the standard feature, anomaly, and SLA pipeline.",
        "allowed_issue_types": ["PIPELINE_INTEGRITY", "ANOMALY_DETECTION", "SLA"],
        "required_evidence": [EvidenceAuthority.SOURCE.value],
        "preconditions": [
            "Source record is valid and complete.",
        ],
        "risk_level": "MEDIUM",
        "reversible": True,
    },
    "RERUN_EXISTING_ANOMALY_CALCULATION": {
        "action_id": "RERUN_EXISTING_ANOMALY_CALCULATION",
        "name": "Rerun Anomaly Calculation",
        "description": "Re-evaluate statistical and Isolation Forest scoring for the record using pre-fitted parameters.",
        "allowed_issue_types": ["ANOMALY_DETECTION"],
        "required_evidence": [EvidenceAuthority.BACKEND.value],
        "preconditions": [
            "Model parameters, thresholds, and contamination remain unchanged.",
        ],
        "risk_level": "LOW",
        "reversible": True,
    },
    "RERUN_EXISTING_SLA_CALCULATION": {
        "action_id": "RERUN_EXISTING_SLA_CALCULATION",
        "name": "Rerun SLA Calculation",
        "description": "Re-evaluate elapsed latency against statutory SLA target using the deterministic SLA engine.",
        "allowed_issue_types": ["SLA"],
        "required_evidence": [EvidenceAuthority.SOURCE.value, EvidenceAuthority.BACKEND.value],
        "preconditions": [
            "SLA rules, business policies, and threshold values remain unchanged.",
        ],
        "risk_level": "LOW",
        "reversible": True,
    },
    "RERUN_EXISTING_DATA_QUALITY_CHECK": {
        "action_id": "RERUN_EXISTING_DATA_QUALITY_CHECK",
        "name": "Rerun Data Quality Check",
        "description": "Re-validate dataset completeness, validity, consistency, and timeliness dimensions.",
        "allowed_issue_types": ["DATA_QUALITY"],
        "required_evidence": [EvidenceAuthority.VALIDATION.value],
        "preconditions": [
            "DQ validation rules remain unchanged.",
        ],
        "risk_level": "LOW",
        "reversible": True,
    },
    "REBUILD_FINAL_OUTPUT": {
        "action_id": "REBUILD_FINAL_OUTPUT",
        "name": "Rebuild Final Output Artifact",
        "description": "Re-synthesize the final monitoring output from verified intermediate stage outputs.",
        "allowed_issue_types": ["FINAL_OUTPUT", "PIPELINE_INTEGRITY"],
        "required_evidence": [EvidenceAuthority.BACKEND.value, EvidenceAuthority.VALIDATION.value],
        "preconditions": [
            "All intermediate stage artifacts exist and have passed integrity checks.",
        ],
        "risk_level": "MEDIUM",
        "reversible": True,
    },
    "REGENERATE_EXISTING_EVIDENCE": {
        "action_id": "REGENERATE_EXISTING_EVIDENCE",
        "name": "Regenerate Evidence Pack",
        "description": "Rebuild the multi-layer factual evidence bundle for the anomaly record.",
        "allowed_issue_types": ["EVIDENCE_BUILDER"],
        "required_evidence": [EvidenceAuthority.BACKEND.value],
        "preconditions": [
            "Underlying signals are unchanged.",
        ],
        "risk_level": "LOW",
        "reversible": True,
    },
    "RETRIGGER_EXISTING_RAG_RETRIEVAL": {
        "action_id": "RETRIGGER_EXISTING_RAG_RETRIEVAL",
        "name": "Retrigger RAG Knowledge Retrieval",
        "description": "Re-query ChromaDB vector store for relevant historical case patterns.",
        "allowed_issue_types": ["RAG_RETRIEVAL"],
        "required_evidence": [EvidenceAuthority.RAG.value],
        "preconditions": [
            "Vector database is active and available.",
        ],
        "risk_level": "LOW",
        "reversible": True,
    },
    "NO_ACTION": {
        "action_id": "NO_ACTION",
        "name": "No Action Required (Valid Analytical Signal)",
        "description": "Finding is an expected statistical detection or analytical flag rather than a system defect.",
        "allowed_issue_types": ["ANOMALY_DETECTION", "CORRELATION_ANALYSIS", "QUANTITY_SUPPLY_ANALYSIS"],
        "required_evidence": [EvidenceAuthority.BACKEND.value],
        "preconditions": [
            "Record was processed accurately according to approved models and rules.",
        ],
        "risk_level": "NONE",
        "reversible": True,
    },
    "MANUAL_REVIEW": {
        "action_id": "MANUAL_REVIEW",
        "name": "Escalate to Manual Review",
        "description": "Issue cannot be deterministically resolved automatically without guessing or fabricating data.",
        "allowed_issue_types": ["*"],
        "required_evidence": [],
        "preconditions": [],
        "risk_level": "NONE",
        "reversible": True,
    },
}
