from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict


class RCAAnalysis(BaseModel):
    """
    Standardized Root Cause Analysis schema for healthcare claims anomalies.
    """
    priority: str = Field(..., description="Priority level: CRITICAL, HIGH, MEDIUM, or LOW derived from severity and signal strength")
    record_id: str = Field(..., description="Unique identifier for the analyzed record")
    anomaly_type: str = Field(..., description="Category of anomaly detected (e.g., Pharmacy Claim Anomaly, Correlation Anomaly)")
    root_cause: str = Field(..., description="Explanation of WHY the anomaly detection system flagged the record (detectors, scores, residuals)")
    observed_facts: List[str] = Field(default_factory=list, description="Factual statements strictly traceable to the supplied evidence")
    possible_causes: List[str] = Field(default_factory=list, description="Hypotheses supported by evidence and retrieved RAG knowledge")
    likely_root_cause: str = Field(..., description="Most defensible explanation supported by evidence and RAG knowledge, or 'Insufficient evidence to determine root cause.'")
    recommended_actions: List[str] = Field(default_factory=list, description="Practical, actionable operational steps directly connected to the anomaly")


class BatchRCAAnalysis(BaseModel):
    """Container for multiple RCA analyses in a batch run."""
    analyses: List[RCAAnalysis] = Field(default_factory=list)


# Backward compatibility schema
class RCAOutput(BaseModel):
    incident_id: Optional[str] = None
    record_id: Optional[str] = None
    record_type: Optional[str] = "CLAIM"
    priority: Optional[str] = "MEDIUM"
    severity: Optional[str] = "MEDIUM"
    summary: Optional[str] = ""
    anomaly_type: Optional[str] = "Multivariate Anomaly"
    anomaly_signals: Optional[Dict[str, Any]] = Field(default_factory=dict)
    evidence: Optional[List[str]] = Field(default_factory=list)
    root_cause: Optional[str] = ""
    observed_facts: List[str] = Field(default_factory=list)
    possible_causes: List[str] = Field(default_factory=list)
    likely_root_cause: str = "Insufficient evidence to determine root cause."
    confidence: Optional[float] = 0.5
    impact: Optional[str] = None
    recommended_actions: List[str] = Field(default_factory=list)
    additional_checks_required: Optional[List[str]] = Field(default_factory=list)

    def to_rca_analysis(self) -> RCAAnalysis:
        rec_id = self.record_id or self.incident_id or "UNKNOWN"
        prio = self.priority or self.severity or "MEDIUM"
        return RCAAnalysis(
            priority=prio.upper(),
            record_id=rec_id,
            anomaly_type=self.anomaly_type or self.record_type or "Multivariate Anomaly",
            root_cause=self.root_cause or self.summary or "Record flagged by anomaly detection models.",
            observed_facts=self.observed_facts or self.evidence or [],
            possible_causes=self.possible_causes or [],
            likely_root_cause=self.likely_root_cause or "Insufficient evidence to determine root cause.",
            recommended_actions=self.recommended_actions or []
        )
