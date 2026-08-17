"""
Reformat final_anomaly_synthesis_report.json with anomaly type classification.

Restructures the report to include:
- Priority (derived from severity)
- Record ID
- Type (record type)
- Anomaly (classification)
- Severity
- Primary Signal
- Likely Root Cause
- Recommended Action
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path


class AnomalyClassifier:
    """Classify anomalies by type based on evidence and root cause."""
    
    # Anomaly type keywords mapping
    ANOMALY_TYPES = {
        "Provider": ["provider", "npi", "practitioner", "specialty", "credentialing", "panel"],
        "Financial": ["amount", "billed", "paid", "allowed", "zero-pay", "reimburse", "cost"],
        "Timing": ["date", "submission", "processing", "service_date", "delay"],
        "Quantity": ["quantity", "days_supply", "dose", "volume", "dispense"],
        "Relationship": ["correlation", "residual", "relationship", "pattern"],
        "Quality": ["missing", "invalid", "format", "completeness", "validity", "consistency"],
        "Frequency": ["high", "low", "outlier", "anomalous", "deviation", "zscore", "outlier"],
        "Authorization": ["auth", "approval", "authorization", "denial", "reject"],
    }
    
    @classmethod
    def classify(cls, record: Dict[str, Any]) -> str:
        """Classify anomaly type based on available evidence."""
        
        # Check historical cases first
        if "rag_context" in record and record["rag_context"].get("historical_cases"):
            for case in record["rag_context"]["historical_cases"]:
                anomaly_name = case.get("anomaly_name") or case.get("anomaly") or ""
                if anomaly_name:
                    # Extract type from anomaly name or root cause
                    for anomaly_type, keywords in cls.ANOMALY_TYPES.items():
                        if any(kw in anomaly_name.lower() for kw in keywords):
                            return anomaly_type
                
                # Check root cause
                root_cause = case.get("root_cause") or ""
                for anomaly_type, keywords in cls.ANOMALY_TYPES.items():
                    if any(kw in root_cause.lower() for kw in keywords):
                        return anomaly_type
        
        # Check root cause from main record
        root_cause = (record.get("likely_root_cause") or "").lower()
        for anomaly_type, keywords in cls.ANOMALY_TYPES.items():
            if any(kw in root_cause for kw in keywords):
                return anomaly_type
        
        # Check anomaly signals
        signals = record.get("anomaly_signals") or {}
        for signal_name in signals.keys():
            signal_name_lower = signal_name.lower()
            for anomaly_type, keywords in cls.ANOMALY_TYPES.items():
                if any(kw in signal_name_lower for kw in keywords):
                    return anomaly_type
        
        # Check observed facts
        for fact in record.get("observed_facts", []):
            fact_lower = str(fact).lower()
            for anomaly_type, keywords in cls.ANOMALY_TYPES.items():
                if any(kw in fact_lower for kw in keywords):
                    return anomaly_type
        
        # Default to Frequency if multiple signals detected
        signal_count = record.get("rag_context", {}).get("ml_signal_count", 0)
        if signal_count > 1:
            return "Frequency"
        
        return "Other"
    
    @classmethod
    def extract_primary_signal(cls, record: Dict[str, Any]) -> str:
        """Extract the primary anomaly signal."""
        
        # Check historical cases
        if "rag_context" in record and record["rag_context"].get("historical_cases"):
            for case in record["rag_context"]["historical_cases"]:
                anomaly_name = case.get("anomaly_name") or case.get("anomaly") or ""
                if anomaly_name:
                    return anomaly_name
        
        # Check anomaly signals
        signals = record.get("anomaly_signals") or {}
        if signals:
            for signal_name, signal_value in signals.items():
                if signal_value or isinstance(signal_value, bool):
                    return signal_name
        
        # Check observation facts
        if record.get("observed_facts"):
            return record["observed_facts"][0]
        
        # Fallback to record type + severity
        return f"{record.get('record_type')} anomaly detected"


def severity_to_priority(severity: str) -> str:
    """Convert severity to priority level."""
    severity_lower = (severity or "").lower()
    if severity_lower in ["high", "critical", "severe"]:
        return "1-Critical"
    elif severity_lower == "medium":
        return "2-High"
    elif severity_lower == "low":
        return "3-Medium"
    else:
        return "4-Low"


def extract_first_recommended_action(record: Dict[str, Any]) -> str:
    """Extract the first recommended action or a summary."""
    
    actions = record.get("recommended_actions") or []
    if actions:
        return actions[0]
    
    # Check historical cases
    if "rag_context" in record and record["rag_context"].get("historical_cases"):
        for case in record["rag_context"]["historical_cases"]:
            case_actions = case.get("recommended_actions") or []
            if case_actions:
                return case_actions[0]
    
    return "Review evidence and implement corrective action"


def reformat_synthesis_report(
    input_path: str = "log/final_anomaly_synthesis_report.json",
    output_path: str = "log/final_anomaly_synthesis_report.json"
) -> Dict[str, Any]:
    """Reformat synthesis report with anomaly classification."""
    
    print(f"Loading synthesis report from {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    reports = data.get("anomaly_reports", [])
    print(f"Found {len(reports)} anomaly reports to reformat")
    
    # Create reformatted records
    reformatted = []
    
    for idx, record in enumerate(reports, 1):
        # Classify anomaly type
        anomaly_type = AnomalyClassifier.classify(record)
        primary_signal = AnomalyClassifier.extract_primary_signal(record)
        priority = severity_to_priority(record.get("severity"))
        recommended_action = extract_first_recommended_action(record)
        
        reformatted_record = {
            "Priority": priority,
            "Record ID": record.get("incident_id") or record.get("record_id") or f"REC-{idx}",
            "Type": record.get("record_type") or "CLAIM",
            "Anomaly": anomaly_type,
            "Severity": record.get("severity") or "MEDIUM",
            "Primary Signal": primary_signal,
            "Likely Root Cause": record.get("likely_root_cause") or "Unknown",
            "Recommended Action": recommended_action,
            # Additional metadata for reference
            "_metadata": {
                "confidence": record.get("confidence", 0.0),
                "impact": record.get("impact") or "Not specified",
                "additional_checks": record.get("additional_checks_required", []),
                "processed_at": record.get("synthesis_metadata", {}).get("processed_at"),
            }
        }
        
        reformatted.append(reformatted_record)
    
    # Create output structure
    output_data = {
        "report_metadata": {
            "generated_at": data.get("synthesis_report", {}).get("generated_at"),
            "total_anomalies": len(reformatted),
            "by_severity": data.get("synthesis_report", {}).get("by_severity", {}),
            "format": "Flat anomaly report with Priority, Record ID, Type, Anomaly, Severity, Primary Signal, Likely Root Cause, Recommended Action",
        },
        "anomalies": reformatted,
    }
    
    # Sort by priority (1-Critical first)
    output_data["anomalies"].sort(key=lambda x: (x["Priority"], x["Record ID"]))
    
    # Save output
    print(f"Saving reformatted report to {output_path}...")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Reformatted {len(reformatted)} anomaly records")
    print("\nSample output (first 3 records):")
    for rec in reformatted[:3]:
        print(f"  {rec['Record ID']:12s} | {rec['Priority']:12s} | {rec['Type']:12s} | {rec['Anomaly']:12s} | {rec['Severity']:8s}")
    
    return output_data


if __name__ == "__main__":
    try:
        result = reformat_synthesis_report()
        total = result["report_metadata"]["total_anomalies"]
        print(f"\n[SUCCESS] Report reformatted successfully with {total} records")
    except FileNotFoundError as e:
        print(f"[ERROR] Input file not found: {e}")
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
