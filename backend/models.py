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


class User(Base):
    """
    User model for MEDLYTICS authentication and access control.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    approval_status = Column(String(50), default="PENDING_EMAIL_VERIFICATION", nullable=False)
    # Statuses: PENDING_EMAIL_VERIFICATION, PENDING_APPROVAL, APPROVED, REJECTED, DISABLED
    role = Column(String(50), default="USER", nullable=False)  # USER, ADMIN
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tokens = relationship("VerificationToken", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "email_verified": self.email_verified,
            "approval_status": self.approval_status,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class VerificationToken(Base):
    """
    Verification token model for email verification and password resets.
    """
    __tablename__ = "verification_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(128), unique=True, nullable=False, index=True)
    token_type = Column(String(50), default="EMAIL_VERIFICATION", nullable=False)  # EMAIL_VERIFICATION, PASSWORD_RESET
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="tokens")



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
    observed_facts = Column(JSON, nullable=True)  # RCA observed facts
    possible_causes = Column(JSON, nullable=True)  # RCA hypotheses
    evidence = Column(JSON, nullable=True)  # RCA evidence list
    anomaly_signals = Column(JSON, nullable=True)  # RCA anomaly signals dictionary

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
            "observed_facts": self.observed_facts,
            "possible_causes": self.possible_causes,
            "evidence": self.evidence,
            "anomaly_signals": self.anomaly_signals,
            "created_at": self.created_at.isoformat(),
        }

    def to_detail_dict(self):
        """Return full detail including technical fields."""
        result = self.to_dict()
        if self.full_record:
            result["full_record"] = self.full_record
        return result


class AutoResolutionAudit(Base):
    """
    Audit log for all automatic and manual resolution actions.
    Ensures complete traceability, before/after diffs, and verification proof.
    """
    __tablename__ = "auto_resolution_audit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fix_id = Column(String(64), unique=True, nullable=False, index=True)
    run_id = Column(String(64), nullable=False, index=True)
    record_id = Column(String(100), nullable=False, index=True)
    issue_id = Column(String(100), nullable=False)
    issue_type = Column(String(100), nullable=False)
    layer = Column(String(100), nullable=False)
    action_id = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)  # AUTO_FIXED, FIX_FAILED_ROLLED_BACK, MANUAL_REVIEW_REQUIRED, NO_ACTION_REQUIRED
    validation_status = Column(String(50), nullable=False)  # PASS, FAIL, SKIPPED
    evidence = Column(JSON, nullable=True)
    root_cause = Column(Text, nullable=True)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    validation_details = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    executed_by = Column(String(120), default="Auto-Resolution Agent", nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "fix_id": self.fix_id,
            "run_id": self.run_id,
            "record_id": self.record_id,
            "issue_id": self.issue_id,
            "issue_type": self.issue_type,
            "layer": self.layer,
            "action_id": self.action_id,
            "status": self.status,
            "validation_status": self.validation_status,
            "evidence": self.evidence,
            "root_cause": self.root_cause,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "validation_details": self.validation_details,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "executed_by": self.executed_by,
        }

