import os
import shutil
import pandas as pd
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Body
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Dataset, AnalysisRun
from schemas import AnalyzeResponse, DatasetResponse, ErrorResponse
from services.pipeline_adapter import run_existing_pipeline
from services.result_service import (
    save_analysis_run,
    get_run_by_id,
    get_run_statistics,
    generate_dataset_id,
    generate_run_id,
    save_dataset,
    get_dataset_by_id,
    load_dataset,
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/datasets/upload", response_model=DatasetResponse)
async def upload_dataset_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Persist an uploaded dataset, inspect schema and row count, and generate a Dataset ID.
    """
    valid_extensions = {".csv", ".xls", ".xlsx"}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in valid_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format: {file_ext}. Supported: {', '.join(valid_extensions)}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    repo_root = Path(__file__).resolve().parents[2]
    uploads_dir = repo_root / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    dataset_id = generate_dataset_id()
    saved_filename = f"{dataset_id}_{file.filename}"
    saved_file_path = uploads_dir / saved_filename

    with open(saved_file_path, "wb") as f:
        f.write(content)

    # Read row count directly from the uploaded file
    try:
        if file_ext in (".xls", ".xlsx"):
            df = pd.read_excel(saved_file_path)
        else:
            df = pd.read_csv(saved_file_path)
        row_count = len(df)
        schema_info = df.columns.tolist()
    except Exception as e:
        logger.error(f"[API] Failed to parse uploaded dataset: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse uploaded dataset: {e}")

    dataset = save_dataset(
        db=db,
        filename=file.filename,
        file_path=str(saved_file_path),
        row_count=row_count,
        file_size_bytes=len(content),
        schema_info=schema_info,
        dataset_id=dataset_id,
    )

    return DatasetResponse(
        dataset_id=dataset.id,
        filename=dataset.filename,
        row_count=dataset.row_count,
        file_size_bytes=dataset.file_size_bytes,
        status=dataset.status,
        schema_info=dataset.schema_info,
        created_at=dataset.created_at.isoformat(),
    )


@router.get("/datasets", response_model=List[DatasetResponse])
def list_datasets_endpoint(db: Session = Depends(get_db)):
    """List all uploaded datasets."""
    datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).all()
    return [
        DatasetResponse(
            dataset_id=d.id,
            filename=d.filename,
            row_count=d.row_count,
            file_size_bytes=d.file_size_bytes,
            status=d.status,
            schema_info=d.schema_info,
            created_at=d.created_at.isoformat() if d.created_at else None,
        )
        for d in datasets
    ]


@router.post("/runs", response_model=AnalyzeResponse)
def create_run_endpoint(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """
    Trigger a new analysis run for a previously uploaded dataset ID.
    """
    dataset_id = payload.get("dataset_id")
    if not dataset_id:
        raise HTTPException(status_code=400, detail="dataset_id is required")

    dataset = get_dataset_by_id(db, dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=404,
            detail=f"Uploaded dataset {dataset_id} is not available for this run",
        )

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Dataset file is missing on disk: {dataset.file_path}",
        )

    run_id = generate_run_id()
    repo_root = Path(__file__).resolve().parents[2]
    run_dir = repo_root / "log" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    try:
        report_json_path, _ = run_existing_pipeline(
            str(file_path),
            output_dir=str(run_dir),
            run_id=run_id,
            dataset_id=dataset_id,
        )
        run = save_analysis_run(
            db=db,
            filename=dataset.filename,
            report_json_path=report_json_path,
            dataset_id=dataset_id,
            run_id=run_id,
            report_dir=str(run_dir),
            status="completed",
        )

        return AnalyzeResponse(
            run_id=run.id,
            dataset_id=run.dataset_id,
            status=run.processing_status,
            filename=run.filename,
            total_records=run.total_records,
            total_anomalies=run.anomaly_count,
            severity_summary={
                "high": run.high_count,
                "medium": run.medium_count,
                "low": run.low_count,
            },
            message=f"Analysis completed for dataset {dataset_id}. Processed {run.total_records} records.",
        )
    except Exception as e:
        logger.error(f"[API] Run execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
):
    """
    Upload a CSV/XLSX/XLS file, persist dataset, and trigger the isolated anomaly detection pipeline.
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

        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        repo_root = Path(__file__).resolve().parents[2]
        uploads_dir = repo_root / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)

        dataset_id = generate_dataset_id()
        saved_filename = f"{dataset_id}_{file.filename}"
        saved_file_path = uploads_dir / saved_filename

        with open(saved_file_path, "wb") as temp_file:
            temp_file.write(content)

        logger.info(f"[API] Received and persisted file: {file.filename} as {dataset_id} ({len(content)} bytes)")

        # Inspect actual row count and schema
        try:
            if file_ext in (".xls", ".xlsx"):
                df_inspect = pd.read_excel(saved_file_path)
            else:
                df_inspect = pd.read_csv(saved_file_path)
            actual_row_count = len(df_inspect)
            schema_info = df_inspect.columns.tolist()
        except Exception as e:
            logger.error(f"[API] Failed to parse uploaded dataset: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to parse uploaded dataset: {e}")

        # Save Dataset record
        dataset = save_dataset(
            db=db,
            filename=file.filename,
            file_path=str(saved_file_path),
            row_count=actual_row_count,
            file_size_bytes=len(content),
            schema_info=schema_info,
            dataset_id=dataset_id,
        )

        run_id = generate_run_id()
        run_dir = repo_root / "log" / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"[API] Starting isolated pipeline for {file.filename} (Dataset: {dataset_id}, Run: {run_id})")

        try:
            report_json_path, _ = run_existing_pipeline(
                str(saved_file_path),
                output_dir=str(run_dir),
                run_id=run_id,
                dataset_id=dataset_id,
            )
        except Exception as e:
            logger.error(f"[API] Pipeline execution failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Pipeline execution failed: {str(e)}",
            )

        # Save analysis run with dataset lineage
        try:
            run = save_analysis_run(
                db=db,
                filename=file.filename,
                report_json_path=report_json_path,
                dataset_id=dataset_id,
                run_id=run_id,
                report_dir=str(run_dir),
                status="completed",
            )
        except Exception as e:
            logger.error(f"[API] Database save failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save results: {str(e)}",
            )

        logger.info(f"[API] Analysis completed: {run.id} for dataset {dataset_id}")

        return AnalyzeResponse(
            run_id=run.id,
            dataset_id=run.dataset_id,
            status=run.processing_status,
            filename=run.filename,
            total_records=run.total_records,
            total_anomalies=run.anomaly_count,
            severity_summary={
                "high": run.high_count,
                "medium": run.medium_count,
                "low": run.low_count,
            },
            message=f"Analysis completed for dataset {dataset_id}. Processed {run.total_records} records.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Unexpected error in /analyze: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}",
        )


@router.get("/runs/{run_id}/summary")
def get_run_summary_endpoint(run_id: str, db: Session = Depends(get_db)):
    """
    Get high-level summary metrics for a specific run.
    """
    run = get_run_by_id(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    stats = get_run_statistics(db, run_id)
    sla_sum = stats.get("sla_summary", {})
    return {
        "run_id": run.id,
        "dataset_id": run.dataset_id,
        "filename": run.filename,
        "total_records": run.total_records,
        "anomalies": run.anomaly_count,
        "sla_breaches": sla_sum.get("records_breached", sla_sum.get("breached", 0)),
        "data_quality_score": stats.get("overall_data_quality_score", 100.0),
    }


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
