import sys
import os
import json
import pandas as pd

import feature_engineering as fe
import isolation_forest as isf
import correlation_analysis as ca

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <input.csv>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    
    try:
        # Load the input dataset
        df = pd.read_csv(input_file)
    except Exception as e:
        print(f"Error reading {input_file}: {e}")
        sys.exit(1)
    
    # 1. Feature Engineering
    # This prepares the data (e.g. creating Provider_NPI_Frequency, missing checks, etc.)
    df = fe.run_feature_engineering(df)
    
    # 2. Isolation Forest (Machine Learning Anomaly Detection)
    # Computes ISO_Is_Anomaly, ISO_Raw_Score, ISO_Severity_0to1
    df = isf.run_isolation_forest(df)
    
    # 3. Correlation Analysis
    # Computes Correlation_Anomaly and Quantity_Supply_Anomaly
    df = ca.run_correlation_analysis(df)
    
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
            "ML_Is_Anomalous": is_anomalous
        }
        results.append(result)
    
    # Write to a JSON file or print to stdout
    output_path = "final_anomaly_report.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"\nPipeline complete! Output written to {output_path}")
    print(f"Total Records processed: {len(results)}")
    
if __name__ == "__main__":
    main()
