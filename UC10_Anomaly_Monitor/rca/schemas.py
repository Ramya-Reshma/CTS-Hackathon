from pydantic import BaseModel, Field
from typing import List, Optional


class RCAOutput(BaseModel):
    incident_id: str = Field(...)
    record_type: str
    severity: str
    summary: str
    anomaly_signals: dict
    evidence: List[str]
    observed_facts: List[str]
    possible_causes: List[str]
    likely_root_cause: str
    confidence: float
    impact: Optional[str]
    recommended_actions: List[str]
    additional_checks_required: List[str]
