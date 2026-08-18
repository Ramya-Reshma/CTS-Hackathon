"""
FastAPI routes for querying and viewing anomalies.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas import AnomaliesListResponse, AnomalyResultResponse, AnomalyResultDetail
from services.result_service import (
    get_run_by_id,
    list_runs,
    get_anomalies_for_run,
    get_anomaly_detail,
    get_run_statistics,
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["anomalies"])


@router.get("/runs")
def get_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List analysis runs for run-history views."""
    try:
        offset = (page - 1) * page_size
        runs, total = list_runs(db=db, limit=page_size, offset=offset)

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "records": [run.to_dict() for run in runs],
        }
    except Exception as e:
        logger.error(f"[API] Error listing runs: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/runs/{run_id}/anomalies", response_model=AnomaliesListResponse)
def list_anomalies(
    run_id: str,
    severity: Optional[str] = Query(None, description="Filter by severity: HIGH, MEDIUM, LOW"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None, description="Search by record ID, type, etc."),
    db: Session = Depends(get_db),
):
    """
    Get anomalies for a run with optional filtering and pagination.

    Query Parameters:
        severity: Optional filter (HIGH, MEDIUM, LOW)
        page: Page number (1-indexed)
        page_size: Results per page (max 500)
        search: Search string (record_id, type, anomaly_type)

    Returns:
        List of anomaly records with pagination info
    """
    try:
        # Verify run exists
        run = get_run_by_id(db, run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

        # Get anomalies with filters
        anomalies, total = get_anomalies_for_run(
            db,
            run_id=run_id,
            severity=severity,
            page=page,
            page_size=page_size,
            search_query=search,
        )

        logger.info(
            f"[API] Listed {len(anomalies)} anomalies for run {run_id} "
            f"(severity={severity}, page={page}, search={search})"
        )

        return AnomaliesListResponse(
            run_id=run_id,
            total=total,
            page=page,
            page_size=page_size,
            severity_filter=severity,
            records=[AnomalyResultResponse.model_validate(a) for a in anomalies],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error listing anomalies: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/anomalies/{anomaly_id}", response_model=AnomalyResultDetail)
def get_anomaly(anomaly_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a single anomaly.

    Includes:
    - Record ID, type, severity
    - Primary signals and evidence
    - Root cause analysis
    - Recommended actions
    - Technical fields and full record

    Args:
        anomaly_id: Anomaly database ID

    Returns:
        Detailed anomaly information
    """
    try:
        anomaly = get_anomaly_detail(db, anomaly_id)

        if not anomaly:
            raise HTTPException(status_code=404, detail=f"Anomaly {anomaly_id} not found")

        logger.info(f"[API] Fetched anomaly details: {anomaly_id}")

        return AnomalyResultDetail.model_validate(anomaly)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error fetching anomaly: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/runs/{run_id}")
def get_run_info(run_id: str, db: Session = Depends(get_db)):
    """
    Get metadata and statistics for an analysis run.

    Args:
        run_id: Analysis run ID

    Returns:
        Run metadata and statistics
    """
    try:
        run = get_run_by_id(db, run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

        stats = get_run_statistics(db, run_id)

        logger.info(f"[API] Fetched run info: {run_id}")

        return {
            "run": run.to_dict(),
            "statistics": stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error fetching run info: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/runs/{run_id}/integrity")
def get_run_integrity(run_id: str, db: Session = Depends(get_db)):
    """
    Get 4-stage processing integrity validation for an analysis run.
    """
    try:
        run = get_run_by_id(db, run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

        from pathlib import Path
        from services.processing_integrity import compute_processing_integrity

        run_dir = Path(run.report_dir) if run.report_dir else (Path(__file__).resolve().parents[2] / "log" / "runs" / run_id)
        report_file_path = str(run_dir / "final_anomaly_report.json")
        if not Path(report_file_path).exists():
            report_file_path = str(Path(__file__).resolve().parents[2] / "log" / "final_anomaly_report.json")

        integrity = compute_processing_integrity(report_file_path)

        return {
            "run_id": run_id,
            "processing_integrity": integrity,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error fetching integrity: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/runs/{run_id}/sla")
def get_run_sla_findings(run_id: str, db: Session = Depends(get_db)):
    """
    Get authoritative SLA findings and per-record details for an analysis run.
    """
    try:
        run = get_run_by_id(db, run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

        from pathlib import Path
        import json

        run_dir = Path(run.report_dir) if run.report_dir else (Path(__file__).resolve().parents[2] / "log" / "runs" / run_id)
        sla_file_path = run_dir / "sla_temporal_findings.json"
        if not sla_file_path.exists():
            sla_file_path = Path(__file__).resolve().parents[2] / "log" / "sla_temporal_findings.json"

        sla_data = {}
        if sla_file_path.exists():
            try:
                with open(sla_file_path, "r", encoding="utf-8") as f:
                    sla_data = json.load(f)
            except Exception as e:
                logger.warning(f"[API] Failed to parse {sla_file_path}: {e}")

        records = sla_data.get("record_level_findings", [])
        summary = sla_data.get("summary", run.sla_summary or {})

        # Load full anomaly report to merge any extra claim attributes if needed
        report_file_path = run_dir / "final_anomaly_report.json"
        if not report_file_path.exists():
            report_file_path = Path(__file__).resolve().parents[2] / "log" / "final_anomaly_report.json"

        full_report_map = {}
        if report_file_path.exists():
            try:
                with open(report_file_path, "r", encoding="utf-8") as f:
                    rep_list = json.load(f)
                    if isinstance(rep_list, list):
                        for r in rep_list:
                            rid = str(r.get("Record_ID", "")).strip().upper()
                            if rid:
                                full_report_map[rid] = r
            except Exception:
                pass

        enriched_records = []
        for idx, rec in enumerate(records):
            rid = str(rec.get("record_id", "")).strip().upper()
            full_rec = full_report_map.get(rid, {})
            merged = {**full_rec, **rec}

            sla_status = rec.get("sla_status") or rec.get("status") or ("BREACHED" if rec.get("is_breached") else "ON_TRACK")
            is_breached = bool(rec.get("is_breached", False) or sla_status == "BREACHED" or rec.get("sla_breach") is True)
            breach_cats = rec.get("breach_categories", [])
            breach_reasons = rec.get("breach_reasons", [])
            primary_cat = breach_cats[0] if breach_cats else ("TIME_BASED" if is_breached else "NONE")

            record_item = {
                "id": rec.get("record_id") or f"SLA-{idx}",
                "record_id": rec.get("record_id", ""),
                "record_type": rec.get("record_type", full_rec.get("Record_Type", "")),
                "sla_group": rec.get("sla_group", ""),
                "batch_id": rec.get("batch_id", ""),
                "sla_target_days": rec.get("sla_target_days", full_rec.get("SLA_Target_Days")),
                "processing_latency_days": rec.get("processing_latency_days", full_rec.get("Processing_Latency_Days")),
                "sla_utilization": rec.get("sla_utilization", full_rec.get("SLA_Utilization")),
                "temporal_validity": rec.get("temporal_validity", "VALID"),
                "status": sla_status,
                "sla_status": sla_status,
                "is_breached": is_breached,
                "sla_breach": is_breached,
                "sla_risk": rec.get("sla_risk", "HIGH" if is_breached else "LOW"),
                "breach_categories": breach_cats,
                "breach_reasons": breach_reasons,
                "sla_breach_category": primary_cat,
                "sla_breach_reason": "; ".join(breach_reasons) if breach_reasons else rec.get("reason", ""),
                "reason": rec.get("reason", ""),
                "full_record": {
                    **merged,
                    "Record_ID": rec.get("record_id", ""),
                    "Record_Type": rec.get("record_type", full_rec.get("Record_Type", "")),
                    "SLA_Target_Days": rec.get("sla_target_days", full_rec.get("SLA_Target_Days")),
                    "Processing_Latency_Days": rec.get("processing_latency_days", full_rec.get("Processing_Latency_Days")),
                    "SLA_Utilization": rec.get("sla_utilization", full_rec.get("SLA_Utilization")),
                    "SLA_Status": sla_status,
                    "Is_Breached": is_breached,
                    "SLA_Breach": is_breached,
                    "SLA_Risk": rec.get("sla_risk", "HIGH" if is_breached else "LOW"),
                    "Breach_Categories": breach_cats,
                    "Breach_Reasons": breach_reasons,
                    "SLA_Breach_Category": primary_cat,
                    "SLA_Reason": "; ".join(breach_reasons) if breach_reasons else rec.get("reason", ""),
                }
            }
            enriched_records.append(record_item)

        return {
            "run_id": run_id,
            "total_records": len(enriched_records),
            "summary": summary,
            "records": enriched_records,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error fetching SLA findings: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
