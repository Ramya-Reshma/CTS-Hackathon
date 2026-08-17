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


def normalize_data_types(input_file_path: str, output_file_path: str) -> str:
    """
    Normalize data types in the input file to prevent encoder errors.
    
    This preprocesses the file to ensure:
    - Boolean columns are converted to strings (e.g., True -> 'True')
    - All object columns are properly stringified
    - This avoids "mixed bool/str" encoder errors
    
    Args:
        input_file_path: Path to original input file
        output_file_path: Path where normalized file will be saved
    
    Returns:
        Path to normalized file
    """
    import pandas as pd
    
    input_path = Path(input_file_path)
    
    try:
        # Read the file
        if str(input_path).lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(input_path)
        else:
            df = pd.read_csv(input_path)
        
        # Convert boolean columns to strings to avoid mixed type issues
        for col in df.columns:
            # Check explicit boolean dtype
            if df[col].dtype == 'bool':
                df[col] = df[col].astype(str)
            # Check object columns for any boolean values (check ALL rows, not just head)
            elif df[col].dtype == 'object':
                # Check if column contains ANY boolean values in the entire column
                has_bool = any(isinstance(x, bool) for x in df[col].dropna())
                if has_bool:
                    # Convert all values to strings
                    df[col] = df[col].astype(str)
        
        # Save normalized file
        if str(output_file_path).lower().endswith('.xlsx'):
            df.to_excel(output_file_path, index=False)
        else:
            df.to_csv(output_file_path, index=False)
        
        logger.info(f"[PIPELINE] Data types normalized: {output_file_path}")
        return output_file_path
        
    except Exception as e:
        logger.error(f"[PIPELINE] Data normalization failed: {str(e)}")
        # If normalization fails, return original file and let pipeline handle it
        return input_file_path


def run_existing_pipeline(input_file_path: str, output_dir: str = None) -> Tuple[str, Dict[str, Any]]:
    """
    Call the EXISTING UC10 anomaly detection pipeline.

    This function:
    1. Validates the input file
    2. Calls ML.main.run_pipeline (the existing pipeline)
    3. Returns the path to final_anomaly_report.json and metadata

    Args:
        input_file_path: Path to uploaded CSV/XLSX/XLS file
        output_dir: Optional custom output directory

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
        raise FileNotFoundError(f"Input file not found: {input_file_path}")

    # Validate file extension
    valid_extensions = {'.csv', '.xls', '.xlsx'}
    if input_path.suffix.lower() not in valid_extensions:
        raise ValueError(
            f"Invalid file format: {input_path.suffix}. "
            f"Supported formats: {', '.join(valid_extensions)}"
        )

    # Set output directory to log/ if not specified
    if output_dir is None:
        repo_root = Path(__file__).resolve().parents[2]
        output_dir = str(repo_root / "log")

    try:
        logger.info(f"[PIPELINE] Starting existing UC10 pipeline with input: {input_file_path}")
        logger.info(f"[PIPELINE] Output directory: {output_dir}")

        # Normalize data types to avoid encoder errors (bool/str mixed types)
        # This preprocesses the file but does NOT change the ML pipeline logic
        temp_dir = tempfile.mkdtemp(prefix="uc10_normalized_")
        normalized_file_path = Path(temp_dir) / input_path.name
        normalized_file_path = normalize_data_types(
            input_file_path, 
            str(normalized_file_path)
        )

        # Import and call the EXISTING pipeline (ML.main.run_pipeline)
        # This is the ONLY modification: we're calling the existing function
        from ML.main import run_pipeline

        # Call the EXISTING pipeline with normalized data (still same logic)
        report_json_path = run_pipeline(normalized_file_path, output_dir=output_dir)

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
    Extract severity from an anomaly record.

    Handles both old format (numeric scores) and new format (Severity field).

    Args:
        record: Anomaly record from pipeline output

    Returns:
        Severity string: "HIGH", "MEDIUM", or "LOW"
    """
    # Check for Severity field (new synthesis format)
    if "Severity" in record:
        severity = str(record.get("Severity", "")).upper()
        if severity in ["HIGH", "MEDIUM", "LOW"]:
            return severity

    # Check for ISO_Severity_0to1 (old ML format)
    iso_severity = record.get("ISO_Severity_0to1")
    if iso_severity is not None:
        try:
            score = float(iso_severity)
            # Map 0-1 score to HIGH/MEDIUM/LOW
            if score >= 0.7:
                return "HIGH"
            elif score >= 0.4:
                return "MEDIUM"
            else:
                return "LOW"
        except (ValueError, TypeError):
            pass

    # Default to MEDIUM if cannot determine
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
