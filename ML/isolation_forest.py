def run_isolation_forest(df):
    # ==============================================================================
    # MODULE: Domain-Aware Isolation Forest Anomaly Detection Pipeline
    # Assumes `df` is already present in memory.
    # ==============================================================================
    
    import json
    import os
    import numpy as np
    import pandas as pd
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import IsolationForest
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    
    OUTPUT_DIR = "outputs"
    OUTPUT_PATH = os.path.join(OUTPUT_DIR, "ml_isolation_forest_findings.json")
    
    # ------------------------------------------------------------------------------
    # STEP 0: Data Sanitization & Type Normalization
    # ------------------------------------------------------------------------------
    # Normalize key identifiers to strings (preserve alphanumeric IDs and leading zeros)
    id_cols = ["Record_ID", "BENE_ID", "Provider_NPI", "Auth_Linked_ID"]
    for col in id_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).replace({"nan": np.nan, "None": np.nan})
    
    # Parse timestamp/date fields into proper datetime dtype
    date_cols = [
        "Service_Date",
        "Service_End_Date",
        "Processed_Date",
        "Decision_Date",
        "Submission_Date",
    ]
    for col in date_cols:
        if col in df.columns and not pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col], errors="coerce")
    
    print(f"Loaded DataFrame: {len(df):,} rows x {len(df.columns)} columns")
    
    # ------------------------------------------------------------------------------
    # STEP 1: Feature Engineering (Contextual & Domain-Aware)
    # ------------------------------------------------------------------------------
    X = df.copy()
    
    # Latency and Duration Metrics
    if "Processing_Latency_Days" in X.columns:
        X["Days_To_Process"] = X["Processing_Latency_Days"]
    elif "Processed_Date" in X.columns and "Submission_Date" in X.columns:
        X["Days_To_Process"] = (X["Processed_Date"] - X["Submission_Date"]).dt.days
    else:
        X["Days_To_Process"] = np.nan
    
    if "Decision_Date" in X.columns and "Processed_Date" in X.columns:
        X["Decision_Latency_Days"] = (
            X["Decision_Date"] - X["Processed_Date"]
        ).dt.days.fillna(0)
    else:
        X["Decision_Latency_Days"] = 0
    
    if "Service_End_Date" in X.columns and "Service_Date" in X.columns:
        X["Service_Duration_Days"] = (
            X["Service_End_Date"] - X["Service_Date"]
        ).dt.days
    else:
        X["Service_Duration_Days"] = np.nan
    
    # Financial Ratios (Replacing 0 denominators with NaN to avoid division-by-zero errors)
    billed = (
        X["Billed_Amount"].replace(0, np.nan)
        if "Billed_Amount" in X.columns
        else np.nan
    )
    allowed = (
        X["Allowed_Amount"].replace(0, np.nan)
        if "Allowed_Amount" in X.columns
        else np.nan
    )
    paid = X["Paid_Amount"] if "Paid_Amount" in X.columns else np.nan
    
    X["Paid_to_Billed_Ratio"] = (
        paid / billed if isinstance(paid, pd.Series) else np.nan
    )
    X["Allowed_to_Billed_Ratio"] = (
        allowed / billed if isinstance(allowed, pd.Series) else np.nan
    )
    X["Paid_to_Allowed_Ratio"] = (
        paid / allowed if isinstance(paid, pd.Series) else np.nan
    )
    
    # Operational Flags and Overruns
    if (
        "Processing_Latency_Days" in X.columns
        and "SLA_Target_Days" in X.columns
    ):
        X["SLA_Overrun_Days"] = (
            X["Processing_Latency_Days"] - X["SLA_Target_Days"]
        )
    else:
        X["SLA_Overrun_Days"] = 0
    
    if "Status" in X.columns:
        X["Is_Denied_Or_Rejected"] = (
            X["Status"].isin(["DENIED", "REJECTED"]).astype(int)
        )
    else:
        X["Is_Denied_Or_Rejected"] = 0
    
    if "Retry_Count" in X.columns:
        X["Retry_Count_Bucket"] = (
            pd.cut(
                X["Retry_Count"].fillna(0),
                bins=[-np.inf, 0, 2, np.inf],
                labels=[0, 1, 2],
            )
            .astype(float)
            .fillna(0)
        )
    else:
        X["Retry_Count_Bucket"] = 0.0
    
    # Logical Business Missingness: Requires authorization but none is linked
    auth_req = (
        X["Auth_Required_Flag"].fillna("N")
        if "Auth_Required_Flag" in X.columns
        else pd.Series("N", index=X.index)
    )
    rec_type = (
        X["Record_Type"].fillna("")
        if "Record_Type" in X.columns
        else pd.Series("", index=X.index)
    )
    auth_id = (
        X["Auth_Linked_ID"]
        if "Auth_Linked_ID" in X.columns
        else pd.Series(np.nan, index=X.index)
    )
    
    X["Unexpected_Missing_Count"] = (
        (auth_req == "Y") & (rec_type != "PRIOR_AUTH") & (auth_id.isna())
    ).astype(int)
    
    # String-Safe Frequency Encodings (Preserves alphanumeric format without float coercion)
    freq_targets = [
        ("Provider_NPI", "Provider_NPI_Frequency"),
        ("BENE_ID", "BENE_ID_Frequency"),
        ("Diagnosis_Code", "Diagnosis_Code_Frequency"),
        ("NDC_Code", "NDC_Code_Frequency"),
        ("Drug_Name", "Drug_Name_Frequency"),
    ]
    
    for col, new_col in freq_targets:
        if col in X.columns:
            counts = X[col].dropna().value_counts()
            X[new_col] = X[col].map(counts).fillna(0)
        else:
            X[new_col] = 0
    
    # ------------------------------------------------------------------------------
    # STEP 2: Domain-Specific Partitioning & Feature Definition
    # ------------------------------------------------------------------------------
    DOMAIN_CONFIGS = {
        "MEDICAL_CLAIM": {
            "numeric": [
                "Billed_Amount",
                "Allowed_Amount",
                "Paid_Amount",
                "Patient_Responsibility",
                "Processing_Latency_Days",
                "Days_To_Process",
                "Decision_Latency_Days",
                "Service_Duration_Days",
                "Paid_to_Billed_Ratio",
                "Allowed_to_Billed_Ratio",
                "Paid_to_Allowed_Ratio",
                "SLA_Overrun_Days",
                "Is_Denied_Or_Rejected",
                "Retry_Count_Bucket",
                "Unexpected_Missing_Count",
                "Provider_NPI_Frequency",
                "BENE_ID_Frequency",
                "Diagnosis_Code_Frequency",
            ],
            "categorical": [
                "Provider_State",
                "Status",
                "Denial_Reason_Code",
                "Procedure_Code",
                "Source_System",
                "SLA_Breach_Flag",
                "Urgency_Flag",
                "Auth_Required_Flag",
            ],
        },
        "PHARMACY_CLAIM": {
            "numeric": [
                "Billed_Amount",
                "Allowed_Amount",
                "Paid_Amount",
                "Patient_Responsibility",
                "Days_Supply",
                "Quantity_Dispensed",
                "Processing_Latency_Days",
                "Days_To_Process",
                "Decision_Latency_Days",
                "Paid_to_Billed_Ratio",
                "Allowed_to_Billed_Ratio",
                "Paid_to_Allowed_Ratio",
                "SLA_Overrun_Days",
                "Is_Denied_Or_Rejected",
                "Retry_Count_Bucket",
                "Unexpected_Missing_Count",
                "Provider_NPI_Frequency",
                "BENE_ID_Frequency",
                "NDC_Code_Frequency",
                "Drug_Name_Frequency",
            ],
            "categorical": [
                "Provider_State",
                "Status",
                "Denial_Reason_Code",
                "Source_System",
                "SLA_Breach_Flag",
                "Urgency_Flag",
                "Auth_Required_Flag",
            ],
        },
        "PRIOR_AUTH": {
            "numeric": [
                "Processing_Latency_Days",
                "Days_To_Process",
                "Decision_Latency_Days",
                "Service_Duration_Days",
                "SLA_Overrun_Days",
                "Is_Denied_Or_Rejected",
                "Retry_Count_Bucket",
                "Provider_NPI_Frequency",
                "BENE_ID_Frequency",
                "Diagnosis_Code_Frequency",
            ],
            "categorical": [
                "Provider_State",
                "Status",
                "Denial_Reason_Code",
                "Procedure_Code",
                "Source_System",
                "SLA_Breach_Flag",
                "Urgency_Flag",
            ],
        },
    }
    
    # ------------------------------------------------------------------------------
    # STEP 3: Model Training per Domain
    # ------------------------------------------------------------------------------
    # Initialize output target fields
    df["ISO_Is_Anomaly"] = False
    df["ISO_Raw_Score"] = np.nan
    df["ISO_Severity_0to1"] = np.nan
    
    fitted_feature_counts = {}
    
    # Ensure Record_Type exists, default to ALL if missing
    if "Record_Type" not in df.columns:
        df["Record_Type"] = "MEDICAL_CLAIM"
    
    for domain_type, cfg in DOMAIN_CONFIGS.items():
        mask = df["Record_Type"] == domain_type
        subset_indices = df[mask].index
    
        if len(subset_indices) == 0:
            continue
    
        # Filter features available in the current dataset
        num_feats = [f for f in cfg["numeric"] if f in X.columns]
        cat_feats = [f for f in cfg["categorical"] if f in X.columns]
    
        # Preprocessing Pipeline
        # Using max_categories to prevent dimensionality explosion on high-cardinality codes
        preprocessor = ColumnTransformer(
            transformers=[
                (
                    "num",
                    Pipeline(
                        steps=[
                            (
                                "imputer",
                                SimpleImputer(strategy="median"),
                            ),
                            ("scaler", StandardScaler()),
                        ]
                    ),
                    num_feats,
                ),
                (
                    "cat",
                    Pipeline(
                        steps=[
                            (
                                "imputer",
                                SimpleImputer(
                                    strategy="most_frequent"
                                ),
                            ),
                            (
                                "encoder",
                                OneHotEncoder(
                                    handle_unknown="ignore",
                                    sparse_output=False,
                                    max_categories=30,
                                ),
                            ),
                        ]
                    ),
                    cat_feats,
                ),
            ]
        )
    
        domain_input = X.loc[subset_indices, num_feats + cat_feats]
        X_proc = preprocessor.fit_transform(domain_input)
        fitted_feature_counts[domain_type] = int(X_proc.shape[1])
    
        # Model instantiation with reproducibility and domain sensitivity
        iso = IsolationForest(
            n_estimators=200,
            contamination="auto",
            random_state=42,
            n_jobs=-1,
        )
        iso.fit(X_proc)
    
        # Scikit-learn outputs: -1 = Anomaly, 1 = Normal
        preds = iso.predict(X_proc)
        raw_scores = iso.decision_function(X_proc)
    
        # Convert raw score to standardized 0-1 severity (lower score = higher severity)
        score_min, score_max = raw_scores.min(), raw_scores.max()
        denom = (score_max - score_min) if (score_max - score_min) != 0 else 1e-9
        severity = np.clip((score_max - raw_scores) / denom, 0.0, 1.0)
    
        # Assign domain outputs back to main DataFrame
        df.loc[subset_indices, "ISO_Is_Anomaly"] = preds == -1
        df.loc[subset_indices, "ISO_Raw_Score"] = raw_scores
        df.loc[subset_indices, "ISO_Severity_0to1"] = severity
    
        print(
            f"Domain [{domain_type:<15}] Transformed Features: {X_proc.shape[1]:>3} | "
            f"Rows: {len(subset_indices):>6,} | Flagged Anomalies: {(preds == -1).sum():>5,} "
            f"({100 * (preds == -1).mean():.2f}%)"
        )
    
    # ------------------------------------------------------------------------------
    # STEP 4: Output Serialization & Artifact Generation
    # ------------------------------------------------------------------------------
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    export_cols = [
        "Record_ID",
        "Record_Type",
        "BENE_ID",
        "Provider_NPI",
        "ISO_Is_Anomaly",
        "ISO_Raw_Score",
        "ISO_Severity_0to1",
    ]
    available_export_cols = [c for c in export_cols if c in df.columns]
    
    # Extract top 20 records with the highest anomaly severity score
    top_20_anomalies = (
        df.sort_values("ISO_Severity_0to1", ascending=False)
        .head(20)[available_export_cols]
        .fillna("")
        .to_dict(orient="records")
    )
    
    total_records = len(df)
    flagged_count = int(df["ISO_Is_Anomaly"].sum())
    flagged_pct = round(100 * (flagged_count / max(total_records, 1)), 2)
    
    findings = {
        "method": (
            "Domain-Partitioned IsolationForest(n_estimators=200, contamination='auto', random_state=42) "
            "with median/most-frequent imputation, standard scaling, and one-hot encoding (max_categories=30)."
        ),
        "features_per_domain": fitted_feature_counts,
        "summary": {
            "total_records_scanned": total_records,
            "isolation_forest_flagged_count": flagged_count,
            "isolation_forest_flagged_pct": flagged_pct,
        },
        "top_20_highest_severity_records": top_20_anomalies,
    }
    
    with open(OUTPUT_PATH, "w") as f:
        json.dump(findings, f, indent=2, default=str)
    
    print(f"\nSuccessfully generated outputs at: {OUTPUT_PATH}")
    print(f"Total Anomalies Flagged: {flagged_count:,} / {total_records:,} ({flagged_pct}%)")
    return df
