"""
Pydantic schemas for API request/response validation.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ============================================================================
# Analysis Run Schemas
# ============================================================================

class AnomalyResultBase(BaseModel):
    """Base fields for anomaly result."""
    record_id: str
    record_type: str
    severity: str  # HIGH, MEDIUM, LOW
    priority: str  # 1-Critical, 2-High, 3-Medium, 4-Low
    anomaly_type: Optional[str] = None
    primary_signal: Optional[str] = None
    likely_root_cause: Optional[str] = None
    recommended_action: Optional[str] = None
    confidence: Optional[float] = 0.5
    impact: Optional[str] = None
    additional_checks: Optional[str] = None
    observed_facts: Optional[List[str]] = None
    possible_causes: Optional[List[str]] = None
    evidence: Optional[List[str]] = None
    anomaly_signals: Optional[Dict[str, Any]] = None
    full_record: Optional[Dict[str, Any]] = None


class AnomalyResultResponse(AnomalyResultBase):
    """Response schema for anomaly result."""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AnomalyResultDetail(AnomalyResultResponse):
    """Detailed anomaly response with full record."""
    full_record: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class SeveritySummary(BaseModel):
    """Summary counts by severity."""
    high: int
    medium: int
    low: int


class AnalysisRunBase(BaseModel):
    """Base fields for analysis run."""
    filename: str
    dataset_id: Optional[str] = None
    total_records: int = 0
    anomaly_count: int = 0


class AnalysisRunResponse(AnalysisRunBase):
    """Response schema for analysis run."""
    id: str
    dataset_id: Optional[str] = None
    created_at: datetime
    processing_status: str
    severity_summary: SeveritySummary
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class DatasetResponse(BaseModel):
    """Response schema for an uploaded dataset."""
    dataset_id: str
    filename: str
    row_count: int
    file_size_bytes: int
    status: str
    schema_info: Optional[List[str]] = None
    created_at: Optional[str] = None


# ============================================================================
# API Endpoint Schemas
# ============================================================================

class AnalyzeRequest(BaseModel):
    """Request for file analysis."""
    # File will be sent as multipart/form-data, not JSON
    pass


class AnalyzeResponse(BaseModel):
    """Response after analysis starts/completes."""
    run_id: str
    dataset_id: Optional[str] = None
    status: str  # pending, processing, completed, failed
    filename: str
    total_records: int
    total_anomalies: int
    severity_summary: SeveritySummary
    message: Optional[str] = None


class AnomaliesListResponse(BaseModel):
    """Response for listing anomalies."""
    run_id: str
    total: int
    page: int
    page_size: int
    severity_filter: Optional[str] = None
    records: List[AnomalyResultResponse]


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    message: str = "UC10 Anomaly Monitor API is running"


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    message: str
    detail: Optional[str] = None


class AnomalySearchRequest(BaseModel):
    """Request for searching anomalies."""
    query: str  # Search by record_id, npi, bene_id, etc.
    severity: Optional[str] = None


# ============================================================================
# Statistics Schemas
# ============================================================================

class AnomalyDistribution(BaseModel):
    """Distribution of anomalies by type/severity."""
    name: str
    value: int


class RunStatistics(BaseModel):
    """Statistics for a run."""
    total_records: int
    total_anomalies: int
    by_severity: SeveritySummary
    by_record_type: Optional[Dict[str, int]] = None
    by_anomaly_type: Optional[Dict[str, int]] = None
    average_confidence: Optional[float] = None
    overall_data_quality_score: Optional[float] = None
    overall_risk_level: Optional[str] = None
    dimension_scores: Optional[Dict[str, float]] = None
    all_rule_results: Optional[List[Dict[str, Any]]] = None
    top_failed_rules: Optional[List[Dict[str, Any]]] = None
    critical_issue_count: Optional[int] = None
    processing_integrity: Optional[Dict[str, Any]] = None
    sla_summary: Optional[Dict[str, Any]] = None
