import sys
import os
import json
import pandas as pd
from pathlib import Path

# Add ML directory to path for imports
_ml_dir = str(Path(__file__).resolve().parent)
if _ml_dir not in sys.path:
    sys.path.insert(0, _ml_dir)

import feature_engineering as fe
import isolation_forest as isf
import correlation_analysis as ca
import statistical_detection as sd
import data_quality as dq
import sla_temporal_monitoring as sla_mon


def run_pipeline(
    input_file: str,
    output_dir: str | None = None,
    run_id: str | None = None,
    dataset_id: str | None = None,
) -> str:
    """
    Run the complete ML anomaly detection pipeline on ONLY the uploaded dataset.
    
    Args:
        input_file: Path to input CSV or Excel file
        output_dir: Optional custom output directory (defaults to log/)
        run_id: Optional Run ID (e.g. RUN-YYYYMMDD-XXXX)
        dataset_id: Optional Dataset ID (e.g. DS-YYYYMMDD-XXXX)
    
    Returns:
        Path to the generated final_anomaly_report.json
    
    Raises:
        FileNotFoundError: If input file does not exist
        Exception: If pipeline processing fails
    """
    # Resolve file paths
    repo_root = Path(__file__).resolve().parent.parent
    input_path = Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Uploaded dataset is not available for this run: {input_file}")
    
    if output_dir is None:
        output_dir = str(repo_root / "log")
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load ONLY the uploaded dataset (support CSV and Excel)
    try:
        if str(input_path).lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(input_path)
        else:
            df = pd.read_csv(input_path)
    except Exception as e:
        raise Exception(f"Error reading uploaded dataset {input_file}: {e}")

    input_rows = len(df)
    r_id = run_id or "RUN-DEFAULT"
    d_id = dataset_id or "DS-DEFAULT"

    print("\n" + "=" * 60)
    print(f"[PIPELINE]")
    print(f"Run ID: {r_id}")
    print(f"Dataset ID: {d_id}")
    print(f"Filename: {input_path.name}")
    print(f"Input rows: {input_rows}")
    print("=" * 60)

    # 1. Feature Engineering (Only on uploaded df)
    df = fe.run_feature_engineering(df)
    if len(df) != input_rows:
        print(f"[ERROR] Row count changed in Feature Engineering: {len(df)} != {input_rows}")
    print(f"[FEATURE ENGINEERING] rows={len(df)}")

    # 2. Statistical Detection (Z-score + IQR)
    df = sd.run_statistical_detection(df)
    if len(df) != input_rows:
        print(f"[ERROR] Row count changed in Statistical Detection: {len(df)} != {input_rows}")

    # 3. Isolation Forest (Machine Learning Anomaly Detection)
    df = isf.run_isolation_forest(df)
    if len(df) != input_rows:
        print(f"[ERROR] Row count changed in Isolation Forest: {len(df)} != {input_rows}")

    # 4. Correlation Analysis
    df = ca.run_correlation_analysis(df)
    if len(df) != input_rows:
        print(f"[ERROR] Row count changed in Correlation Analysis: {len(df)} != {input_rows}")
    print(f"[ANOMALY DETECTION] rows={len(df)}")

    # 5. Data Quality checks (Only on uploaded df)
    try:
        profile = dq.generate_profile(df, output_path=str(output_path / "data_profile.json"))
        rule_results = dq.run_quality_checks(df, dq.RULES)
        quality_report = dq.calculate_scores_and_risk(rule_results, df, output_dir=str(output_path))
        print(f"[DATA QUALITY] rows={len(df)}")
    except Exception as e:
        import traceback
        print("Data quality step failed:")
        traceback.print_exc()

    # 6. SLA / Temporal Monitoring (Only on uploaded df)
    sla_output = None
    try:
        sla_output = sla_mon.run_sla_monitoring(
            df,
            config_overrides={"output_dir": str(output_path)},
        )
        print(f"[SLA ENGINE] rows={len(df)}")
    except Exception as e:
        import traceback
        print("SLA / Temporal Monitoring step failed:")
        traceback.print_exc()
    
    # Build record-level SLA lookup from the existing SLA output
    sla_record_map = {}
    if isinstance(sla_output, dict) and "record_level_findings" in sla_output and isinstance(sla_output["record_level_findings"], list):
        for rf in sla_output["record_level_findings"]:
            if isinstance(rf, dict) and "record_id" in rf:
                sla_record_map[str(rf["record_id"]).strip().upper()] = rf
    
    # Extract the requested output JSON format for each record
    results = []
    
    for idx, row in df.iterrows():
        # Handle nan values gracefully
        def safe_float(val):
            if pd.isna(val):
                return None
            return float(val)
        
        iso_anomaly = bool(row.get("ISO_Is_Anomaly", False))
        corr_anomaly = bool(row.get("Correlation_Anomaly", False))
        qs_anomaly = bool(row.get("Quantity_Supply_Anomaly", False))
        stat_anomaly = bool(row.get("Stat_Is_Anomalous", False))
        stat_fields = row.get("Stat_Anomaly_Fields", [])
        has_stat_fields = bool(stat_fields) and (len(stat_fields) > 0 if isinstance(stat_fields, (list, tuple)) else str(stat_fields) not in ("", "nan", "[]"))
        is_stat_anomaly = stat_anomaly and has_stat_fields

        signal_count = sum([iso_anomaly, corr_anomaly, qs_anomaly, is_stat_anomaly])
        is_anomalous = signal_count > 0

        if is_stat_anomaly and corr_anomaly:
            anomaly_type = "Composite Anomaly"
            primary_signal = f"Statistical Outlier ({stat_fields}) & Correlation Anomaly"
        elif is_stat_anomaly and iso_anomaly:
            anomaly_type = "Composite Anomaly"
            primary_signal = f"Statistical Outlier ({stat_fields}) & Isolation Forest"
        elif is_stat_anomaly:
            anomaly_type = "Statistical Anomaly"
            primary_signal = stat_fields
        elif corr_anomaly:
            anomaly_type = "Correlation Anomaly"
            primary_signal = "Paid_Amount vs Allowed_Amount"
        elif qs_anomaly:
            anomaly_type = "Quantity/Supply Anomaly"
            primary_signal = "Quantity_Dispensed vs Days_Supply"
        elif iso_anomaly:
            anomaly_type = "Multivariate Anomaly"
            primary_signal = "Isolation Forest Multi-dimensional"
        else:
            anomaly_type = "Normal"
            primary_signal = "None"
        
        rec_id_str = str(row.get("Record_ID", ""))
        rec_id_clean = rec_id_str.strip().upper()
        sla_finding = sla_record_map.get(rec_id_clean, {})
        
        result = {
            "Record_ID": rec_id_str,
            "Record_Type": str(row.get("Record_Type", "")),
            "BENE_ID": str(row.get("BENE_ID", "")),
            "Provider_NPI": str(row.get("Provider_NPI", "")),
            "Billed_Amount": safe_float(row.get("Billed_Amount")),
            "Paid_Amount": safe_float(row.get("Paid_Amount")),
            "Allowed_Amount": safe_float(row.get("Allowed_Amount")),
            "Quantity_Dispensed": safe_float(row.get("Quantity_Dispensed")),
            "Days_Supply": safe_float(row.get("Days_Supply")),
            "Status": str(row.get("Status", "")),
            "Denial_Reason_Code": str(row.get("Denial_Reason_Code", "")),
            "Auth_Required_Flag": row.get("Auth_Required_Flag"),
            "Stat_Zscore_Anomaly": bool(row.get("Stat_Zscore_Anomaly", False)),
            "Stat_IQR_Anomaly": bool(row.get("Stat_IQR_Anomaly", False)),
            "Stat_Anomaly_Fields": row.get("Stat_Anomaly_Fields", []),
            "ISO_Is_Anomaly": iso_anomaly,
            "ISO_Raw_Score": safe_float(row.get("ISO_Raw_Score")),
            "ISO_Severity_0to1": safe_float(row.get("ISO_Severity_0to1")),
            "Correlation_Anomaly": corr_anomaly,
            "Correlation_Residual": safe_float(row.get("Correlation_Residual")),
            "Quantity_Supply_Anomaly": qs_anomaly,
            "Quantity_Supply_Residual": safe_float(row.get("Quantity_Supply_Residual")),
            "ML_Anomaly_Signal_Count": signal_count,
            "ML_Is_Anomalous": is_anomalous,
            "anomaly_type": anomaly_type,
            "primary_signal": primary_signal,
            # Propagate authoritative SLA output fields from SLA engine
            "SLA_Applicable": sla_finding.get("temporal_validity") != "NOT_ASSESSABLE" if sla_finding else True,
            "SLA_Target_Days": sla_finding.get("sla_target_days", safe_float(row.get("SLA_Target_Days"))),
            "Processing_Latency_Days": sla_finding.get("processing_latency_days", safe_float(row.get("Processing_Latency_Days"))),
            "SLA_Status": sla_finding.get("sla_status", sla_finding.get("status")),
            "Is_Breached": bool(sla_finding.get("is_breached", sla_finding.get("sla_breach") is True)),
            "Breach_Categories": sla_finding.get("breach_categories", []),
            "Breach_Reasons": sla_finding.get("breach_reasons", []),
            "SLA_Risk": sla_finding.get("sla_risk"),
            "SLA_Breach": sla_finding.get("sla_breach"),
            "SLA_Utilization": sla_finding.get("sla_utilization"),
            "Temporal_Validity": sla_finding.get("temporal_validity"),
            "SLA_Reason": sla_finding.get("reason"),
            "Record_SLA_Breach_Numeric": int(row.get("Record_SLA_Breach_Numeric", 1 if sla_finding.get("sla_breach") is True else 0)) if pd.notna(row.get("Record_SLA_Breach_Numeric")) else (1 if sla_finding.get("sla_breach") is True else 0),
        }
        results.append(result)
    
    # Write to a JSON file under `output_path / final_anomaly_report.json`
    report_file = output_path / "final_anomaly_report.json"
    with open(report_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"[RECOMMENDATION ENGINE] rows={len(results)}")
    print(f"\nML Pipeline complete! Output written to {report_file}")
    print(f"Total Records processed: {len(results)}")
    
    return str(report_file)


def main():
    # Default input file in Data/ if none provided
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    default_input = os.path.join(repo_root, "Data", "claims_pharmacy_auth_monitor_dataset_final.xlsx")

    if len(sys.argv) < 2:
        input_file = default_input
        print(f"No input provided. Using default: {input_file}")
    else:
        input_file = sys.argv[1]

    try:
        output_file = run_pipeline(input_file)
        print(f"Success: {output_file}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()