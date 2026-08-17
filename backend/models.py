"""
Database models for storing analysis runs and anomaly results.

SQLite tables:
- analysis_runs: Metadata about each analysis run
- anomaly_results: Individual anomaly records
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Float, Boolean, ForeignKey, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class AnalysisRun(Base):
    """
    Metadata about an analysis run.

    Stores minimal run information - does NOT store raw input claims.
    """
    __tablename__ = "analysis_runs"

    id = Column(String(64), primary_key=True)  # e.g., RUN-20260816-001
    filename = Column(String(256), nullable=False)  # Name of uploaded file
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    total_records = Column(Integer, nullable=False, default=0)  # Records in input file
    anomaly_count = Column(Integer, nullable=False, default=0)  # Total anomalies detected
    high_count = Column(Integer, nullable=False, default=0)
    medium_count = Column(Integer, nullable=False, default=0)
    low_count = Column(Integer, nullable=False, default=0)
    processing_status = Column(String(50), nullable=False, default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)  # If processing failed
    pipeline_version = Column(String(50), nullable=False, default="1.0")

    # Relationship
    anomalies = relationship("AnomalyResult", back_populates="run", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "created_at": self.created_at.isoformat(),
            "total_records": self.total_records,
            "anomaly_count": self.anomaly_count,
            "severity_summary": {
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
            },
            "processing_status": self.processing_status,
            "error_message": self.error_message,
        }


class AnomalyResult(Base):
    """
    Individual anomaly record from pipeline output.

    Stores the final anomaly results (not raw claims data).
    Maps to the synthesis report format for display.
    """
    __tablename__ = "anomaly_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("analysis_runs.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Core fields from synthesis report
    record_id = Column(String(100), nullable=False)  # e.g., PH201432, MC100034
    record_type = Column(String(50), nullable=False)  # PHARMACY_CLAIM, MEDICAL_CLAIM, PRIOR_AUTH
    severity = Column(String(20), nullable=False)  # HIGH, MEDIUM, LOW
    priority = Column(String(20), nullable=False)  # 1-Critical, 2-High, 3-Medium, 4-Low
    anomaly_type = Column(String(100), nullable=True)  # Provider, Financial, Timing, etc.

    # Display fields
    primary_signal = Column(Text, nullable=True)  # What triggered the anomaly
    likely_root_cause = Column(Text, nullable=True)  # Why it happened
    recommended_action = Column(Text, nullable=True)  # How to fix it

    # Technical fields (from pipeline)
    confidence = Column(Float, nullable=True, default=0.5)  # 0.0 - 1.0
    impact = Column(Text, nullable=True)  # Business impact description
    additional_checks = Column(Text, nullable=True)  # Recommended further checks

    # Full anomaly record (JSON) for advanced users
    full_record = Column(JSON, nullable=True)  # Complete original anomaly from pipeline

    # Relationship
    run = relationship("AnalysisRun", back_populates="anomalies")

    def to_dict(self):
        return {
            "id": self.id,
            "record_id": self.record_id,
            "record_type": self.record_type,
            "severity": self.severity,
            "priority": self.priority,
            "anomaly_type": self.anomaly_type,
            "primary_signal": self.primary_signal,
            "likely_root_cause": self.likely_root_cause,
            "recommended_action": self.recommended_action,
            "confidence": self.confidence,
            "impact": self.impact,
            "additional_checks": self.additional_checks,
            "created_at": self.created_at.isoformat(),
        }

    def to_detail_dict(self):
        """Return full detail including technical fields."""
        result = self.to_dict()
        if self.full_record:
            result["full_record"] = self.full_record
        return result
