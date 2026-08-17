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


def run_pipeline(input_file: str, output_dir: str | None = None) -> str:
    """
    Run the complete ML anomaly detection pipeline.
    
    Args:
        input_file: Path to input CSV or Excel file
        output_dir: Optional custom output directory (defaults to log/)
    
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
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    if output_dir is None:
        output_dir = str(repo_root / "log")
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load the input dataset (support CSV and Excel)
    try:
        if str(input_path).lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(input_path)
        else:
            df = pd.read_csv(input_path)
    except Exception as e:
        raise Exception(f"Error reading {input_file}: {e}")

    # 1. Feature Engineering
    # This prepares the data (e.g. creating Provider_NPI_Frequency, missing checks, etc.)
    df = fe.run_feature_engineering(df)

    # 2. Statistical Detection (Z-score + IQR)
    df = sd.run_statistical_detection(df)

    # 3. Isolation Forest (Machine Learning Anomaly Detection)
    # Computes ISO_Is_Anomaly, ISO_Raw_Score, ISO_Severity_0to1
    df = isf.run_isolation_forest(df)

    # 4. Correlation Analysis
    # Computes Correlation_Anomaly and Quantity_Supply_Anomaly
    df = ca.run_correlation_analysis(df)

    # 5. Data Quality checks (profiles, rule engine, scoring)
    try:
        profile = dq.generate_profile(df, output_path=str(output_path / "data_profile.json"))
        rule_results = dq.run_quality_checks(df, dq.RULES)
        quality_report = dq.calculate_scores_and_risk(rule_results, df, output_dir=str(output_path))
    except Exception as e:
        import traceback
        print("Data quality step failed:")
        traceback.print_exc()

    # 6. SLA / classification (run sla_monitoring after data-quality outputs are written)
    try:
        import importlib
        sla = importlib.import_module("sla_monitoring")
    except Exception as e:
        print(f"SLA classification step skipped: {e}")
    
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
        
        signal_count = sum([iso_anomaly, corr_anomaly, qs_anomaly])
        is_anomalous = signal_count > 0
        
        stat_anomaly = bool(row.get("Stat_Is_Anomalous", False))
        stat_fields = row.get("Stat_Anomaly_Fields", [])
        has_stat_fields = bool(stat_fields) and (len(stat_fields) > 0 if isinstance(stat_fields, (list, tuple)) else str(stat_fields) not in ("", "nan", "[]"))
        
        if stat_anomaly and has_stat_fields:
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
        
        result = {
            "Record_ID": str(row.get("Record_ID", "")),
            "Record_Type": str(row.get("Record_Type", "")),
            "BENE_ID": str(row.get("BENE_ID", "")),
            "Provider_NPI": str(row.get("Provider_NPI", "")),
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
            "primary_signal": primary_signal
        }
        results.append(result)
    
    # Write to a JSON file under `log/final_anomaly_report.json` (required by RCA agent)
    report_file = output_path / "final_anomaly_report.json"
    with open(report_file, "w") as f:
        json.dump(results, f, indent=2)

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