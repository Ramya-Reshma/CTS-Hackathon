"""
Build RAG context by merging quality rules, correlation findings, and historical cases.
Used by the final synthesis pipeline to enrich evidence before LLM processing.
"""

import json
import os
from typing import Any, Dict, List, Optional


def load_quality_report(report_path: str = "log/quality_report.json") -> Dict[str, Any]:
    """Load data quality report with rule descriptions and fixes."""
    if not os.path.exists(report_path):
        return {"rules": []}
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_correlation_findings(report_path: str = "log/correlation_findings.json") -> Dict[str, Any]:
    """Load correlation analysis findings with relationship descriptions."""
    if not os.path.exists(report_path):
        return {"findings": []}
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_statistical_findings(report_path: str = "log/statistical_findings.json") -> Dict[str, Any]:
    """Load statistical analysis findings."""
    if not os.path.exists(report_path):
        return {"findings": []}
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"findings": []}


def extract_quality_rules_for_record(record: Dict[str, Any], quality_report: Dict[str, Any]) -> List[str]:
    """Extract relevant quality rules that apply to this record type.
    
    Returns a list of rule descriptions and recommended fixes.
    """
    record_type = record.get("Record_Type") or record.get("record_type") or ""
    rules_text = []
    
    if not quality_report.get("all_rule_results"):
        return rules_text
    
    for rule in quality_report.get("all_rule_results", []):
        if rule.get("status") != "PASSED" or rule.get("severity") == "Critical":
            description = rule.get("description", "")
            recommended_fix = rule.get("recommended_fix", "")
            rule_name = rule.get("rule_name", "")
            
            if description:
                rules_text.append(f"[DQ Rule] {rule_name}: {description}")
            if recommended_fix:
                rules_text.append(f"[Recommendation] {recommended_fix}")
    
    return rules_text


def extract_correlation_insights_for_record(record: Dict[str, Any], correlation_report: Dict[str, Any]) -> List[str]:
    """Extract relevant correlation analysis insights.
    
    Returns a list of relationship descriptions and anomaly explanations.
    """
    insights = []
    
    # Check if this record has correlation anomalies
    if record.get("Correlation_Anomaly") or record.get("correlation_anomaly"):
        residual = record.get("Correlation_Residual") or record.get("correlation_residual") or 0
        insights.append(f"[Correlation Anomaly] Record exhibits unexpected residual of {residual} from known relationship pattern.")
    
    # Check quantity-supply anomaly
    if record.get("Quantity_Supply_Anomaly") or record.get("quantity_supply_anomaly"):
        residual = record.get("Quantity_Supply_Residual") or record.get("quantity_supply_residual") or 0
        insights.append(f"[Quantity-Supply Anomaly] Quantity vs. Days Supply relationship shows residual of {residual}.")
    
    # Add findings from correlation report if available
    if correlation_report.get("findings"):
        for finding in correlation_report.get("findings", [])[:3]:  # Limit to top 3
            description = finding.get("description") or finding.get("insight") or ""
            if description:
                insights.append(f"[Relationship Analysis] {description}")
    
    return insights


def extract_statistical_context(record: Dict[str, Any], stat_report: Dict[str, Any]) -> List[str]:
    """Extract statistical analysis context for the record."""
    context = []
    
    # Check statistical anomalies
    if record.get("Stat_Zscore_Anomaly"):
        context.append("[Statistical] Z-score indicates deviation from expected distribution.")
    
    if record.get("Stat_IQR_Anomaly"):
        context.append("[Statistical] IQR test indicates value outside expected range.")
    
    # Add anomaly fields if present
    anomaly_fields = record.get("Stat_Anomaly_Fields", [])
    if anomaly_fields:
        fields_str = ", ".join(str(f) for f in anomaly_fields[:5])
        context.append(f"[Anomalous Fields] Detected in: {fields_str}")
    
    return context


def build_synthesis_rag_context(
    record: Dict[str, Any],
    quality_report: Dict[str, Any],
    correlation_report: Dict[str, Any],
    statistical_report: Dict[str, Any],
    historical_cases: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Build comprehensive RAG context for synthesis LLM.
    
    Merges evidence from all upstream modules (DQ, Correlation, Statistical, Historical).
    Returns a context dict with quality_insights, correlation_insights, statistical_context, and historical_cases.
    """
    
    quality_insights = extract_quality_rules_for_record(record, quality_report)
    correlation_insights = extract_correlation_insights_for_record(record, correlation_report)
    statistical_context = extract_statistical_context(record, statistical_report)
    
    context = {
        "record_id": record.get("Record_ID") or record.get("record_id"),
        "record_type": record.get("Record_Type") or record.get("record_type"),
        "severity_score": record.get("ISO_Severity_0to1") or record.get("severity_score") or 0.0,
        "ml_signal_count": record.get("ML_Anomaly_Signal_Count") or record.get("ml_signal_count") or 0,
        "quality_insights": quality_insights,
        "correlation_insights": correlation_insights,
        "statistical_context": statistical_context,
        "anomaly_flags": {
            "ml_anomalous": record.get("ML_Is_Anomalous", False),
            "iso_anomaly": record.get("ISO_Is_Anomaly", False),
            "correlation_anomaly": record.get("Correlation_Anomaly", False),
            "quantity_supply_anomaly": record.get("Quantity_Supply_Anomaly", False),
        },
        "historical_cases": historical_cases or [],
    }
    
    return context


def format_rag_context_for_prompt(rag_context: Dict[str, Any]) -> str:
    """Format RAG context into a readable prompt section."""
    
    lines = []
    lines.append(f"Record ID: {rag_context.get('record_id', 'N/A')}")
    lines.append(f"Record Type: {rag_context.get('record_type', 'N/A')}")
    lines.append(f"ML Severity Score (0-1): {rag_context.get('severity_score', 0.0):.3f}")
    lines.append(f"Anomaly Signal Count: {rag_context.get('ml_signal_count', 0)}")
    lines.append("")
    
    if rag_context.get("quality_insights"):
        lines.append("=== Data Quality Insights ===")
        for insight in rag_context["quality_insights"]:
            lines.append(f"  • {insight}")
        lines.append("")
    
    if rag_context.get("correlation_insights"):
        lines.append("=== Correlation Analysis ===")
        for insight in rag_context["correlation_insights"]:
            lines.append(f"  • {insight}")
        lines.append("")
    
    if rag_context.get("statistical_context"):
        lines.append("=== Statistical Analysis ===")
        for insight in rag_context["statistical_context"]:
            lines.append(f"  • {insight}")
        lines.append("")
    
    anomaly_flags = rag_context.get("anomaly_flags", {})
    if any(anomaly_flags.values()):
        lines.append("=== Anomaly Flags ===")
        if anomaly_flags.get("ml_anomalous"):
            lines.append("  • ML Model flagged as anomalous")
        if anomaly_flags.get("iso_anomaly"):
            lines.append("  • Isolation Forest detected anomaly")
        if anomaly_flags.get("correlation_anomaly"):
            lines.append("  • Relationship anomaly detected")
        if anomaly_flags.get("quantity_supply_anomaly"):
            lines.append("  • Quantity-Supply relationship anomaly")
        lines.append("")
    
    if rag_context.get("historical_cases"):
        lines.append("=== Similar Historical Cases ===")
        for i, case in enumerate(rag_context["historical_cases"][:3], 1):
            root_cause = case.get("root_cause") or case.get("likely_root_cause") or "Unresolved"
            resolution = case.get("resolution") or case.get("resolution_used") or "N/A"
            lines.append(f"  Case {i}: {root_cause}")
            lines.append(f"    Resolution: {resolution}")
        lines.append("")
    
    return "\n".join(lines)
