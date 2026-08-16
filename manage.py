#!/usr/bin/env python
"""
CLI for managing the Claims Pharmacy Auth Monitor pipeline.

Commands:
  ml-pipeline       Run ML anomaly detection pipeline
  rca               Run RCA (Root Cause Analysis) for a specific record
  vector-db-init    Initialize/rebuild vector knowledge base from workbook
  full-pipeline     Run complete pipeline end-to-end
  list-anomalies    List flagged anomalies from last ML run
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_ml_pipeline(input_file: str, output_dir: Optional[str] = None) -> str:
    """
    Run the ML anomaly detection pipeline.
    
    Args:
        input_file: Path to input CSV with claims data
        output_dir: Optional output directory (defaults to log/)
    
    Returns:
        Path to the generated final_anomaly_report.json
    """
    logger.info(f"Starting ML pipeline with input: {input_file}")
    
    if not Path(input_file).exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    try:
        from ML.main import run_pipeline
        result_path = run_pipeline(input_file, output_dir=output_dir)
        logger.info(f"ML pipeline completed. Report saved to: {result_path}")
        return result_path
    except Exception as e:
        logger.error(f"ML pipeline failed: {e}")
        raise


def init_vector_db() -> int:
    """
    Initialize or rebuild the vector knowledge base from the Excel workbook.
    
    Returns:
        0 if successful, non-zero otherwise
    """
    logger.info("Initializing vector knowledge base from workbook...")
    
    try:
        from UC10_Anomaly_Monitor.rca.vector_kb import ChromaCaseKB
        
        kb = ChromaCaseKB()
        count = kb.collection.count() if kb.collection is not None else 0
        
        logger.info(f"Vector KB initialized with {count} cases from: {kb.kb_path}")
        logger.info(f"Persist directory: {kb.persist_dir}")
        
        if count == 0:
            logger.warning("Vector KB is empty. Check workbook path and try again.")
            return 1
        
        return 0
    except Exception as e:
        logger.error(f"Failed to initialize vector DB: {e}")
        return 1


def run_rca(record_id: str, kb_path: Optional[str] = None) -> int:
    """
    Run RCA for a specific anomalous record.
    
    Args:
        record_id: The record ID (e.g., PH201432)
        kb_path: Optional custom path to knowledge base
    
    Returns:
        0 if successful, non-zero otherwise
    """
    logger.info(f"Running RCA for record: {record_id}")
    
    try:
        from UC10_Anomaly_Monitor import main as rca_main
        import sys as _sys
        
        old_argv = _sys.argv
        try:
            _sys.argv = ["manage.py", record_id]
            rca_main.main()
        finally:
            _sys.argv = old_argv
        
        log_dir = Path("log")
        rca_file = log_dir / f"rca_{record_id}.json"
        
        if rca_file.exists():
            logger.info(f"RCA report saved to: {rca_file}")
            with open(rca_file) as f:
                report = json.load(f)
            logger.info(f"Root Cause: {report.get('likely_root_cause', 'N/A')}")
            logger.info(f"Confidence: {report.get('confidence', 'N/A')}")
            return 0
        else:
            logger.warning(f"RCA report not found at {rca_file}")
            return 1
    except Exception as e:
        logger.error(f"RCA failed: {e}")
        return 1


def list_anomalies(report_path: Optional[str] = None, limit: int = 10) -> int:
    """
    List flagged anomalies from the latest ML report.
    
    Args:
        report_path: Optional custom path to report
        limit: Maximum number to display
    
    Returns:
        0 if successful, non-zero otherwise
    """
    if report_path is None:
        report_path = "log/final_anomaly_report.json"
    
    report_file = Path(report_path)
    if not report_file.exists():
        logger.error(f"Report not found: {report_path}. Run ml-pipeline first.")
        return 1
    
    try:
        with open(report_file) as f:
            report = json.load(f)
        
        if isinstance(report, list):
            anomalies = report
        else:
            anomalies = report.get("anomalies", [])
        
        flagged = [a for a in anomalies if a.get("ML_Is_Anomalous", False) or a.get("is_anomaly", False)]
        
        logger.info(f"Total records: {len(anomalies)}, Flagged anomalies: {len(flagged)}")
        logger.info(f"Showing first {min(limit, len(flagged))} anomalies:\n")
        
        for i, anom in enumerate(flagged[:limit], 1):
            record_id = anom.get("Record_ID", "N/A")
            record_type = anom.get("Record_Type", "N/A")
            severity = anom.get("ISO_Severity_0to1", 0.0)
            denial_reason = anom.get("Denial_Reason_Code", "N/A")
            print(f"{i}. {record_id} | Type: {record_type} | Severity: {severity:.2f} | Denial: {denial_reason}")
        
        return 0
    except Exception as e:
        logger.error(f"Failed to list anomalies: {e}")
        return 1


def run_full_pipeline(input_file: str, sample_records: Optional[int] = None) -> int:
    """
    Run the complete pipeline: ML detection -> Vector DB init -> RCA on flagged records.
    
    Args:
        input_file: Path to input CSV
        sample_records: Optional limit on how many records to run RCA for
    
    Returns:
        0 if successful, non-zero otherwise
    """
    logger.info("=" * 70)
    logger.info("STARTING FULL PIPELINE")
    logger.info("=" * 70)
    
    try:
        # Step 1: Run ML pipeline
        logger.info("\n[STEP 1] Running ML anomaly detection...")
        ml_report = run_ml_pipeline(input_file)
        
        # Step 2: Initialize vector DB
        logger.info("\n[STEP 2] Initializing vector knowledge base...")
        if init_vector_db() != 0:
            logger.warning("Vector DB init failed, continuing with fallback KB...")
        
        # Step 3: Run RCA on flagged anomalies
        logger.info("\n[STEP 3] Running RCA on flagged anomalies...")
        with open(ml_report) as f:
            report = json.load(f)
        
        if isinstance(report, list):
            anomalies = report
        else:
            anomalies = report.get("anomalies", [])
        
        flagged = [a for a in anomalies if a.get("ML_Is_Anomalous", False) or a.get("is_anomaly", False)]
        
        if not flagged:
            logger.info("No anomalies flagged. Pipeline complete.")
            return 0
        
        max_records = sample_records or len(flagged)
        records_to_process = flagged[:max_records]
        
        logger.info(f"Processing {len(records_to_process)} flagged records (out of {len(flagged)} total)...")
        
        results = []
        for idx, anom in enumerate(records_to_process, 1):
            record_id = anom.get("Record_ID", "N/A")
            logger.info(f"\n[{idx}/{len(records_to_process)}] Processing {record_id}...")
            
            try:
                run_rca(record_id)
                results.append((record_id, "SUCCESS"))
            except Exception as e:
                logger.warning(f"RCA for {record_id} failed: {e}")
                results.append((record_id, "FAILED"))
        
        # Step 4: Summary
        logger.info("\n" + "=" * 70)
        logger.info("PIPELINE SUMMARY")
        logger.info("=" * 70)
        logger.info(f"ML Pipeline: Complete")
        logger.info(f"Vector DB: Initialized with workbook KB")
        logger.info(f"RCA Results: {len([r for r in results if r[1] == 'SUCCESS'])}/{len(results)} successful")
        
        for record_id, status in results:
            logger.info(f"  {record_id}: {status}")
        
        logger.info("=" * 70)
        
        return 0
    except Exception as e:
        logger.error(f"Full pipeline failed: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Claims Pharmacy Auth Monitor Pipeline CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage.py ml-pipeline Data/sample_input.csv
  python manage.py rca PH201432
  python manage.py vector-db-init
  python manage.py list-anomalies
  python manage.py full-pipeline Data/sample_input.csv --sample-records 5
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # ML Pipeline command
    ml_parser = subparsers.add_parser("ml-pipeline", help="Run ML anomaly detection pipeline")
    ml_parser.add_argument("input_file", help="Path to input CSV file")
    ml_parser.add_argument("--output-dir", help="Optional output directory (default: log/)")
    
    # RCA command
    rca_parser = subparsers.add_parser("rca", help="Run RCA for a specific record")
    rca_parser.add_argument("record_id", help="Record ID to analyze (e.g., PH201432)")
    rca_parser.add_argument("--kb-path", help="Optional custom knowledge base path")
    
    # Vector DB Init command
    vdb_parser = subparsers.add_parser("vector-db-init", help="Initialize vector knowledge base")
    
    # List Anomalies command
    list_parser = subparsers.add_parser("list-anomalies", help="List flagged anomalies")
    list_parser.add_argument("--report", help="Optional custom report path")
    list_parser.add_argument("--limit", type=int, default=10, help="Max anomalies to display")
    
    # Full Pipeline command
    full_parser = subparsers.add_parser("full-pipeline", help="Run complete end-to-end pipeline")
    full_parser.add_argument("input_file", help="Path to input CSV file")
    full_parser.add_argument("--sample-records", type=int, help="Optional limit on RCA records")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Execute command
    if args.command == "ml-pipeline":
        try:
            run_ml_pipeline(args.input_file, output_dir=args.output_dir)
            return 0
        except Exception as e:
            logger.error(str(e))
            return 1
    
    elif args.command == "rca":
        return run_rca(args.record_id, kb_path=args.kb_path)
    
    elif args.command == "vector-db-init":
        return init_vector_db()
    
    elif args.command == "list-anomalies":
        return list_anomalies(report_path=args.report, limit=args.limit)
    
    elif args.command == "full-pipeline":
        return run_full_pipeline(args.input_file, sample_records=args.sample_records)
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
