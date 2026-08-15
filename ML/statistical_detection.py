def run_statistical_detection(df):
    # ============================================================
    # MODULE 1: Statistical Detection (Z-score + IQR)
    # Runs after the Feature Engineering cell - uses `df` already
    # in memory. No files to upload.
    #
    # Applies Z-score and IQR outlier detection to key numeric
    # fields, computed WITHIN each Record_Type group (medical claims,
    # pharmacy claims, and prior auths have very different scales -
    # mixing them would make legitimate pharmacy amounts look like
    # outliers next to medical claim amounts, and vice versa).
    # ============================================================
    
    import pandas as pd
    import numpy as np
    import json
    import os
    
    OUTPUT_DIR = "outputs"
    OUTPUT_PATH = f"{OUTPUT_DIR}/statistical_findings.json"
    
    # Fields checked per record type (only fields that apply to that type)
    FIELDS_BY_TYPE = {
        "MEDICAL_CLAIM":   ["Billed_Amount", "Allowed_Amount", "Paid_Amount",
                             "Patient_Responsibility", "Processing_Latency_Days"],
        "PHARMACY_CLAIM":  ["Billed_Amount", "Allowed_Amount", "Paid_Amount",
                             "Patient_Responsibility", "Days_Supply",
                             "Quantity_Dispensed", "Processing_Latency_Days"],
        "PRIOR_AUTH":      ["Processing_Latency_Days"],
    }
    
    Z_THRESHOLD = 3.0
    IQR_MULTIPLIER = 1.5
    
    df["Stat_Zscore_Anomaly"] = False
    df["Stat_IQR_Anomaly"] = False
    df["Stat_Anomaly_Fields"] = [[] for _ in range(len(df))]
    
    field_level_results = []
    
    for rtype, fields in FIELDS_BY_TYPE.items():
        type_mask = df["Record_Type"] == rtype
        subset = df.loc[type_mask]
    
        for field in fields:
            if field not in df.columns:
                continue
    
            values = subset[field]
            valid = values.dropna()
            if len(valid) < 10:
                continue  # not enough data to compute a meaningful baseline
    
            # ---- Z-score ----
            mean = valid.mean()
            std = valid.std()
            if std > 0:
                z_scores = (values - mean) / std
                z_flag = z_scores.abs() > Z_THRESHOLD
            else:
                z_flag = pd.Series(False, index=values.index)
    
            # ---- IQR ----
            q1, q3 = valid.quantile(0.25), valid.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - IQR_MULTIPLIER * iqr
            upper = q3 + IQR_MULTIPLIER * iqr
            if iqr > 0:
                iqr_flag = (values < lower) | (values > upper)
            else:
                iqr_flag = pd.Series(False, index=values.index)
    
            z_flag = z_flag.fillna(False)
            iqr_flag = iqr_flag.fillna(False)
    
            df.loc[type_mask, "Stat_Zscore_Anomaly"] |= z_flag
            df.loc[type_mask, "Stat_IQR_Anomaly"] |= iqr_flag
    
            combined_flag = z_flag | iqr_flag
            for idx in values.index[combined_flag]:
                df.at[idx, "Stat_Anomaly_Fields"] = df.at[idx, "Stat_Anomaly_Fields"] + [field]
    
            field_level_results.append({
                "record_type": rtype,
                "field": field,
                "mean": round(float(mean), 2),
                "std": round(float(std), 2),
                "iqr_lower_bound": round(float(lower), 2),
                "iqr_upper_bound": round(float(upper), 2),
                "zscore_flagged": int(z_flag.sum()),
                "iqr_flagged": int(iqr_flag.sum()),
                "combined_flagged": int(combined_flag.sum()),
            })
    
    df["Stat_Is_Anomalous"] = df["Stat_Zscore_Anomaly"] | df["Stat_IQR_Anomaly"]
    
    print(f"Z-score anomalies : {df['Stat_Zscore_Anomaly'].sum():,}")
    print(f"IQR anomalies     : {df['Stat_IQR_Anomaly'].sum():,}")
    print(f"Combined (either) : {df['Stat_Is_Anomalous'].sum():,} / {len(df):,} "
          f"({100*df['Stat_Is_Anomalous'].mean():.2f}%)")
    
    print("\nPer-field breakdown:")
    for r in field_level_results:
        print(f"  [{r['record_type']:<15}] {r['field']:<25} "
              f"z={r['zscore_flagged']:>4}  iqr={r['iqr_flagged']:>4}  combined={r['combined_flagged']:>4}")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    findings = {
        "method": "Z-score (threshold=3.0) and IQR (multiplier=1.5), computed within each Record_Type group",
        "summary": {
            "zscore_anomalies": int(df["Stat_Zscore_Anomaly"].sum()),
            "iqr_anomalies": int(df["Stat_IQR_Anomaly"].sum()),
            "combined_anomalies": int(df["Stat_Is_Anomalous"].sum()),
            "combined_anomalies_pct": round(100 * df["Stat_Is_Anomalous"].mean(), 2),
        },
        "field_level_results": field_level_results,
    }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(findings, f, indent=2, default=str)
    
    print(f"\nSaved: {OUTPUT_PATH}")
    return df
