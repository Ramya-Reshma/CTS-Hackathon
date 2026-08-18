# ============================================================
# UC10 - Data Quality Engine (Profiler + Rule Checks + Scoring)
# Runs AFTER the feature-engineering step.
# Input : claims_pharmacy_auth_monitor_dataset_features.csv
# Output: outputs/data_profile.json, outputs/quality_report.json,
#         outputs/batch_sla_risk.json
# Run this in Google Colab
# ============================================================

import pandas as pd
import numpy as np
import json
import os
import datetime

# ============================================================
# Configuration constants
# ============================================================
OUTPUT_DIR = "outputs"

# dtype spec for optional file-loading utilities
dtype_spec = {
    "Record_ID": str,
    "BENE_ID": str,
    "Provider_NPI": str,
    "Auth_Linked_ID": str
}


# ============================================================
# STEP 1: PROFILER
# Produces a structural snapshot of the dataset - per-column
# missingness, uniqueness, ranges, and top values. This is the
# "what does the raw data look like" layer, before any rule judges it.
# ============================================================
def generate_profile(df, output_path=f"{OUTPUT_DIR}/data_profile.json"):
    profile = {}

    profile["total_records"] = len(df)
    profile["total_columns"] = len(df.columns)
    profile["columns"] = {}

    # exact duplicate rows (every column identical) -- handle list-like cells by converting to tuples
    safe_df = df.copy()
    for c in safe_df.columns:
        safe_df[c] = safe_df[c].apply(lambda x: tuple(x) if isinstance(x, list) else x)
    profile["exact_duplicate_rows"] = int(safe_df.duplicated().sum())

    # duplicate Record_ID values (same ID appearing more than once)
    if "Record_ID" in df.columns:
        profile["duplicate_record_ids"] = int(df["Record_ID"].duplicated().sum())
    else:
        profile["duplicate_record_ids"] = 0

    for col in df.columns:
        col_data = df[col]
        # create a safe version for operations that require hashable values
        try:
            safe_col = col_data.apply(lambda x: tuple(x) if isinstance(x, list) else x)
        except Exception:
            safe_col = col_data
        col_profile = {}

        col_profile["data_type"] = str(col_data.dtype)

        missing_count = int(col_data.isnull().sum())
        col_profile["missing_count"] = missing_count
        col_profile["missing_percentage"] = float(missing_count / len(df) * 100) if len(df) > 0 else 0.0

        col_profile["unique_count"] = int(safe_col.nunique(dropna=True))

        if pd.api.types.is_numeric_dtype(col_data):
            col_profile["min"] = float(col_data.min()) if pd.notnull(col_data.min()) else None
            col_profile["max"] = float(col_data.max()) if pd.notnull(col_data.max()) else None
            col_profile["mean"] = float(col_data.mean()) if pd.notnull(col_data.mean()) else None

        elif pd.api.types.is_object_dtype(col_data) or isinstance(col_data.dtype, pd.CategoricalDtype):
            vc = safe_col.value_counts(dropna=True).head(10).to_dict()
            # JSON keys must be strings
            col_profile["value_counts"] = {str(k): int(v) for k, v in vc.items()}

        profile["columns"][col] = col_profile

    profile["date_parsing_failures"] = {}

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(profile, f, indent=4)

    return profile


# ============================================================
# STEP 2: RULE CATALOG
# 21 rules across 5 data-quality dimensions: Completeness,
# Validity, Uniqueness, Consistency, Timeliness. Each rule
# carries a severity, the fields it checks, a plain-language
# description, and a recommended fix - so every failure is
# immediately explainable, not just a flagged number.
# ============================================================
RULES = [
    {"rule_id": "R001", "rule_name": "Record_ID Completeness", "dimension": "Completeness", "severity": "Critical",
     "applicable_record_types": ["MEDICAL_CLAIM", "PHARMACY_CLAIM", "PRIOR_AUTH"], "fields": ["Record_ID"],
     "description": "Record_ID must not be missing.",
     "recommended_fix": "Investigate source system extraction logic. All records must have a primary identifier."},

    {"rule_id": "R002", "rule_name": "Record_ID Uniqueness", "dimension": "Uniqueness", "severity": "Critical",
     "applicable_record_types": ["MEDICAL_CLAIM", "PHARMACY_CLAIM", "PRIOR_AUTH"], "fields": ["Record_ID"],
     "description": "Record_ID must be unique.",
     "recommended_fix": "Deduplicate records based on Record_ID or check if upstream systems are sending multiple updates as new records."},

    {"rule_id": "R003", "rule_name": "Beneficiary and Provider Completeness", "dimension": "Completeness", "severity": "High",
     "applicable_record_types": ["MEDICAL_CLAIM", "PHARMACY_CLAIM", "PRIOR_AUTH"], "fields": ["BENE_ID", "Provider_NPI"],
     "description": "BENE_ID and Provider_NPI must be present for every record type.",
     "recommended_fix": "Ensure patient and provider contexts are fully mapped in the data pipeline."},

    {"rule_id": "R004", "rule_name": "Provider_NPI Validity", "dimension": "Validity", "severity": "High",
     "applicable_record_types": ["MEDICAL_CLAIM", "PHARMACY_CLAIM", "PRIOR_AUTH"], "fields": ["Provider_NPI"],
     "description": "Provider_NPI must contain exactly 10 digits when present.",
     "recommended_fix": "Validate NPI format against the National Plan and Provider Enumeration System standard."},

    {"rule_id": "R005", "rule_name": "Record_ID Prefix Consistency", "dimension": "Consistency", "severity": "High",
     "applicable_record_types": ["MEDICAL_CLAIM", "PHARMACY_CLAIM", "PRIOR_AUTH"], "fields": ["Record_ID", "Record_Type"],
     "description": "Record_ID prefix must match Record_Type (MC, PH, PA).",
     "recommended_fix": "Check for ID generation errors or mismatched Record_Type assignments."},

    {"rule_id": "R006", "rule_name": "Source System Consistency", "dimension": "Consistency", "severity": "High",
     "applicable_record_types": ["MEDICAL_CLAIM", "PHARMACY_CLAIM", "PRIOR_AUTH"], "fields": ["Record_Type", "Source_System"],
     "description": "Record_Type must map to the correct Source_System.",
     "recommended_fix": "Correct source system mapping tables in the ETL logic."},

    {"rule_id": "R007", "rule_name": "Medical Claim Core Fields Completeness", "dimension": "Completeness", "severity": "High",
     "applicable_record_types": ["MEDICAL_CLAIM"],
     "fields": ["Service_Date", "Service_End_Date", "Diagnosis_Code", "Billed_Amount", "Allowed_Amount", "Paid_Amount", "Patient_Responsibility"],
     "description": "MEDICAL_CLAIM requires specific dates, codes, and financial amounts.",
     "recommended_fix": "Verify that all required medical claim fields are extracted from CARRIER_CLAIMS_SYS."},

    {"rule_id": "R008", "rule_name": "Pharmacy Claim Core Fields Completeness", "dimension": "Completeness", "severity": "High",
     "applicable_record_types": ["PHARMACY_CLAIM"],
     "fields": ["Service_Date", "Service_End_Date", "NDC_Code", "Drug_Name", "Days_Supply", "Quantity_Dispensed", "Billed_Amount", "Allowed_Amount", "Paid_Amount", "Patient_Responsibility"],
     "description": "PHARMACY_CLAIM requires specific dates, drug details, and financial amounts.",
     "recommended_fix": "Verify that all required pharmacy claim fields are extracted from PHARMACY_ADJ_SYS."},

    {"rule_id": "R009", "rule_name": "Prior Auth Core Fields Completeness", "dimension": "Completeness", "severity": "High",
     "applicable_record_types": ["PRIOR_AUTH"], "fields": ["Procedure_Code", "Urgency_Flag", "Processed_Date", "Decision_Date", "Status"],
     "description": "PRIOR_AUTH requires codes and urgency, plus dates if APPROVED or DENIED.",
     "recommended_fix": "Ensure decision dates are captured when prior authorizations leave the PENDING state."},

    {"rule_id": "R010", "rule_name": "Financial Amount Non-Negative Validity", "dimension": "Validity", "severity": "High",
     "applicable_record_types": ["MEDICAL_CLAIM", "PHARMACY_CLAIM"], "fields": ["Billed_Amount", "Allowed_Amount", "Paid_Amount", "Patient_Responsibility"],
     "description": "Financial amounts for claims must not be negative.",
     "recommended_fix": "Review adjustment or reversal logic to ensure final line amounts are non-negative."},

    {"rule_id": "R011", "rule_name": "Pharmacy Supply Validity", "dimension": "Validity", "severity": "High",
     "applicable_record_types": ["PHARMACY_CLAIM"], "fields": ["Days_Supply", "Quantity_Dispensed"],
     "description": "Days_Supply and Quantity_Dispensed must be greater than zero.",
     "recommended_fix": "Investigate pharmacy dispensing data for zero values."},

    {"rule_id": "R012", "rule_name": "Status Validity by Record Type", "dimension": "Validity", "severity": "High",
     "applicable_record_types": ["MEDICAL_CLAIM", "PHARMACY_CLAIM", "PRIOR_AUTH"], "fields": ["Record_Type", "Status"],
     "description": "Status must be a valid value for the given Record_Type.",
     "recommended_fix": "Update allowed value lists or correct status mapping during data ingestion."},

    {"rule_id": "R013", "rule_name": "Denial Reason Completeness", "dimension": "Completeness", "severity": "Medium",
     "applicable_record_types": ["MEDICAL_CLAIM", "PHARMACY_CLAIM", "PRIOR_AUTH"], "fields": ["Status", "Denial_Reason_Code"],
     "description": "DENIED or REJECTED records must have a Denial_Reason_Code.",
     "recommended_fix": "Ensure denial codes are populated whenever a claim or auth is denied."},

    {"rule_id": "R014", "rule_name": "Service Dates Consistency", "dimension": "Consistency", "severity": "High",
     "applicable_record_types": ["MEDICAL_CLAIM", "PHARMACY_CLAIM"], "fields": ["Service_Date", "Service_End_Date"],
     "description": "Service_End_Date must be on or after Service_Date.",
     "recommended_fix": "Fix date entry errors where end date precedes start date."},

    {"rule_id": "R015", "rule_name": "Submission vs Service Date Consistency", "dimension": "Consistency", "severity": "High",
     "applicable_record_types": ["MEDICAL_CLAIM", "PHARMACY_CLAIM", "PRIOR_AUTH"], "fields": ["Service_Date", "Submission_Date"],
     "description": "Submission_Date must not be before Service_Date.",
     "recommended_fix": "Investigate time zone issues or data entry errors causing submissions prior to service."},

    {"rule_id": "R016", "rule_name": "Processed vs Submission Date Consistency", "dimension": "Consistency", "severity": "Critical",
     "applicable_record_types": ["MEDICAL_CLAIM", "PHARMACY_CLAIM", "PRIOR_AUTH"], "fields": ["Submission_Date", "Processed_Date"],
     "description": "Processed_Date must not be before Submission_Date.",
     "recommended_fix": "Investigate system clock sync or ETL latency causing processed date anomalies."},

    {"rule_id": "R017", "rule_name": "Auth Link Consistency", "dimension": "Consistency", "severity": "Critical",
     "applicable_record_types": ["MEDICAL_CLAIM", "PHARMACY_CLAIM"], "fields": ["Auth_Required_Flag", "Auth_Linked_ID"],
     "description": "If Auth_Required_Flag is Y, Auth_Linked_ID must exist.",
     "recommended_fix": "Ensure auth numbers are carried over into claims processing systems."},

    {"rule_id": "R018", "rule_name": "Auth Link Referential Integrity", "dimension": "Consistency", "severity": "High",
     "applicable_record_types": ["MEDICAL_CLAIM", "PHARMACY_CLAIM"], "fields": ["Auth_Linked_ID"],
     "description": "If Auth_Linked_ID exists, it must match an existing PRIOR_AUTH record.",
     "recommended_fix": "Check for orphaned claims where the prior authorization is missing from the dataset."},
]
# Note: SLA/Timeliness rules (SLA breach flag accuracy, volume trend consistency,
# SLA breach rate trend consistency) are intentionally excluded from this catalog.
# They will run as part of a separate SLA risk pipeline downstream of this
# data-quality check.


# ============================================================
# STEP 3: QUALITY ENGINE
# Executes every rule from the catalog against the records it
# applies to (by Record_Type), and records a pass/fail outcome
# with the failure rate and sample offending Record_IDs.
# ============================================================
def run_quality_checks(df, rules):
    results = []

    for rule in rules:
        rule_id = rule["rule_id"]
        applicable_types = rule["applicable_record_types"]
        mask = df["Record_Type"].isin(applicable_types)
        applicable_df = df[mask]

        total_applicable = len(applicable_df)
        if total_applicable == 0:
            continue

        failed_mask = pd.Series(False, index=applicable_df.index)

        if rule_id == "R001":
            failed_mask = applicable_df["Record_ID"].isnull() | (applicable_df["Record_ID"] == "")

        elif rule_id == "R002":
            failed_mask = applicable_df.duplicated(subset=["Record_ID"], keep=False)

        elif rule_id == "R003":
            failed_mask = (applicable_df["BENE_ID"].isnull() | applicable_df["Provider_NPI"].isnull()
                            | (applicable_df["BENE_ID"] == "") | (applicable_df["Provider_NPI"] == ""))

        elif rule_id == "R004":
            clean_npi = applicable_df["Provider_NPI"].astype(str).str.replace(r'\.0$', '', regex=True)
            failed_mask = (applicable_df["Provider_NPI"].notnull() & (applicable_df["Provider_NPI"] != "") & (applicable_df["Provider_NPI"] != "nan")
                            & (clean_npi.str.len() != 10))

        elif rule_id == "R005":
            rec_id_str = applicable_df["Record_ID"].astype(str)
            mc_fail = (applicable_df["Record_Type"] == "MEDICAL_CLAIM") & ~rec_id_str.str.startswith(("MC", "TEST"))
            ph_fail = (applicable_df["Record_Type"] == "PHARMACY_CLAIM") & ~rec_id_str.str.startswith(("PH", "TEST"))
            pa_fail = (applicable_df["Record_Type"] == "PRIOR_AUTH") & ~rec_id_str.str.startswith(("PA", "TEST"))
            failed_mask = mc_fail | ph_fail | pa_fail

        elif rule_id == "R006":
            mc_fail = (applicable_df["Record_Type"] == "MEDICAL_CLAIM") & (applicable_df["Source_System"] != "CARRIER_CLAIMS_SYS")
            ph_fail = (applicable_df["Record_Type"] == "PHARMACY_CLAIM") & (applicable_df["Source_System"] != "PHARMACY_ADJ_SYS")
            pa_fail = (applicable_df["Record_Type"] == "PRIOR_AUTH") & (applicable_df["Source_System"] != "AUTH_MGMT_SYS")
            failed_mask = mc_fail | ph_fail | pa_fail

        elif rule_id == "R007":
            cols = ["Service_Date", "Service_End_Date", "Submission_Date", "Diagnosis_Code", "Billed_Amount", "Allowed_Amount", "Paid_Amount", "Patient_Responsibility"]
            failed_mask = applicable_df[cols].isnull().any(axis=1)

        elif rule_id == "R008":
            cols = ["Service_Date", "Service_End_Date", "Submission_Date", "NDC_Code", "Drug_Name", "Days_Supply", "Quantity_Dispensed", "Billed_Amount", "Allowed_Amount", "Paid_Amount", "Patient_Responsibility"]
            failed_mask = applicable_df[cols].isnull().any(axis=1)

        elif rule_id == "R009":
            missing_base = applicable_df[["Procedure_Code", "Urgency_Flag", "Submission_Date"]].isnull().any(axis=1)
            needs_dates = applicable_df["Status"].isin(["APPROVED", "DENIED"])
            missing_dates = needs_dates & applicable_df[["Processed_Date", "Decision_Date"]].isnull().any(axis=1)
            failed_mask = missing_base | missing_dates

        elif rule_id == "R010":
            cols = ["Billed_Amount", "Allowed_Amount", "Paid_Amount", "Patient_Responsibility"]
            failed_mask = (applicable_df[cols] < 0).any(axis=1)

        elif rule_id == "R011":
            cols = ["Days_Supply", "Quantity_Dispensed"]
            failed_mask = (applicable_df[cols] <= 0).any(axis=1)

        elif rule_id == "R012":
            valid_statuses_mc = ["PAID", "DENIED", "REJECTED", "PENDING", "SERVICE_PENDING", "SERVICE_NOT_COMPLETED", "PAYMENT_PENDING", "PAYMENT_NOT_COMPLETED", "IN_PROGRESS", "AWAITING_DECISION", "AWAITING_RESOLUTION", "AWAITING_SERVICE", "AWAITING_PAYMENT"]
            valid_statuses_ph = ["PAID", "REJECTED", "DENIED", "PENDING", "IN_PROGRESS", "AWAITING_DECISION", "AWAITING_RESOLUTION"]
            valid_statuses_pa = ["APPROVED", "DENIED", "PENDING", "IN_PROGRESS", "AWAITING_DECISION", "AWAITING_RESOLUTION", "SERVICE_PENDING", "SERVICE_NOT_COMPLETED", "PAYMENT_PENDING", "PAYMENT_NOT_COMPLETED"]

            mc_fail = (applicable_df["Record_Type"] == "MEDICAL_CLAIM") & ~applicable_df["Status"].isin(valid_statuses_mc)
            ph_fail = (applicable_df["Record_Type"] == "PHARMACY_CLAIM") & ~applicable_df["Status"].isin(valid_statuses_ph)
            pa_fail = (applicable_df["Record_Type"] == "PRIOR_AUTH") & ~applicable_df["Status"].isin(valid_statuses_pa)
            failed_mask = mc_fail | ph_fail | pa_fail

        elif rule_id == "R013":
            needs_reason = applicable_df["Status"].isin(["DENIED", "REJECTED"])
            missing_reason = applicable_df["Denial_Reason_Code"].isnull() | (applicable_df["Denial_Reason_Code"] == "")
            failed_mask = needs_reason & missing_reason

        elif rule_id == "R014":
            has_dates = applicable_df["Service_Date"].notnull() & applicable_df["Service_End_Date"].notnull()
            failed_mask = has_dates & (applicable_df["Service_End_Date"] < applicable_df["Service_Date"])

        elif rule_id == "R015":
            has_dates = applicable_df["Service_Date"].notnull() & applicable_df["Submission_Date"].notnull()
            failed_mask = has_dates & (applicable_df["Submission_Date"] < applicable_df["Service_Date"])

        elif rule_id == "R016":
            has_dates = applicable_df["Submission_Date"].notnull() & applicable_df["Processed_Date"].notnull()
            failed_mask = has_dates & (applicable_df["Processed_Date"] < applicable_df["Submission_Date"])

        elif rule_id == "R017":
            auth_req = applicable_df["Auth_Required_Flag"] == "Y"
            auth_missing = applicable_df["Auth_Linked_ID"].isnull() | (applicable_df["Auth_Linked_ID"] == "")
            failed_mask = auth_req & auth_missing

        elif rule_id == "R018":
            has_auth = applicable_df["Auth_Linked_ID"].notnull() & (applicable_df["Auth_Linked_ID"] != "")
            valid_auths = df[df["Record_Type"] == "PRIOR_AUTH"]["Record_ID"].unique()
            failed_mask = has_auth & ~applicable_df["Auth_Linked_ID"].isin(valid_auths)

        affected_count = int(failed_mask.sum())
        failure_rate = (affected_count / total_applicable) * 100 if total_applicable > 0 else 0

        status = "PASSED" if affected_count == 0 else "FAILED"
        sample_ids = applicable_df[failed_mask]["Record_ID"].head(10).tolist() if "Record_ID" in applicable_df.columns else []

        results.append({
            "rule_id": rule_id,
            "rule_name": rule["rule_name"],
            "dimension": rule["dimension"],
            "severity": rule["severity"],
            "status": status,
            "total_applicable_records": total_applicable,
            "affected_records": affected_count,
            "failure_rate_pct": failure_rate,
            "sample_record_ids": sample_ids,
            "fields": rule["fields"],
            "message": f"{affected_count} records failed the rule." if affected_count > 0 else "All records passed.",
            "description": rule["description"],
            "recommended_fix": rule["recommended_fix"]
        })

    return results


# ============================================================
# STEP 4: SCORING
# Rolls up rule results into 4 dimension scores (0-100) and a
# weighted overall quality score. SLA/Timeliness is intentionally
# excluded here - it runs as its own downstream SLA risk pipeline,
# not as part of this data-quality check.
# ============================================================
def calculate_scores_and_risk(rule_results, df, output_dir=OUTPUT_DIR):
    dimensions = ["Completeness", "Validity", "Uniqueness", "Consistency"]
    dim_scores = {dim: 100.0 for dim in dimensions}
    dim_rates = {dim: [] for dim in dimensions}
    critical_failures = 0
    top_failed_rules = []
    failed_record_ids = set()

    for res in rule_results:
        dim = res["dimension"]
        if dim not in dim_rates:
            dim = "Consistency"  # fallback bucket

        dim_rates[dim].append(res["failure_rate_pct"])

        if res["severity"] == "Critical" and res["status"] == "FAILED":
            critical_failures += 1

        if res["status"] == "FAILED":
            top_failed_rules.append(res)
            for rid in res.get("sample_record_ids", []):
                failed_record_ids.add(rid)

    for dim, rates in dim_rates.items():
        if rates:
            avg_rate = sum(rates) / len(rates)
            dim_scores[dim] = max(0.0, 100.0 - avg_rate)

    # Authoritative weighted aggregation across evaluated data quality dimensions
    # Canonical engine weights: Completeness (27.78%), Validity (27.78%), Uniqueness (22.22%), Consistency (22.22%)
    dimension_weights = {
        "Completeness": 0.2778,
        "Validity": 0.2778,
        "Uniqueness": 0.2222,
        "Consistency": 0.2222,
    }
    total_w = sum(dimension_weights.get(d, 1.0 / len(dim_scores)) for d in dim_scores)
    overall_score = sum(
        (dimension_weights.get(d, 1.0 / len(dim_scores)) / total_w) * dim_scores[d]
        for d in dim_scores
    )
    overall_score = round(float(overall_score), 2)

    if overall_score >= 90 and critical_failures == 0:
        overall_risk_level = "LOW"
    elif overall_score >= 75:
        overall_risk_level = "MEDIUM"
    elif overall_score >= 50:
        overall_risk_level = "HIGH"
    else:
        overall_risk_level = "CRITICAL"

    top_failed_rules.sort(key=lambda x: x["failure_rate_pct"], reverse=True)

    quality_report = {
        "run_timestamp": datetime.datetime.now().isoformat(),
        "records_scanned": len(df),
        "dimension_scores": dim_scores,
        "overall_quality_score": overall_score,
        "overall_risk_level": overall_risk_level,
        "critical_issue_count": critical_failures,
        "all_rule_results": rule_results,
        "top_failed_rules": top_failed_rules[:5],
    }

    os.makedirs(output_dir, exist_ok=True)
    with open(f"{output_dir}/quality_report.json", "w") as f:
        json.dump(quality_report, f, indent=4)

    return quality_report


# ============================================================
# STEP 5: RUN THE FULL PIPELINE (standalone)
# ============================================================
if __name__ == "__main__":
    print("Generating data profile...")
    # default CSV expected when running this module standalone
    DATA_PATH = "claims_pharmacy_auth_monitor_dataset_features.csv"
    try:
        df = pd.read_csv(DATA_PATH, dtype=dtype_spec)
    except Exception as e:
        raise SystemExit(f"Failed to load {DATA_PATH}: {e}")

    date_columns = ["Service_Date", "Service_End_Date", "Processed_Date", "Decision_Date", "Submission_Date"]
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    profile = generate_profile(df)
    print(f"  -> outputs/data_profile.json")

    print("Running quality checks (18 rules)...")
    results = run_quality_checks(df, RULES)
    print(f"  -> {len(results)} rules executed")

    print("Calculating scores and risk...")
    report = calculate_scores_and_risk(results, df)
    print(f"  -> outputs/quality_report.json")

    print()
    print(f"Overall Quality Score : {report['overall_quality_score']:.2f} / 100")
    print(f"Overall Risk Level    : {report['overall_risk_level']}")
    print(f"Critical Issues       : {report['critical_issue_count']}")
    print()
    print("Dimension scores:")
    for dim, score in report["dimension_scores"].items():
        print(f"  {dim:<15} {score:.2f}%")
    print()
    print("Top failed rules:")
    for r in report["top_failed_rules"]:
        print(f"  {r['rule_id']} - {r['rule_name']} ({r['severity']}): {r['failure_rate_pct']:.2f}% failed")

    print("\nRun successful!")

    # In Colab, download the results:
    # from google.colab import files
    # files.download(f"{OUTPUT_DIR}/data_profile.json")
    # files.download(f"{OUTPUT_DIR}/quality_report.json")

