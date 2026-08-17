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
