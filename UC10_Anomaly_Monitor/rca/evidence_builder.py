import json
from UC10_Anomaly_Monitor.rca import tools
from UC10_Anomaly_Monitor.config import settings
from typing import Dict, Any


def build_evidence(record_id: str, report_path: str = None) -> Dict[str, Any]:
    """Build a compact JSON evidence package for the given record id.

    The package is intentionally small (only key numeric fields and signals).
    """
    rec = tools.get_record_details(record_id, path=report_path)

    evidence = {
        "record_id": rec.get("Record_ID"),
        "record_type": rec.get("Record_Type"),
        "beneficiary_id": rec.get("BENE_ID"),
        "provider_npi": rec.get("Provider_NPI"),
        "financials": {
            "billed": rec.get("Billed_Amount"),
            "paid": rec.get("Paid_Amount"),
            "allowed": rec.get("Allowed_Amount")
        },
        "supply": {
            "quantity": rec.get("Quantity_Dispensed"),
            "days_supply": rec.get("Days_Supply")
        },
        "statistical": {
            "zscore": rec.get("Stat_Zscore_Anomaly", False),
            "iqr": rec.get("Stat_IQR_Anomaly", False),
            "zscore_fields": rec.get("Stat_Anomaly_Fields", [])
        },
        "isolation_forest": {
            "is_anomaly": rec.get("ISO_Is_Anomaly", False),
            "raw_score": rec.get("ISO_Raw_Score"),
            "severity_0to1": rec.get("ISO_Severity_0to1")
        },
        "correlation": {
            "anomaly": rec.get("Correlation_Anomaly", False),
            "residual": rec.get("Correlation_Residual", None),
            "quantity_supply_anomaly": rec.get("Quantity_Supply_Anomaly", False),
            "quantity_supply_residual": rec.get("Quantity_Supply_Residual", None)
        },
        "data_quality": rec.get("Data_Quality_Rule_Failures", []),
        "ml_signal_count": rec.get("ML_Anomaly_Signal_Count", 0),
    }

    # Keep package compact: prune None values and keep lists short
    def prune(obj):
        if isinstance(obj, dict):
            return {k: prune(v) for k, v in obj.items() if v is not None and v != []}
        if isinstance(obj, list):
            return obj[:10]
        return obj

    compact = prune(evidence)
    # Add a short provenance header
    package = {
        "source": "final_anomaly_report.json",
        "record_id": record_id,
        "evidence": compact
    }

    return package
