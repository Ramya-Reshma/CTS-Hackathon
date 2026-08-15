def run_correlation_analysis(df):
    # ============================================================
    # MODULE 3: Correlation & Relationship Analysis
    # Runs after Module 2 in the same Colab session - uses `df`
    # already in memory. Trains fresh, no files to upload.
    #
    # Checks whether known business relationships between fields
    # still hold for each record. Unlike Module 1 (single-field
    # outliers) or Module 2 (overall multivariate strangeness), this
    # catches records where two RELATED fields disagree with each
    # other - e.g. a paid amount that doesn't track the allowed
    # amount the way it should, or a drug quantity that doesn't
    # match the days-supply it was dispensed for.
    # ============================================================
    
    import pandas as pd
    import numpy as np
    import json
    import os
    
    from sklearn.linear_model import LinearRegression
    
    OUTPUT_DIR = "outputs"
    OUTPUT_PATH = f"{OUTPUT_DIR}/correlation_findings.json"
    
    RESIDUAL_SIGMA_THRESHOLD = 3.0
    
    # ------------------------------------------------------------
    # RELATIONSHIP 1: Paid_Amount ~ Allowed_Amount
    # Business expectation: paid amount should track the allowed
    # amount closely (a plan pays close to, but usually at or below,
    # what it allowed). A record that breaks this pattern signals a
    # pricing/adjudication error or a manual override.
    # ------------------------------------------------------------
    corr_mask = df["Allowed_Amount"].notna() & df["Paid_Amount"].notna()
    
    correlation_model = LinearRegression()
    correlation_model.fit(df.loc[corr_mask, ["Allowed_Amount"]], df.loc[corr_mask, "Paid_Amount"])
    
    pearson_r = df.loc[corr_mask, "Allowed_Amount"].corr(df.loc[corr_mask, "Paid_Amount"])
    
    df["Correlation_Predicted_Paid"] = np.nan
    df["Correlation_Residual"] = np.nan
    df["Correlation_Anomaly"] = False
    
    pred_paid = correlation_model.predict(df.loc[corr_mask, ["Allowed_Amount"]])
    residual = df.loc[corr_mask, "Paid_Amount"].values - pred_paid
    resid_std = residual.std()
    
    df.loc[corr_mask, "Correlation_Predicted_Paid"] = pred_paid
    df.loc[corr_mask, "Correlation_Residual"] = residual
    df.loc[corr_mask, "Correlation_Anomaly"] = np.abs(residual) > RESIDUAL_SIGMA_THRESHOLD * resid_std
    
    print("RELATIONSHIP 1: Paid_Amount ~ Allowed_Amount")
    print(f"  Pearson r              : {pearson_r:.4f}")
    print(f"  Fitted line             : Paid = {correlation_model.coef_[0]:.4f} * Allowed + {correlation_model.intercept_:.4f}")
    print(f"  Residual std             : {resid_std:.2f}")
    print(f"  Anomalies (|resid|>{RESIDUAL_SIGMA_THRESHOLD}sd): {df['Correlation_Anomaly'].sum():,}")
    
    # ------------------------------------------------------------
    # RELATIONSHIP 2: Quantity_Dispensed ~ Days_Supply
    # Business expectation: the quantity dispensed should scale
    # consistently with the days-supply prescribed (pharmacy claims
    # only). A record that breaks this pattern signals a dispensing
    # error or a mismatched drug/quantity/days-supply entry.
    # ------------------------------------------------------------
    qty_mask = (df["Record_Type"] == "PHARMACY_CLAIM") & df["Days_Supply"].notna() & df["Quantity_Dispensed"].notna()
    
    quantity_supply_model = LinearRegression()
    quantity_supply_model.fit(df.loc[qty_mask, ["Days_Supply"]], df.loc[qty_mask, "Quantity_Dispensed"])
    
    qty_pearson_r = df.loc[qty_mask, "Days_Supply"].corr(df.loc[qty_mask, "Quantity_Dispensed"])
    
    df["Quantity_Supply_Predicted"] = np.nan
    df["Quantity_Supply_Residual"] = np.nan
    df["Quantity_Supply_Anomaly"] = False
    
    pred_qty = quantity_supply_model.predict(df.loc[qty_mask, ["Days_Supply"]])
    qresidual = df.loc[qty_mask, "Quantity_Dispensed"].values - pred_qty
    qresid_std = qresidual.std()
    
    df.loc[qty_mask, "Quantity_Supply_Predicted"] = pred_qty
    df.loc[qty_mask, "Quantity_Supply_Residual"] = qresidual
    df.loc[qty_mask, "Quantity_Supply_Anomaly"] = np.abs(qresidual) > RESIDUAL_SIGMA_THRESHOLD * qresid_std
    
    print()
    print("RELATIONSHIP 2: Quantity_Dispensed ~ Days_Supply")
    print(f"  Pearson r               : {qty_pearson_r:.4f}")
    print(f"  Fitted line              : Quantity = {quantity_supply_model.coef_[0]:.4f} * Days_Supply + {quantity_supply_model.intercept_:.4f}")
    print(f"  Residual std              : {qresid_std:.2f}")
    print(f"  Anomalies (|resid|>{RESIDUAL_SIGMA_THRESHOLD}sd): {df['Quantity_Supply_Anomaly'].sum():,}")
    
    # ------------------------------------------------------------
    # Combine into one Module-3 verdict per record
    # ------------------------------------------------------------
    df["Correlation_Module_Anomaly_Count"] = (
        df["Correlation_Anomaly"].astype(int) + df["Quantity_Supply_Anomaly"].astype(int)
    )
    df["Correlation_Module_Is_Anomalous"] = df["Correlation_Module_Anomaly_Count"] > 0
    
    print()
    print(f"Combined Module 3 anomalies (either relationship broken): "
          f"{df['Correlation_Module_Is_Anomalous'].sum():,} / {len(df):,} "
          f"({100*df['Correlation_Module_Is_Anomalous'].mean():.2f}%)")
    
    # ------------------------------------------------------------
    # Save findings
    # ------------------------------------------------------------
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    record_cols = ["Record_ID", "Record_Type", "BENE_ID",
                   "Correlation_Anomaly", "Correlation_Residual",
                   "Quantity_Supply_Anomaly", "Quantity_Supply_Residual",
                   "Correlation_Module_Anomaly_Count", "Correlation_Module_Is_Anomalous"]
    
    findings = {
        "relationships_checked": [
            {
                "name": "Paid_Amount ~ Allowed_Amount",
                "pearson_r": round(float(pearson_r), 4),
                "fitted_coefficient": round(float(correlation_model.coef_[0]), 4),
                "fitted_intercept": round(float(correlation_model.intercept_), 4),
                "residual_std": round(float(resid_std), 2),
                "anomalies_flagged": int(df["Correlation_Anomaly"].sum()),
            },
            {
                "name": "Quantity_Dispensed ~ Days_Supply",
                "pearson_r": round(float(qty_pearson_r), 4),
                "fitted_coefficient": round(float(quantity_supply_model.coef_[0]), 4),
                "fitted_intercept": round(float(quantity_supply_model.intercept_), 4),
                "residual_std": round(float(qresid_std), 2),
                "anomalies_flagged": int(df["Quantity_Supply_Anomaly"].sum()),
            },
        ],
        "summary": {
            "combined_anomalies": int(df["Correlation_Module_Is_Anomalous"].sum()),
            "combined_anomalies_pct": round(100 * df["Correlation_Module_Is_Anomalous"].mean(), 2),
        },
        "sample_flagged_records": (
            df[df["Correlation_Module_Is_Anomalous"]][record_cols]
              .head(20)
              .fillna("")
              .to_dict(orient="records")
        ),
    }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(findings, f, indent=2, default=str)
    
    print(f"\nSaved: {OUTPUT_PATH}")
    return df
