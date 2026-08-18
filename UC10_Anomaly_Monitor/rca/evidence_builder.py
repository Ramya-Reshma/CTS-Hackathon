import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from UC10_Anomaly_Monitor.config import settings


def _find_report_path(report_path: Optional[str] = None) -> Path:
    """Resolve report path from parameter, settings, or default fallback locations."""
    if report_path:
        p = Path(report_path)
        if p.exists():
            return p

    if hasattr(settings, "JSON_REPORT_PATH") and settings.JSON_REPORT_PATH:
        p = Path(settings.JSON_REPORT_PATH)
        if p.exists():
            return p

    base_dir = Path(__file__).resolve().parents[2]
    candidates = [
        base_dir / "log" / "final_anomaly_report.json",
        base_dir / "Data" / "final_anomaly_report.json",
        Path("log/final_anomaly_report.json"),
    ]
    for cand in candidates:
        if cand.exists():
            return cand

    raise FileNotFoundError("final_anomaly_report.json not found in expected paths.")


def _load_report(path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load the JSON anomaly report."""
    p = _find_report_path(path)
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "records" in data and isinstance(data["records"], list):
            return data["records"]
        return [data]
    return []


def get_record_details(record_id: str, path: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve raw record from final_anomaly_report.json matching record_id."""
    report = _load_report(path)
    target_id = str(record_id).strip().upper()
    for rec in report:
        rec_id = str(rec.get("Record_ID", "")).strip().upper()
        if rec_id == target_id:
            return rec
    raise KeyError(f"Record ID {record_id} not found in final_anomaly_report.json.")


def build_evidence(record_id: str, report_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Build a compact JSON evidence package for the given record_id.
    
    Extracts ONLY the relevant fields from final_anomaly_report.json
    without passing the entire dataset or performing RCA.
    """
    rec = get_record_details(record_id, path=report_path)

    # Safe conversion helpers to preserve original values without modifying them
    def _bool_or_none(val, default=False):
        if val is None:
            return default
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        return default

    def _clean_str(val):
        if val is None or str(val).lower() in ("nan", "none", "null", ""):
            return None
        return str(val).strip()

    # Statistical flags & fields
    stat_zscore = _bool_or_none(rec.get("Stat_Zscore_Anomaly"), False)
    stat_iqr = _bool_or_none(rec.get("Stat_IQR_Anomaly"), False)
    stat_fields_raw = rec.get("Stat_Anomaly_Fields")
    if isinstance(stat_fields_raw, list):
        affected_fields = [str(x) for x in stat_fields_raw if x and str(x).lower() != "none"]
    elif isinstance(stat_fields_raw, str) and stat_fields_raw.strip() and stat_fields_raw.lower() not in ("none", "nan", "[]"):
        affected_fields = [stat_fields_raw.strip()]
    else:
        affected_fields = []

    # Isolation Forest
    iso_is_anomaly = _bool_or_none(rec.get("ISO_Is_Anomaly"), False)
    iso_raw_score = rec.get("ISO_Raw_Score")
    iso_severity = rec.get("ISO_Severity_0to1")

    # Correlation
    corr_anomaly = _bool_or_none(rec.get("Correlation_Anomaly"), False)
    corr_residual = rec.get("Correlation_Residual")
    qs_anomaly = _bool_or_none(rec.get("Quantity_Supply_Anomaly"), False)
    qs_residual = rec.get("Quantity_Supply_Residual")

    # ML Signal count
    ml_signal_count = rec.get("ML_Anomaly_Signal_Count")
    if ml_signal_count is None:
        ml_signal_count = sum([1 for flag in [iso_is_anomaly, corr_anomaly, qs_anomaly] if flag])

    # Construct the exact required compact evidence package
    evidence = {
        "record_id": rec.get("Record_ID", record_id),
        "record_type": rec.get("Record_Type"),
        "beneficiary": {
            "beneficiary_id": _clean_str(rec.get("BENE_ID"))
        },
        "provider": {
            "provider_npi": _clean_str(rec.get("Provider_NPI"))
        },
        "financials": {
            "billed": rec.get("Billed_Amount"),
            "paid": rec.get("Paid_Amount"),
            "allowed": rec.get("Allowed_Amount")
        },
        "supply": {
            "quantity_dispensed": rec.get("Quantity_Dispensed"),
            "days_supply": rec.get("Days_Supply")
        },
        "statistical": {
            "zscore_anomaly": stat_zscore,
            "iqr_anomaly": stat_iqr,
            "affected_fields": affected_fields
        },
        "isolation_forest": {
            "is_anomaly": iso_is_anomaly,
            "raw_score": iso_raw_score,
            "severity_0to1": iso_severity
        },
        "correlation": {
            "anomaly": corr_anomaly,
            "residual": corr_residual,
            "quantity_supply_anomaly": qs_anomaly,
            "quantity_supply_residual": qs_residual
        },
        "data_quality": rec.get("Data_Quality_Rule_Failures", []) if isinstance(rec.get("Data_Quality_Rule_Failures"), list) else [],
        "ml_signal_count": ml_signal_count
    }

    # Pass additional contextual fields if present in source (e.g. status, denial_reason, codes)
    if rec.get("Status"):
        evidence["status"] = rec.get("Status")
    if rec.get("Denial_Reason_Code"):
        evidence["denial_reason_code"] = rec.get("Denial_Reason_Code")
    if rec.get("Diagnosis_Code"):
        evidence["diagnosis_code"] = rec.get("Diagnosis_Code")
    if rec.get("Procedure_Code"):
        evidence["procedure_code"] = rec.get("Procedure_Code")
    if rec.get("Drug_Name"):
        evidence["drug_name"] = rec.get("Drug_Name")
    if rec.get("NDC_Code"):
        evidence["ndc_code"] = rec.get("NDC_Code")
    if rec.get("Processing_Latency_Days") is not None:
        evidence["processing_latency_days"] = rec.get("Processing_Latency_Days")
    if rec.get("Provider_State"):
        evidence["provider_state"] = rec.get("Provider_State")
    if rec.get("Auth_Required_Flag") is not None:
        evidence["auth_required_flag"] = rec.get("Auth_Required_Flag")
    if rec.get("Missing_Required_Auth_Link") is not None:
        evidence["missing_required_auth_link"] = rec.get("Missing_Required_Auth_Link")
    if rec.get("anomaly_type"):
        evidence["anomaly_type"] = rec.get("anomaly_type")
    if rec.get("primary_signal"):
        evidence["primary_signal"] = rec.get("primary_signal")

    return evidence
