"""
Service layer for handling analysis results and database operations.
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from uuid import uuid4
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from models import AnalysisRun, AnomalyResult
from schemas import AnomalyResultResponse, SeveritySummary
from services.pipeline_adapter import (
    get_severity_from_record,
    count_anomalies_by_severity,
    load_anomaly_report,
)

import logging

logger = logging.getLogger(__name__)


def generate_run_id() -> str:
    """Generate a unique run ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_suffix = str(uuid4())[:8]
    return f"RUN-{timestamp}-{random_suffix}"


def save_analysis_run(
    db: Session,
    filename: str,
    report_json_path: str,
    status: str = "completed",
    error_message: Optional[str] = None,
) -> AnalysisRun:
    """
    Save an analysis run and its results to the database.

    Args:
        db: Database session
        filename: Name of uploaded file
        report_json_path: Path to final_anomaly_report.json from pipeline
        status: Processing status
        error_message: If processing failed

    Returns:
        AnalysisRun object

    Raises:
        FileNotFoundError: If report JSON not found
        json.JSONDecodeError: If report JSON is invalid
    """
    run_id = generate_run_id()

    try:
        # Load the anomaly report
        report_data = load_anomaly_report(report_json_path)

        # Extract anomalies (handle both formats)
        if isinstance(report_data, dict):
            anomalies = report_data.get("anomalies", [])
        else:
            anomalies = report_data

        # Count records and severities
        total_records = len(anomalies)
        severity_counts = count_anomalies_by_severity(anomalies)

        # Create run record
        run = AnalysisRun(
            id=run_id,
            filename=filename,
            total_records=total_records,
            anomaly_count=total_records,  # All loaded records are anomalies
            high_count=severity_counts.get("HIGH", 0),
            medium_count=severity_counts.get("MEDIUM", 0),
            low_count=severity_counts.get("LOW", 0),
            processing_status=status,
            error_message=error_message,
        )

        db.add(run)
        db.commit()

        logger.info(f"[DB] Created analysis run: {run_id}")

        # Save individual anomaly results
        for idx, anomaly in enumerate(anomalies):
            try:
                severity = get_severity_from_record(anomaly)
                priority = anomaly.get("Priority", _map_severity_to_priority(severity))

                result = AnomalyResult(
                    run_id=run_id,
                    record_id=anomaly.get("Record ID", f"UNKNOWN-{idx}"),
                    record_type=anomaly.get("Type", "UNKNOWN"),
                    severity=severity,
                    priority=priority,
                    anomaly_type=anomaly.get("Anomaly", None),
                    primary_signal=anomaly.get("Primary Signal", None),
                    likely_root_cause=anomaly.get("Likely Root Cause", None),
                    recommended_action=anomaly.get("Recommended Action", None),
                    confidence=anomaly.get("_metadata", {}).get("confidence", 0.5)
                    if isinstance(anomaly.get("_metadata"), dict)
                    else 0.5,
                    impact=anomaly.get("_metadata", {}).get("impact", None)
                    if isinstance(anomaly.get("_metadata"), dict)
                    else None,
                    additional_checks=anomaly.get("_metadata", {}).get("additional_checks", None)
                    if isinstance(anomaly.get("_metadata"), dict)
                    else None,
                    full_record=anomaly,  # Store full record for power users
                )
                db.add(result)
            except Exception as e:
                logger.error(f"[DB] Failed to save anomaly {idx}: {e}")
                # Continue processing other anomalies
                continue

        db.commit()
        logger.info(f"[DB] Saved {total_records} anomaly results for run {run_id}")

        return run

    except Exception as e:
        logger.error(f"[DB] Failed to save analysis run: {e}")
        raise


def get_run_by_id(db: Session, run_id: str) -> Optional[AnalysisRun]:
    """Get a run by ID."""
    return db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()


def list_runs(
    db: Session, limit: int = 20, offset: int = 0
) -> Tuple[List[AnalysisRun], int]:
    """
    List recent analysis runs.

    Returns:
        Tuple of (list of runs, total count)
    """
    query = db.query(AnalysisRun).order_by(desc(AnalysisRun.created_at))
    total = query.count()
    runs = query.offset(offset).limit(limit).all()
    return runs, total


def get_anomalies_for_run(
    db: Session,
    run_id: str,
    severity: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    search_query: Optional[str] = None,
) -> Tuple[List[AnomalyResult], int]:
    """
    Get anomalies for a run with optional filtering.

    Args:
        db: Database session
        run_id: Analysis run ID
        severity: Optional filter (HIGH, MEDIUM, LOW)
        page: Page number (1-indexed)
        page_size: Results per page
        search_query: Optional search string (record_id, type, etc.)

    Returns:
        Tuple of (results list, total count)
    """
    query = db.query(AnomalyResult).filter(AnomalyResult.run_id == run_id)

    # Apply severity filter
    if severity and severity.upper() in ["HIGH", "MEDIUM", "LOW"]:
        query = query.filter(AnomalyResult.severity == severity.upper())

    # Apply search filter
    if search_query:
        search = f"%{search_query}%"
        query = query.filter(
            or_(
                AnomalyResult.record_id.ilike(search),
                AnomalyResult.record_type.ilike(search),
                AnomalyResult.anomaly_type.ilike(search),
            )
        )

    total = query.count()

    # Paginate
    offset = (page - 1) * page_size
    results = query.order_by(desc(AnomalyResult.created_at)).offset(offset).limit(page_size).all()

    return results, total


def get_anomaly_detail(db: Session, anomaly_id: int) -> Optional[AnomalyResult]:
    """Get a single anomaly by ID."""
    return db.query(AnomalyResult).filter(AnomalyResult.id == anomaly_id).first()


def get_run_statistics(db: Session, run_id: str) -> Dict[str, Any]:
    """
    Get statistics for a run.

    Returns:
        Dictionary with statistics
    """
    run = get_run_by_id(db, run_id)
    if not run:
        return {}

    results = db.query(AnomalyResult).filter(AnomalyResult.run_id == run_id).all()

    # Count by record type
    type_counts = {}
    for result in results:
        type_counts[result.record_type] = type_counts.get(result.record_type, 0) + 1

    # Count by anomaly type
    anomaly_counts = {}
    for result in results:
        if result.anomaly_type:
            anomaly_counts[result.anomaly_type] = (
                anomaly_counts.get(result.anomaly_type, 0) + 1
            )

    # Average confidence
    confidences = [r.confidence for r in results if r.confidence is not None]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    return {
        "total_records": run.total_records,
        "total_anomalies": run.anomaly_count,
        "by_severity": {
            "high": run.high_count,
            "medium": run.medium_count,
            "low": run.low_count,
        },
        "by_record_type": type_counts,
        "by_anomaly_type": anomaly_counts,
        "average_confidence": round(avg_confidence, 3),
    }


def _map_severity_to_priority(severity: str) -> str:
    """Map severity string to priority number."""
    mapping = {
        "HIGH": "2-High",
        "MEDIUM": "3-Medium",
        "LOW": "4-Low",
    }
    return mapping.get(severity.upper(), "3-Medium")
