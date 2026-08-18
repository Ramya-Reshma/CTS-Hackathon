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


def _coalesce(record: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    """Return the first non-empty value among candidate keys."""
    for key in keys:
        value = record.get(key)
        if value is not None and value != "":
            return value
    return default


def _normalize_record_id(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().upper()


def _load_synthesis_lookup(report_json_path: str) -> Dict[str, Dict[str, Any]]:
    """Load the synthesis report keyed by normalized record ID if available."""
    report_dir = Path(report_json_path).resolve().parent
    synthesis_path = report_dir / "final_anomaly_synthesis_report.json"
    if not synthesis_path.exists():
        return {}

    try:
        payload = json.loads(synthesis_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"[DB] Failed to load synthesis report: {e}")
        return {}

    records = payload.get("anomalies", []) if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        return {}

    lookup: Dict[str, Dict[str, Any]] = {}
    for item in records:
        if not isinstance(item, dict):
            continue
        record_id = _coalesce(item, ["Record ID", "Record_ID", "record_id", "incident_id"])
        if record_id is None:
            continue
        lookup[_normalize_record_id(record_id)] = item

    return lookup


def _load_quality_summary(report_json_path: str) -> Dict[str, Any]:
    """Load data-quality summary from the sibling quality report if it exists."""
    report_dir = Path(report_json_path).resolve().parent
    quality_path = report_dir / "quality_report.json"
    if not quality_path.exists():
        return {}

    try:
        payload = json.loads(quality_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {}
        return payload
    except Exception as e:
        logger.warning(f"[DB] Failed to load quality report: {e}")
        return {}


def _load_sla_summary(report_json_path: str) -> Dict[str, Any]:
    """Load population SLA summary from the sibling sla_temporal_findings.json if it exists."""
    report_dir = Path(report_json_path).resolve().parent
    sla_path = report_dir / "sla_temporal_findings.json"
    if not sla_path.exists():
        return {}

    try:
        payload = json.loads(sla_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {}
        return payload.get("summary", {})
    except Exception as e:
        logger.warning(f"[DB] Failed to load SLA summary: {e}")
        return {}


def _calculate_confidence(record: Dict[str, Any], fallback: float = 0.5) -> float:
    """Calculate a confidence score from the anomaly signal profile."""
    if isinstance(record.get("_metadata"), dict):
        metadata_confidence = record["_metadata"].get("confidence")
        if metadata_confidence is not None:
            try:
                return float(metadata_confidence)
            except (TypeError, ValueError):
                pass

    if "confidence" in record:
        try:
            return float(record["confidence"])
        except (TypeError, ValueError):
            pass

    try:
        signal_count = int(record.get("ML_Anomaly_Signal_Count", 0) or 0)
    except (TypeError, ValueError):
        signal_count = 0

    if signal_count >= 3:
        return 0.9
    if signal_count == 2:
        return 0.75
    if signal_count == 1:
        return 0.5

    if "ISO_Severity_0to1" in record:
        try:
            score = float(record.get("ISO_Severity_0to1", 0) or 0)
            return max(0.0, min(1.0, 0.4 + (score * 0.6)))
        except (TypeError, ValueError):
            pass

    return float(fallback)


def _signal_name_mapping() -> Dict[str, str]:
    return {
        "ISO_Is_Anomaly": "Isolation Forest",
        "Correlation_Anomaly": "Correlation",
        "Quantity_Supply_Anomaly": "Quantity Supply",
        "Stat_Zscore_Anomaly": "Z-Score",
        "Stat_IQR_Anomaly": "IQR",
    }


def _derive_anomaly_type(record: Dict[str, Any]) -> str:
    """Infer anomaly type from triggered signal flags."""
    signal_names = []
    for flag_name, signal_name in _signal_name_mapping().items():
        if bool(record.get(flag_name, False)):
            signal_names.append(signal_name)

    if not signal_names:
        existing_type = _coalesce(record, ["Anomaly", "anomaly_type"])
        if existing_type:
            return str(existing_type)
        return "ML Anomaly"

    if len(signal_names) > 1:
        return "Composite Anomaly"

    return f"{signal_names[0]} Anomaly"


def _derive_primary_signal(record: Dict[str, Any]) -> Optional[str]:
    """Pick the strongest signal for the anomaly record."""
    signal_map = _signal_name_mapping()
    triggered = []
    for flag_name, signal_name in signal_map.items():
        if bool(record.get(flag_name, False)):
            triggered.append((signal_name, flag_name))

    if not triggered:
        existing = _coalesce(record, ["Primary Signal", "primary_signal"])
        return str(existing) if existing else None

    if len(triggered) == 1:
        return triggered[0][0]

    signal_scores = []
    for signal_name, flag_name in triggered:
        residual_key = flag_name.replace("_Anomaly", "_Residual")
        residual_value = record.get(residual_key)
        score = 0.0
        try:
            score = abs(float(residual_value)) if residual_value is not None else 0.0
        except (TypeError, ValueError):
            score = 0.0
        if score == 0.0 and "ISO_Severity_0to1" in record and flag_name == "ISO_Is_Anomaly":
            try:
                score = abs(float(record.get("ISO_Severity_0to1", 0) or 0))
            except (TypeError, ValueError):
                score = 0.0
        signal_scores.append((score, signal_name))

    if signal_scores:
        return max(signal_scores, key=lambda item: item[0])[1]

    return triggered[0][0]


def _extract_rca_payload(record_id: str, report_json_path: str) -> Dict[str, Any]:
    """Best-effort load RCA payload for a given record from known RCA outputs."""
    report_dir = Path(report_json_path).resolve().parent
    per_record_path = report_dir / f"rca_{record_id}.json"

    if per_record_path.exists():
        try:
            return json.loads(per_record_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"[DB] Failed to parse {per_record_path.name}: {e}")

    consolidated_path = report_dir / "rca_consolidated_report.json"
    if consolidated_path.exists():
        try:
            payload = json.loads(consolidated_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                for item in payload:
                    if str(item.get("record_id", "")).upper() == str(record_id).upper():
                        return item
        except Exception as e:
            logger.warning(f"[DB] Failed to parse {consolidated_path.name}: {e}")

    return {}


def _resolve_display_fields(record: Dict[str, Any], synthesis_record: Dict[str, Any], rca_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve canonical display values from the synthesis report before falling back to raw ML values."""
    metadata = synthesis_record.get("_metadata", {}) if isinstance(synthesis_record.get("_metadata"), dict) else {}

    severity = _coalesce(synthesis_record, ["Severity"], default=get_severity_from_record(record))
    priority = _coalesce(synthesis_record, ["Priority"], default=record.get("Priority", _map_severity_to_priority(str(severity).upper())))
    anomaly_type = _coalesce(synthesis_record, ["Anomaly", "anomaly_type"], default=_derive_anomaly_type(record))
    primary_signal = _coalesce(synthesis_record, ["Primary Signal", "primary_signal"], default=_derive_primary_signal(record))
    likely_root_cause = _coalesce(synthesis_record, ["Likely Root Cause", "likely_root_cause"], default=rca_payload.get("likely_root_cause"))
    recommended_action = _coalesce(synthesis_record, ["Recommended Action", "recommended_action"], default=rca_payload.get("recommended_action"))

    if not recommended_action:
        rca_actions = rca_payload.get("recommended_actions")
        if isinstance(rca_actions, list):
            recommended_action = "\n".join([str(x) for x in rca_actions if x is not None])
        elif rca_actions is not None:
            recommended_action = str(rca_actions)

    impact = _coalesce(metadata, ["impact"], default=rca_payload.get("impact", record.get("impact")))
    additional_checks = metadata.get("additional_checks")
    if isinstance(additional_checks, list):
        additional_checks = "\n".join([str(x) for x in additional_checks if x is not None])
    elif additional_checks is not None:
        additional_checks = str(additional_checks)
    if not additional_checks:
        additional_checks = rca_payload.get("additional_checks_required")
        if isinstance(additional_checks, list):
            additional_checks = "\n".join([str(x) for x in additional_checks if x is not None])
        elif additional_checks is not None:
            additional_checks = str(additional_checks)

    confidence = None
    if isinstance(metadata, dict) and metadata.get("confidence") is not None:
        try:
            confidence = float(metadata["confidence"])
        except (TypeError, ValueError):
            confidence = None
    if confidence is None:
        confidence = _calculate_confidence(record, fallback=rca_payload.get("confidence", 0.5))

    return {
        "severity": str(severity).upper(),
        "priority": str(priority),
        "anomaly_type": str(anomaly_type) if anomaly_type is not None else None,
        "primary_signal": str(primary_signal) if primary_signal is not None else None,
        "likely_root_cause": likely_root_cause,
        "recommended_action": recommended_action,
        "confidence": confidence,
        "impact": impact,
        "additional_checks": additional_checks,
    }


from models import AnalysisRun, AnomalyResult, Dataset


def generate_dataset_id() -> str:
    """Generate a unique dataset ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_suffix = str(uuid4())[:6]
    return f"DS-{timestamp}-{random_suffix}"


def generate_run_id() -> str:
    """Generate a unique run ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_suffix = str(uuid4())[:8]
    return f"RUN-{timestamp}-{random_suffix}"


def save_dataset(
    db: Session,
    filename: str,
    file_path: str,
    row_count: int,
    file_size_bytes: int,
    schema_info: Optional[List[str]] = None,
    dataset_id: Optional[str] = None,
) -> Dataset:
    """Save an uploaded dataset record to the database."""
    ds_id = dataset_id or generate_dataset_id()
    dataset = Dataset(
        id=ds_id,
        filename=filename,
        file_path=file_path,
        row_count=row_count,
        file_size_bytes=file_size_bytes,
        status="UPLOADED",
        schema_info=schema_info or [],
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    logger.info(f"[DB] Saved dataset {ds_id}: {filename} ({row_count} rows)")
    return dataset


def get_dataset_by_id(db: Session, dataset_id: str) -> Optional[Dataset]:
    """Fetch dataset metadata by ID."""
    return db.query(Dataset).filter(Dataset.id == dataset_id).first()


def load_dataset(dataset_id: str, db: Session):
    """
    Load dataframe for an uploaded dataset. Never falls back to default/training data.
    """
    import pandas as pd
    dataset = get_dataset_by_id(db, dataset_id)
    if not dataset:
        raise FileNotFoundError(f"Uploaded dataset {dataset_id} is not available for this run")
    
    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Dataset file does not exist at: {dataset.file_path}")

    if str(file_path).lower().endswith(('.xls', '.xlsx')):
        return pd.read_excel(file_path)
    return pd.read_csv(file_path)


def save_analysis_run(
    db: Session,
    filename: str,
    report_json_path: str,
    dataset_id: Optional[str] = None,
    run_id: Optional[str] = None,
    report_dir: Optional[str] = None,
    status: str = "completed",
    error_message: Optional[str] = None,
) -> AnalysisRun:
    """
    Save an analysis run and its results to the database with strict dataset lineage.

    Args:
        db: Database session
        filename: Name of uploaded file
        report_json_path: Path to final_anomaly_report.json from pipeline
        dataset_id: ID of source uploaded dataset
        run_id: Optional custom run ID
        report_dir: Path to run artifacts directory
        status: Processing status
        error_message: If processing failed

    Returns:
        AnalysisRun object
    """
    run_id = run_id or generate_run_id()
    rep_dir = report_dir or str(Path(report_json_path).resolve().parent)

    try:
        # Load the anomaly report
        report_data = load_anomaly_report(report_json_path)

        # Extract source records (handle both formats)
        if isinstance(report_data, dict):
            source_records = report_data.get("anomalies", [])
        else:
            source_records = report_data

        if not isinstance(source_records, list):
            raise ValueError("Unsupported report format: expected a list of records")

        # Keep total input records strictly equal to uploaded dataset records
        total_records = len(source_records)
        anomalies = [
            r for r in source_records
            if bool(r.get("ML_Is_Anomalous", False))
        ]
        synthesis_lookup = _load_synthesis_lookup(report_json_path)

        # Count records and severities using synthesis severity when available
        severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for anomaly in anomalies:
            record_id = _coalesce(anomaly, ["Record_ID", "Record ID", "record_id", "incident_id"], default="")
            synthesis_record = synthesis_lookup.get(_normalize_record_id(record_id), {}) if record_id else {}
            severity = _coalesce(synthesis_record, ["Severity"], default=get_severity_from_record(anomaly))
            severity = str(severity).upper()
            if severity in severity_counts:
                severity_counts[severity] += 1

        # Load run-specific population SLA and Data Quality summaries
        run_sla_summary = _load_sla_summary(report_json_path)
        run_dq_summary = _load_quality_summary(report_json_path)

        # Create run record with dataset lineage
        run = AnalysisRun(
            id=run_id,
            dataset_id=dataset_id,
            filename=filename,
            total_records=total_records,
            anomaly_count=len(anomalies),
            high_count=severity_counts.get("HIGH", 0),
            medium_count=severity_counts.get("MEDIUM", 0),
            low_count=severity_counts.get("LOW", 0),
            processing_status=status,
            error_message=error_message,
            report_dir=rep_dir,
            sla_summary=run_sla_summary,
            quality_summary=run_dq_summary,
        )

        db.add(run)

        # Update dataset status if linked
        if dataset_id:
            ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if ds:
                ds.status = "ANALYZED"

        db.commit()

        logger.info(
            f"[DB] Created analysis run: {run_id} (dataset_id={dataset_id}, input_records={total_records}, anomalies={len(anomalies)})"
        )

        # Save individual anomaly results
        for idx, anomaly in enumerate(anomalies):
            try:
                record_id = str(
                    _coalesce(
                        anomaly,
                        ["Record_ID", "Record ID", "record_id", "incident_id"],
                        default=f"UNKNOWN-{idx}",
                    )
                )
                record_type = str(
                    _coalesce(
                        anomaly,
                        ["Record_Type", "Type", "record_type"],
                        default="UNKNOWN",
                    )
                )

                synthesis_record = synthesis_lookup.get(_normalize_record_id(record_id), {})
                severity = str(
                    _coalesce(synthesis_record, ["Severity"], default=get_severity_from_record(anomaly))
                ).upper()
                priority = _coalesce(synthesis_record, ["Priority"], default=anomaly.get("Priority", _map_severity_to_priority(severity)))
                rca_payload = _extract_rca_payload(record_id, report_json_path)

                observed_facts = rca_payload.get("observed_facts")
                if observed_facts is not None and not isinstance(observed_facts, list):
                    observed_facts = [str(observed_facts)]

                possible_causes = rca_payload.get("possible_causes")
                if possible_causes is not None and not isinstance(possible_causes, list):
                    possible_causes = [str(possible_causes)]

                evidence = rca_payload.get("evidence")
                if evidence is not None and not isinstance(evidence, list):
                    evidence = [str(evidence)]

                anomaly_signals = rca_payload.get("anomaly_signals")
                if anomaly_signals is not None and not isinstance(anomaly_signals, dict):
                    anomaly_signals = {"raw": anomaly_signals}

                display_values = _resolve_display_fields(anomaly, synthesis_record, rca_payload)
                severity = display_values["severity"]
                priority = display_values["priority"]
                likely_root_cause = display_values["likely_root_cause"]
                recommended_action = display_values["recommended_action"]
                impact = display_values["impact"]
                additional_checks = display_values["additional_checks"]
                derived_anomaly_type = display_values["anomaly_type"]
                derived_primary_signal = display_values["primary_signal"]
                confidence = display_values["confidence"]

                merged_full_record = dict(anomaly)
                if rca_payload:
                    merged_full_record["RCA"] = rca_payload

                result = AnomalyResult(
                    run_id=run_id,
                    dataset_id=dataset_id,
                    record_id=record_id,
                    record_type=record_type,
                    severity=severity,
                    priority=priority,
                    anomaly_type=derived_anomaly_type,
                    primary_signal=derived_primary_signal,
                    likely_root_cause=likely_root_cause,
                    recommended_action=recommended_action,
                    confidence=confidence,
                    impact=impact,
                    additional_checks=additional_checks,
                    observed_facts=observed_facts,
                    possible_causes=possible_causes,
                    evidence=evidence,
                    anomaly_signals=anomaly_signals,
                    full_record=merged_full_record,
                )
                db.add(result)
            except Exception as e:
                logger.error(f"[DB] Failed to save anomaly {idx}: {e}")
                # Continue processing other anomalies
                continue

        db.commit()
        logger.info(f"[DB] Saved {len(anomalies)} anomaly results for run {run_id} (dataset_id={dataset_id})")

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

    Args:
        db: Database session
        limit: Max records to return
        offset: Offset for pagination

    Returns:
        Tuple of (runs_list, total_count)
    """
    query = db.query(AnalysisRun)
    total = query.count()
    runs = query.order_by(desc(AnalysisRun.created_at)).offset(offset).limit(limit).all()
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
    Get anomalies for a run with optional filtering and pagination.

    Args:
        db: Database session
        run_id: Run ID to filter by
        severity: Optional severity filter (HIGH, MEDIUM, LOW)
        page: Page number (1-indexed)
        page_size: Records per page
        search_query: Optional search term

    Returns:
        Tuple of (anomalies_list, total_count)
    """
    query = db.query(AnomalyResult).filter(AnomalyResult.run_id == run_id)

    # Filter by severity if provided
    if severity:
        query = query.filter(AnomalyResult.severity == severity.upper())

    # Search by record ID, type, anomaly type, or primary signal
    if search_query:
        search = f"%{search_query}%"
        query = query.filter(
            or_(
                AnomalyResult.record_id.ilike(search),
                AnomalyResult.record_type.ilike(search),
                AnomalyResult.anomaly_type.ilike(search),
                AnomalyResult.primary_signal.ilike(search),
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
    Get statistics for an isolated run.

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

    # Locate run-isolated artifact directory
    run_dir = Path(run.report_dir) if run.report_dir else (Path(__file__).resolve().parents[2] / "log" / "runs" / run_id)
    if not run_dir.exists():
        run_dir = Path(__file__).resolve().parents[2] / "log"

    quality_summary = run.quality_summary or _load_quality_summary(str(run_dir / "quality_report.json"))
    overall_quality_score = quality_summary.get("overall_quality_score")
    overall_risk_level = quality_summary.get("overall_risk_level")

    # Authoritative population SLA summary loaded for this specific run
    raw_sla_summary = run.sla_summary or _load_sla_summary(str(run_dir / "sla_temporal_findings.json"))
    
    if raw_sla_summary:
        on_track = raw_sla_summary.get("on_track", raw_sla_summary.get("records_normal", 0))
        at_risk = raw_sla_summary.get("at_risk", raw_sla_summary.get("records_at_risk", 0))
        breached = raw_sla_summary.get("breached", raw_sla_summary.get("records_breached", 0))
        not_assessable = raw_sla_summary.get("not_assessable", raw_sla_summary.get("records_not_assessable", 0))
        total_recs = raw_sla_summary.get("total_records", run.total_records)
        assessable = raw_sla_summary.get("records_assessable", total_recs - not_assessable)
        breach_breakdown = raw_sla_summary.get("breach_breakdown", {
            "time_based": 0,
            "service_payment_based": 0,
            "pending_outcome": 0,
        })
        sla_summary = {
            "total_records": total_recs,
            "records_assessable": assessable,
            "records_not_assessable": not_assessable,
            "records_breached": breached,
            "records_at_risk": at_risk,
            "records_normal": on_track,
            "on_track": on_track,
            "at_risk": at_risk,
            "breached": breached,
            "not_assessable": not_assessable,
            "breach_breakdown": breach_breakdown,
        }
    else:
        sla_summary = {
            "total_records": run.total_records,
            "records_assessable": run.total_records,
            "records_not_assessable": 0,
            "records_breached": 0,
            "records_at_risk": 0,
            "records_normal": run.total_records,
            "on_track": run.total_records,
            "at_risk": 0,
            "breached": 0,
            "not_assessable": 0,
            "breach_breakdown": {
                "time_based": 0,
                "service_payment_based": 0,
                "pending_outcome": 0,
            },
        }

    from services.processing_integrity import compute_processing_integrity
    report_file_path = str(run_dir / "final_anomaly_report.json")
    integrity_data = compute_processing_integrity(report_file_path)

    response = {
        "run_id": run.id,
        "dataset_id": run.dataset_id,
        "filename": run.filename,
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

    if overall_quality_score is not None:
        response["overall_data_quality_score"] = round(float(overall_quality_score), 2)
    if overall_risk_level is not None:
        response["overall_risk_level"] = overall_risk_level
    if sla_summary:
        response["sla_summary"] = sla_summary
    if integrity_data:
        response["processing_integrity"] = integrity_data

    return response


def _map_severity_to_priority(severity: str) -> str:
    """Map severity string to priority number."""
    mapping = {
        "HIGH": "2-High",
        "MEDIUM": "3-Medium",
        "LOW": "4-Low",
    }
    return mapping.get(severity.upper(), "3-Medium")
