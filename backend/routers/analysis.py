"""
FastAPI routes for file analysis and pipeline execution.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from schemas import AnalyzeResponse, ErrorResponse
from services.pipeline_adapter import run_existing_pipeline
from services.result_service import save_analysis_run, get_run_by_id

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])

# Store for tracking background job status
background_jobs = {}


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
):
    """
    Upload a CSV/XLSX/XLS file and trigger the anomaly detection pipeline.

    This endpoint:
    1. Validates the uploaded file
    2. Saves it temporarily
    3. Calls the EXISTING UC10 pipeline (via pipeline_adapter)
    4. Stores results in SQLite
    5. Returns job status

    Args:
        file: Uploaded CSV/XLSX/XLS file
        db: Database session

    Returns:
        AnalyzeResponse with run ID and initial summary
    """
    try:
        # Validate file extension
        valid_extensions = {".csv", ".xls", ".xlsx"}
        file_ext = Path(file.filename).suffix.lower()

        if file_ext not in valid_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file format: {file_ext}. Supported: {', '.join(valid_extensions)}",
            )

        # Validate file size (max 100MB)
        max_size_bytes = 100 * 1024 * 1024
        if file.size and file.size > max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: 100MB",
            )

        # Save uploaded file to temporary location
        temp_dir = tempfile.mkdtemp(prefix="uc10_")
        temp_file_path = os.path.join(temp_dir, file.filename)

        try:
            # Write uploaded file to disk
            with open(temp_file_path, "wb") as temp_file:
                content = await file.read()
                if not content:
                    raise HTTPException(status_code=400, detail="Uploaded file is empty")
                temp_file.write(content)

            logger.info(f"[API] Received file: {file.filename} ({len(content)} bytes)")

            # Call the EXISTING UC10 pipeline
            logger.info(f"[API] Starting pipeline for file: {file.filename}")

            try:
                report_json_path, pipeline_metadata = run_existing_pipeline(temp_file_path)
            except Exception as e:
                logger.error(f"[API] Pipeline execution failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Pipeline execution failed: {str(e)}",
                )

            # Save analysis run to database
            try:
                run = save_analysis_run(
                    db,
                    filename=file.filename,
                    report_json_path=report_json_path,
                    status="completed",
                )
            except Exception as e:
                logger.error(f"[API] Database save failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to save results: {str(e)}",
                )

            # Schedule cleanup of temp file (after response is sent)
            if background_tasks:
                background_tasks.add_task(_cleanup_temp_file, temp_file_path)

            logger.info(f"[API] Analysis completed: {run.id}")

            return AnalyzeResponse(
                run_id=run.id,
                status=run.processing_status,
                filename=run.filename,
                total_records=run.total_records,
                total_anomalies=run.anomaly_count,
                severity_summary={
                    "high": run.high_count,
                    "medium": run.medium_count,
                    "low": run.low_count,
                },
                message=f"Analysis completed. Found {run.anomaly_count} anomalies.",
            )

        except Exception as e:
            # Cleanup temp directory on error
            if os.path.exists(temp_dir):
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temp dir: {cleanup_error}")
            raise

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Unexpected error in /analyze: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}",
        )


@router.get("/runs/{run_id}/download")
def download_results(
    run_id: str,
    severity: Optional[str] = None,
    format: str = "csv",
    db: Session = Depends(get_db),
):
    """
    Download anomaly results as CSV or Excel.

    Args:
        run_id: Analysis run ID
        severity: Optional filter (HIGH, MEDIUM, LOW)
        format: Output format (csv or xlsx)
        db: Database session

    Returns:
        File download response
    """
    from services.result_service import get_anomalies_for_run

    try:
        run = get_run_by_id(db, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        # Get all anomalies (no pagination for download)
        anomalies, _ = get_anomalies_for_run(db, run_id, severity=severity, page_size=10000)

        if format.lower() == "csv":
            import csv
            import io

            # Create CSV in memory
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    "Priority",
                    "Record ID",
                    "Record Type",
                    "Anomaly Type",
                    "Severity",
                    "Primary Signal",
                    "Likely Root Cause",
                    "Recommended Action",
                    "Confidence",
                ],
            )
            writer.writeheader()

            for anomaly in anomalies:
                writer.writerow(
                    {
                        "Priority": anomaly.priority,
                        "Record ID": anomaly.record_id,
                        "Record Type": anomaly.record_type,
                        "Anomaly Type": anomaly.anomaly_type or "",
                        "Severity": anomaly.severity,
                        "Primary Signal": anomaly.primary_signal or "",
                        "Likely Root Cause": anomaly.likely_root_cause or "",
                        "Recommended Action": anomaly.recommended_action or "",
                        "Confidence": anomaly.confidence or "",
                    }
                )

            # Return as file download
            csv_bytes = output.getvalue().encode("utf-8")
            filename = f"anomalies_{run_id}.csv"

            return StreamingResponse(
                iter([csv_bytes]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

        else:
            raise HTTPException(status_code=400, detail="Format must be 'csv'")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Download failed: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


def _cleanup_temp_file(file_path: str):
    """Background task to cleanup temporary file."""
    try:
        import shutil
        if os.path.exists(file_path):
            parent_dir = os.path.dirname(file_path)
            shutil.rmtree(parent_dir)
            logger.info(f"[CLEANUP] Removed temp file: {file_path}")
    except Exception as e:
        logger.warning(f"[CLEANUP] Failed to remove temp file {file_path}: {e}")
