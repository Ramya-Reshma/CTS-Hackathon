"""
Adapter for calling the EXISTING UC10 anomaly detection pipeline.

This module serves as a wrapper around the existing ML pipeline without modifying it.
It:
1. Accepts an input file (CSV/XLSX/XLS)
2. Calls the existing ML pipeline
3. Returns the final anomaly report

DO NOT MODIFY THE EXISTING PIPELINE LOGIC.
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Tuple
import logging

# Add project root to Python path to import ML module
# This allows importing ML.main even when backend is in a subdirectory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


_GLOBAL_LLM_AVAILABLE = None


def _generate_rca_outputs(report_json_path: str) -> Dict[str, Any]:
    """Best-effort RCA generation for anomalous records using existing UC10 RCA modules."""
    global _GLOBAL_LLM_AVAILABLE
    try:
        from UC10_Anomaly_Monitor.rca import evidence_builder, rag, agent
        from UC10_Anomaly_Monitor.config import settings
    except Exception as import_error:
        logger.warning(f"[PIPELINE] RCA modules unavailable, skipping RCA generation: {import_error}")
        return {"generated": False, "reason": "rca_import_failed"}

    report_path = Path(report_json_path)
    if not report_path.exists():
        return {"generated": False, "reason": "report_not_found"}

    try:
        records = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as parse_error:
        logger.warning(f"[PIPELINE] Failed to parse report for RCA: {parse_error}")
        return {"generated": False, "reason": "invalid_report_format"}

    if not isinstance(records, list):
        return {"generated": False, "reason": "invalid_report_format"}

    anomalous_records = [r for r in records if bool(r.get("ML_Is_Anomalous", False))]
    if not anomalous_records:
        return {"generated": True, "count": 0, "consolidated_path": None}

    max_rca_records = 100
    if len(anomalous_records) > max_rca_records:
        logger.info(
            f"[PIPELINE] Limiting RCA generation to first {max_rca_records} anomalies out of {len(anomalous_records)}"
        )
        anomalous_records = anomalous_records[:max_rca_records]

    output_dir = report_path.parent
    historical_kb = str(Path(settings.JSON_REPORT_PATH).parent / "historical_resolution_cases.json")
    consolidated = []
    success = 0

    for record in anomalous_records:
        record_id = str(record.get("Record_ID", "")).strip()
        if not record_id:
            continue

        try:
            ev = evidence_builder.build_evidence(record_id, report_path=str(report_path))
            similar_cases = rag.retrieve_similar_cases(ev, limit=5)

            if _GLOBAL_LLM_AVAILABLE is not False:
                try:
                    rca_agent = agent.RCAAgent()
                    rca_report = rca_agent.run_rag_rca(ev, historical_cases=similar_cases)
                    if hasattr(rca_report, "model_dump"):
                        payload = rca_report.model_dump()
                    elif isinstance(rca_report, dict):
                        payload = rca_report
                    else:
                        payload = json.loads(rca_report.model_dump_json())
                    _GLOBAL_LLM_AVAILABLE = True
                except Exception as llm_error:
                    logger.info(f"[PIPELINE] LLM RCA unavailable, switching to deterministic RAG recommendation: {llm_error}")
                    _GLOBAL_LLM_AVAILABLE = False
                    payload = rag.generate_rag_recommendation(ev)
            else:
                payload = rag.generate_rag_recommendation(ev)

            if hasattr(payload, "model_dump"):
                payload = payload.model_dump()
            elif hasattr(payload, "dict"):
                payload = payload.dict()
            elif isinstance(payload, str):
                payload = json.loads(payload)

            if isinstance(payload, dict):
                payload["record_id"] = record_id
                consolidated.append(payload)
                success += 1
        except Exception as e:
            logger.warning(f"[PIPELINE] RCA generation failed for {record_id}: {e}")

    consolidated_path = output_dir / "rca_consolidated_report.json"
    consolidated_path.write_text(json.dumps(consolidated, indent=2), encoding="utf-8")

    final_analysis_path = output_dir / "final_analysis_report.json"
    final_output = {"analyses": consolidated}
    final_analysis_path.write_text(json.dumps(final_output, indent=2), encoding="utf-8")

    logger.info(
        f"[PIPELINE] RCA generation complete: {success}/{len(anomalous_records)} records, output={final_analysis_path}"
    )
    return {
        "generated": True,
        "count": success,
        "consolidated_path": str(consolidated_path),
        "final_analysis_path": str(final_analysis_path),
    }


# Exact 18 columns generated by ML/feature_engineering.py to sanitize if pre-existing in input
GENERATED_FEATURE_COLUMNS = [
    "Batch_Date",
    "Provider_Total_Records",
    "Provider_Denial_Rate",
    "Batch_Volume",
    "Rolling_7D_Avg_Volume",
    "Volume_Vs_Trend_Ratio",
    "Batch_SLA_Breach_Rate",
    "Rolling_7D_Avg_SLA_Breach_Rate",
    "SLA_Breach_Rate_Vs_Trend_Diff",
    "Beneficiary_Record_Count",
    "High_Frequency_Beneficiary_Flag",
    "Missing_Required_Auth_Link",
    "Days_Since_Prev_Batch",
    "Pipeline_Gap_Flag",
    "Submission_Day_Of_Week",
    "DOW_Avg_SLA_Breach_Rate",
    "Record_SLA_Breach_Numeric",
    "SLA_Breach_Vs_DOW_Norm",
]


def normalize_data_types(input_file_path: str, output_file_path: str) -> str:
    """
    Normalize data types and schema in the input file to prevent encoder and missing-column errors.
    
    This preprocesses the file to ensure:
    - Common column aliases (Claim_Type, Quantity, etc.) are mapped to canonical columns
    - Missing core schema fields receive sensible healthcare defaults
    - Boolean columns are converted to strings (e.g., True -> 'True')
    - All object columns are properly stringified
    - Removes pre-existing generated feature columns so Feature Engineering recomputes them cleanly
    
    Args:
        input_file_path: Path to original input file
        output_file_path: Path where normalized file will be saved
    
    Returns:
        Path to normalized file
    """
    import pandas as pd
    import numpy as np
    
    input_path = Path(input_file_path)
    
    try:
        # Read the file
        if str(input_path).lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(input_path)
        else:
            df = pd.read_csv(input_path)
        
        # Remove any pre-existing generated feature columns to avoid merge collisions in Feature Engineering
        existing_cols = [c for c in GENERATED_FEATURE_COLUMNS if c in df.columns]
        if existing_cols:
            logger.info(f"[PIPELINE] Pre-existing generated columns removed: {existing_cols}")
            df = df.drop(columns=existing_cols)
        
        # Map common aliases if canonical column is not present
        if 'Claim_Type' in df.columns and 'Record_Type' not in df.columns:
            type_map = {
                'Medical Claim': 'MEDICAL_CLAIM',
                'Pharmacy Claim': 'PHARMACY_CLAIM',
                'Prior Authorization': 'PRIOR_AUTH',
                'Prior Auth': 'PRIOR_AUTH',
                'Auth': 'PRIOR_AUTH',
            }
            df['Record_Type'] = df['Claim_Type'].map(
                lambda x: type_map.get(str(x).strip(), str(x).strip().upper().replace(' ', '_'))
            )
        
        if 'Quantity' in df.columns and 'Quantity_Dispensed' not in df.columns:
            df['Quantity_Dispensed'] = df['Quantity']
        
        if 'Claim_Status' in df.columns and 'Status' not in df.columns:
            df['Status'] = df['Claim_Status']
        
        if 'Claim_ID' in df.columns and 'Record_ID' not in df.columns:
            df['Record_ID'] = df['Claim_ID']
        elif 'Incident_ID' in df.columns and 'Record_ID' not in df.columns:
            df['Record_ID'] = df['Incident_ID']
        
        if 'Member_ID' in df.columns and 'BENE_ID' not in df.columns:
            df['BENE_ID'] = df['Member_ID']
        
        if 'NPI' in df.columns and 'Provider_NPI' not in df.columns:
            df['Provider_NPI'] = df['NPI']
        
        # Ensure core columns exist with sensible defaults if omitted from test files
        n = len(df)
        defaults = {
            'Record_ID': [f'REC_{i+1:06d}' for i in range(n)],
            'Record_Type': 'MEDICAL_CLAIM',
            'BENE_ID': [f'BENE_{(i % 50) + 1:04d}' for i in range(n)],
            'Provider_NPI': [f'NPI_{1000000000 + (i % 20)}' for i in range(n)],
            'Provider_State': 'TX',
            'Service_Date': '2026-01-01',
            'Service_End_Date': '2026-01-01',
            'Submission_Date': '2026-01-02',
            'Processed_Date': '2026-01-05',
            'Decision_Date': '2026-01-05',
            'Status': 'APPROVED',
            'Denial_Reason_Code': None,
            'Diagnosis_Code': 'Z00.00',
            'Procedure_Code': '99213',
            'NDC_Code': None,
            'Drug_Name': None,
            'Days_Supply': 30,
            'Quantity_Dispensed': 1.0,
            'Billed_Amount': 100.0,
            'Allowed_Amount': 80.0,
            'Paid_Amount': 72.0,
            'Patient_Responsibility': 0.0,
            'Urgency_Flag': 'STANDARD',
            'Auth_Required_Flag': 'N',
            'Auth_Linked_ID': None,
            'Batch_ID': [f'BATCH_202601{((i // 25) + 1):02d}' for i in range(n)],
            'Source_System': 'FACETS',
            'Ingestion_Timestamp': '2026-01-02 00:00:00',
            'Retry_Count': 0,
            'Processing_Latency_Days': 3,
            'SLA_Target_Days': 5,
            'SLA_Breach_Flag': 'N'
        }
        
        for col, default_val in defaults.items():
            if col not in df.columns:
                df[col] = default_val
        
        # Calculate derived amounts if partial financials were supplied
        if 'Billed_Amount' in df.columns and 'Allowed_Amount' not in df.columns:
            df['Allowed_Amount'] = df['Billed_Amount'] * 0.8
        if 'Allowed_Amount' in df.columns and 'Paid_Amount' not in df.columns:
            df['Paid_Amount'] = df['Allowed_Amount'] * 0.9
        
        # Convert boolean columns to strings to avoid mixed type issues
        for col in df.columns:
            # Check explicit boolean dtype
            if df[col].dtype == 'bool':
                df[col] = df[col].astype(str)
            # Check object columns for any boolean values
            elif df[col].dtype == 'object':
                has_bool = any(isinstance(x, bool) for x in df[col].dropna())
                if has_bool:
                    df[col] = df[col].astype(str)
        
        # Save normalized file
        if str(output_file_path).lower().endswith('.xlsx'):
            df.to_excel(output_file_path, index=False)
        else:
            df.to_csv(output_file_path, index=False)
        
        logger.info(f"[PIPELINE] Data types and schema normalized: {output_file_path}")
        return output_file_path
        
    except Exception as e:
        logger.error(f"[PIPELINE] Data normalization failed: {str(e)}")
        return input_file_path


def run_existing_pipeline(
    input_file_path: str,
    output_dir: str = None,
    run_id: str = None,
    dataset_id: str = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Call the EXISTING UC10 anomaly detection pipeline on ONLY the uploaded dataset.

    This function:
    1. Validates the input file
    2. Calls ML.main.run_pipeline (the existing pipeline)
    3. Returns the path to final_anomaly_report.json and metadata

    Args:
        input_file_path: Path to uploaded CSV/XLSX/XLS file
        output_dir: Optional custom output directory
        run_id: Optional Run ID
        dataset_id: Optional Dataset ID

    Returns:
        Tuple of (report_json_path, metadata_dict)

    Raises:
        FileNotFoundError: If input file does not exist
        ValueError: If file format is not supported
        Exception: If pipeline execution fails
    """
    input_path = Path(input_file_path)

    # Validate input file exists
    if not input_path.exists():
        raise FileNotFoundError(f"Uploaded dataset is not available for this run: {input_file_path}")

    # Validate file extension
    valid_extensions = {'.csv', '.xls', '.xlsx'}
    if input_path.suffix.lower() not in valid_extensions:
        raise ValueError(
            f"Invalid file format: {input_path.suffix}. "
            f"Supported formats: {', '.join(valid_extensions)}"
        )

    # Set output directory to log/runs/{run_id} or log/ if not specified
    if output_dir is None:
        repo_root = Path(__file__).resolve().parents[2]
        if run_id:
            output_dir = str(repo_root / "log" / "runs" / run_id)
        else:
            output_dir = str(repo_root / "log")

    try:
        logger.info(f"[PIPELINE] Starting UC10 pipeline with input: {input_file_path}")
        logger.info(f"[PIPELINE] Output directory: {output_dir}")

        # Normalize data types to avoid encoder errors (bool/str mixed types)
        temp_dir = tempfile.mkdtemp(prefix="uc10_normalized_")
        normalized_file_path = Path(temp_dir) / input_path.name
        normalized_file_path = normalize_data_types(
            input_file_path, 
            str(normalized_file_path)
        )

        # Import and call the EXISTING pipeline (ML.main.run_pipeline)
        from ML.main import run_pipeline

        # Call the pipeline with ONLY the uploaded/normalized dataset
        report_json_path = run_pipeline(
            normalized_file_path,
            output_dir=output_dir,
            run_id=run_id,
            dataset_id=dataset_id,
        )

        # Generate RCA outputs after pipeline report is produced.
        rca_metadata = _generate_rca_outputs(report_json_path)

        logger.info(f"[PIPELINE] Pipeline completed successfully")
        logger.info(f"[PIPELINE] Report saved to: {report_json_path}")

        # Load the report to extract metadata
        with open(report_json_path, 'r') as f:
            report_data = json.load(f)

        # Count anomalies by severity (if available in synthesis report)
        # For now, report basic metadata
        metadata = {
            "report_path": report_json_path,
            "total_records": len(report_data) if isinstance(report_data, list) else len(report_data.get("anomalies", [])),
            "input_file": input_path.name,
            "rca": rca_metadata,
        }

        # Cleanup normalized temp file
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

        return report_json_path, metadata

    except Exception as e:
        logger.error(f"[PIPELINE] Pipeline execution failed: {str(e)}")
        raise


def load_anomaly_report(report_json_path: str) -> Dict[str, Any]:
    """
    Load the final anomaly report JSON.

    Handles both old format (list of records) and new format (dict with anomalies key).

    Args:
        report_json_path: Path to final_anomaly_report.json

    Returns:
        Dictionary containing anomaly data

    Raises:
        FileNotFoundError: If report file not found
        json.JSONDecodeError: If report is not valid JSON
    """
    report_path = Path(report_json_path)

    if not report_path.exists():
        raise FileNotFoundError(f"Report file not found: {report_json_path}")

    try:
        with open(report_path, 'r') as f:
            data = json.load(f)
        logger.info(f"[PIPELINE] Loaded anomaly report from {report_json_path}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"[PIPELINE] Failed to parse JSON report: {e}")
        raise


def get_severity_from_record(record: Dict[str, Any]) -> str:
    """
    Determine severity from the anomaly's signal profile.

    The original ML pipeline produces ISO_Severity_0to1 as a normalized rank among
    flagged anomalies, which makes all anomaly scores appear "high" when viewed in
    isolation. For the application severity tier, prefer the signal count and the
    presence of multiple independent anomaly drivers rather than the raw normalized
    ISO score alone.
    """
    if "Severity" in record:
        severity = str(record.get("Severity", "")).upper()
        if severity in ["HIGH", "MEDIUM", "LOW"]:
            return severity

    signal_count = 0
    try:
        signal_count = int(record.get("ML_Anomaly_Signal_Count", 0) or 0)
    except (TypeError, ValueError):
        signal_count = 0

    triggered_signals = []
    for signal_key in [
        "ISO_Is_Anomaly",
        "Correlation_Anomaly",
        "Quantity_Supply_Anomaly",
        "Stat_Zscore_Anomaly",
        "Stat_IQR_Anomaly",
    ]:
        if bool(record.get(signal_key, False)):
            triggered_signals.append(signal_key)

    if signal_count >= 2 or len(triggered_signals) >= 2:
        return "HIGH"
    if signal_count == 1 or len(triggered_signals) == 1:
        return "MEDIUM"

    iso_severity = record.get("ISO_Severity_0to1")
    if iso_severity is not None:
        try:
            score = float(iso_severity)
            if score >= 0.8:
                return "HIGH"
            elif score >= 0.45:
                return "MEDIUM"
            else:
                return "LOW"
        except (ValueError, TypeError):
            pass

    return "MEDIUM"


def count_anomalies_by_severity(anomalies: list) -> Dict[str, int]:
    """
    Count anomalies by severity level.

    Args:
        anomalies: List of anomaly records

    Returns:
        Dictionary with counts for HIGH, MEDIUM, LOW
    """
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for record in anomalies:
        severity = get_severity_from_record(record)
        if severity in counts:
            counts[severity] += 1

    return counts
