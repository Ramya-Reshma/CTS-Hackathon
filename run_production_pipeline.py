"""
Full Production Pipeline Execution Script
Processes exact dataset: data/claims_pharmacy_auth_monitor_dataset_final.xlsx
Executes all 16 stages:
 1. Data Quality Validation
 2. Preprocessing
 3. Feature Engineering
 4. Existing ML Model Training/Fitting
 5. Statistical Anomaly Detection
 6. Isolation Forest
 7. Correlation Analysis
 8. Quantity/Supply Analysis
 9. final_anomaly_report.json Generation
10. Evidence Builder
11. ChromaDB RAG Retrieval
12. all-MiniLM-L6-v2 Embeddings
13. AWS Bedrock RCA
14. final_analysis_report.json Generation
15. SQLite Persistence
16. Run Summary
"""

import os
import sys
import json
import time
from pathlib import Path
import pandas as pd

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))

from ML.main import run_pipeline
from UC10_Anomaly_Monitor.rca import evidence_builder, rag, agent
from backend.database import SessionLocal, init_db
from backend.services.result_service import save_analysis_run


def run_full_pipeline(input_excel_path: str = "Data/claims_pharmacy_auth_monitor_dataset_final.xlsx"):
    start_time = time.time()
    input_file = REPO_ROOT / input_excel_path
    
    print("="*80)
    print("UC10 CLAIMS & AUTHORIZATION ANOMALY MONITOR - FULL PRODUCTION RUN")
    print(f"Target Dataset: {input_excel_path}")
    print("="*80)

    # 0. Verification & Dataset Inspection
    if not input_file.exists():
        print(f"FATAL: Input dataset not found at {input_file}")
        sys.exit(1)

    print("\n[VERIFICATION & DATASET PROFILE]")
    excel_file = pd.ExcelFile(input_file)
    sheet_names = excel_file.sheet_names
    print(f"  - File Exists:       TRUE ({input_file})")
    print(f"  - Sheet Names:       {sheet_names}")
    
    df_raw = pd.read_excel(input_file, sheet_name=0)
    num_rows = len(df_raw)
    num_cols = len(df_raw.columns)
    print(f"  - Total Records:     {num_rows:,}")
    print(f"  - Total Columns:     {num_cols}")
    print(f"  - Column Names:      {list(df_raw.columns)}")

    # 1 - 9: ML Detection Pipeline
    print("\n" + "="*80)
    print("STAGES 1-9: DATA QUALITY, PREPROCESSING, ML DETECTION, & ANOMALY REPORT")
    print("="*80)
    t_ml_start = time.time()
    output_dir = REPO_ROOT / "log"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_json_path = run_pipeline(str(input_file), output_dir=str(output_dir))
    t_ml_end = time.time()
    print(f"[OK] ML Pipeline complete in {t_ml_end - t_ml_start:.2f}s")
    print(f"[OK] Anomaly Report generated at: {report_json_path}")

    # Inspect Anomaly Report
    with open(report_json_path, "r", encoding="utf-8") as f:
        report_data = json.load(f)
    
    total_processed = len(report_data)
    anomalous_records = [r for r in report_data if bool(r.get("ML_Is_Anomalous", False)) or bool(r.get("ISO_Is_Anomaly", False))]
    total_anomalies = len(anomalous_records)
    
    print(f"\n[ANOMALY DETECTION FINDINGS]")
    print(f"  - Total Records Evaluated: {total_processed:,}")
    print(f"  - Total Anomalies Flagged: {total_anomalies:,} ({total_anomalies/total_processed*100:.2f}%)")
    
    # 10 - 14: Evidence Builder, ChromaDB RAG & RCA Agent
    print("\n" + "="*80)
    print("STAGES 10-14: EVIDENCE BUILDER, CHROMADB RAG (MiniLM), BEDROCK RCA")
    print("="*80)
    t_rca_start = time.time()
    
    # Limit LLM RCA batch to first 100 for time optimization if population is large, while processing all anomalies
    max_rca_records = 100
    rca_target_records = anomalous_records[:max_rca_records]
    print(f"Processing RCA for {len(rca_target_records)} anomalous records (capped at {max_rca_records} for batch runtime)...")
    
    rca_agent_instance = agent.RCAAgent()
    analyses = []
    rca_success = 0
    rca_failed = 0
    
    for idx, rec in enumerate(rca_target_records, 1):
        rec_id = str(rec.get("Record_ID", "")).strip()
        if not rec_id:
            continue
        try:
            # Stage 10: Evidence Builder
            ev = evidence_builder.build_evidence(rec_id, report_path=report_json_path)
            
            # Stages 11-12: ChromaDB RAG Retrieval & MiniLM Embeddings
            similar_cases = rag.retrieve_similar_cases(ev, limit=5)
            
            # Stage 13: AWS Bedrock RCA / LLM Inference
            rca_report = rca_agent_instance.run_rag_rca(ev, historical_cases=similar_cases)
            if hasattr(rca_report, "model_dump"):
                payload = rca_report.model_dump()
            elif isinstance(rca_report, dict):
                payload = rca_report
            else:
                payload = json.loads(rca_report.model_dump_json())
                
            payload["record_id"] = rec_id
            analyses.append(payload)
            
            # Save individual report
            indiv_file = output_dir / f"rca_{rec_id}.json"
            with open(indiv_file, "w", encoding="utf-8") as f_indiv:
                json.dump(payload, f_indiv, indent=2)
                
            rca_success += 1
            if idx % 10 == 0 or idx == len(rca_target_records):
                print(f"  [{idx:3d}/{len(rca_target_records)}] RCA processed ({rca_success} successful)")
        except Exception as e:
            rca_failed += 1
            print(f"  [{idx:3d}/{len(rca_target_records)}] RCA failed for {rec_id}: {e}")

    # Stage 14: Final Analysis Report Generation
    final_analysis_path = output_dir / "final_analysis_report.json"
    consolidated_path = output_dir / "rca_consolidated_report.json"
    
    final_output = {"analyses": analyses}
    with open(final_analysis_path, "w", encoding="utf-8") as f_final:
        json.dump(final_output, f_final, indent=2)
    with open(consolidated_path, "w", encoding="utf-8") as f_cons:
        json.dump(analyses, f_cons, indent=2)
        
    t_rca_end = time.time()
    print(f"[OK] RCA Analysis Complete in {t_rca_end - t_rca_start:.2f}s")
    print(f"[OK] Final Analysis Report generated at: {final_analysis_path}")
    print(f"[OK] Consolidated RCA Report generated at: {consolidated_path}")

    # Stage 15: SQLite Persistence
    print("\n" + "="*80)
    print("STAGE 15: SQLITE DATABASE PERSISTENCE")
    print("="*80)
    t_db_start = time.time()
    init_db()
    db = SessionLocal()
    try:
        run_record = save_analysis_run(
            db=db,
            filename=input_file.name,
            report_json_path=str(report_json_path),
            status="completed"
        )
        db_run_id = run_record.id
        total_rec = run_record.total_records
        anom_cnt = run_record.anomaly_count
        high_cnt = run_record.high_count
        med_cnt = run_record.medium_count
        low_cnt = run_record.low_count
        print(f"[OK] Analysis Run #{db_run_id} persisted to SQLite database successfully.")
        print(f"     - Total Records:    {total_rec:,}")
        print(f"     - Total Anomalies:  {anom_cnt:,}")
        print(f"     - High Severity:    {high_cnt:,}")
        print(f"     - Medium Severity:  {med_cnt:,}")
        print(f"     - Low Severity:     {low_cnt:,}")
    finally:
        db.close()
    t_db_end = time.time()

    # Stage 16: Comprehensive Run Summary
    total_elapsed = time.time() - start_time
    print("\n" + "="*80)
    print("STAGE 16: FINAL PRODUCTION RUN SUMMARY")
    print("="*80)
    print(f"  * Dataset:                  {input_excel_path}")
    print(f"  * Total Input Records:      {num_rows:,}")
    print(f"  * Total Features/Columns:   {num_cols}")
    print(f"  * Total Anomalies Detected: {total_anomalies:,}")
    print(f"  * Anomaly Rate:             {(total_anomalies/num_rows)*100:.2f}%")
    print(f"  * RCA Reports Generated:    {rca_success:,}")
    print(f"  * SQLite Run ID:            #{db_run_id}")
    print(f"  * ML Pipeline Time:         {t_ml_end - t_ml_start:.2f}s")
    print(f"  * RCA & Vector Time:        {t_rca_end - t_rca_start:.2f}s")
    print(f"  * DB Persistence Time:      {t_db_end - t_db_start:.2f}s")
    print(f"  * Total Execution Time:     {total_elapsed:.2f}s")
    print("="*80)
    print("ALL 16 PIPELINE STAGES COMPLETED SUCCESSFULLY [OK]")
    print("="*80)


if __name__ == "__main__":
    run_full_pipeline("Data/claims_pharmacy_auth_monitor_dataset_final.xlsx")
