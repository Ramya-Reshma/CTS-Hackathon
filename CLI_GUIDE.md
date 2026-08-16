# Claims Pharmacy Auth Monitor - CLI Guide

## Overview

The `manage.py` CLI provides a unified interface to run the complete anomaly detection and RCA (Root Cause Analysis) pipeline.

## Quick Start

### 1. Initialize Vector Knowledge Base

Before running RCA, initialize the vector database from the Excel workbook:

```bash
python manage.py vector-db-init
```

Output:
```
[INFO] Initializing vector knowledge base from workbook...
[INFO] Vector KB initialized with 352 cases from: healthcare_claims_anomaly_RAG_knowledge_base_REBUILT.xlsx
```

### 2. View Flagged Anomalies

List the anomalies detected by the ML pipeline:

```bash
python manage.py list-anomalies --limit 10
```

Output:
```
[INFO] Total records: 10000, Flagged anomalies: 815
[INFO] Showing first 10 anomalies:

1. PH201178 | Type: PHARMACY_CLAIM | Severity: 0.66 | Denial: N/A
2. PH200401 | Type: PHARMACY_CLAIM | Severity: 0.54 | Denial: N/A
...
```

### 3. Run RCA on a Specific Record

Analyze a specific anomalous record to generate root cause analysis:

```bash
python manage.py rca PH201178
```

Output:
```json
{
  "incident_id": "PH201178",
  "record_type": "PHARMACY_CLAIM",
  "severity": "MEDIUM",
  "likely_root_cause": "provider behavior, patient mix, coding, contract, credentialing, location, or source-data issue.",
  "confidence": 0.5,
  "recommended_actions": [
    "normalize for specialty, geography, panel size and case mix; validate provider master data and review persistent outliers."
  ]
}
```

---

## Full Command Reference

### `python manage.py ml-pipeline <input_file> [--output-dir DIR]`

Runs the complete ML anomaly detection pipeline on claims data.

**Arguments:**
- `input_file` (required): Path to input CSV or Excel file
  - Supported formats: `.csv`, `.xlsx`, `.xls`
- `--output-dir DIR` (optional): Custom output directory (default: `log/`)

**Outputs:**
- `log/final_anomaly_report.json` - JSON array of all records with anomaly flags
- `outputs/data_profile.json` - Data quality profiling results
- `outputs/quality_report.json` - Detailed quality check results

**Example:**
```bash
python manage.py ml-pipeline Data/claims_pharmacy_auth_monitor_dataset_final.xlsx
```

---

### `python manage.py vector-db-init`

Initializes or rebuilds the ChromaDB vector knowledge base from the Excel workbook.

**Features:**
- Auto-discovers workbook: `healthcare_claims_anomaly_RAG_knowledge_base_REBUILT.xlsx`
- Ingests 352 knowledge base cases into Chroma
- Enables semantic similarity search for RCA retrieval
- Persists collection in `data/vector_kb/`

**Example:**
```bash
python manage.py vector-db-init
```

**Output:**
```
[INFO] Vector KB initialized with 352 cases from: healthcare_claims_anomaly_RAG_knowledge_base_REBUILT.xlsx
[INFO] Persist directory: data/vector_kb
```

---

### `python manage.py rca <record_id> [--kb-path PATH]`

Runs Root Cause Analysis for a specific anomalous record.

**Arguments:**
- `record_id` (required): The anomaly record ID (e.g., `PH201432`, `PA301107`)
- `--kb-path PATH` (optional): Custom knowledge base path

**Prerequisites:**
- ML pipeline must be run first (generates `log/final_anomaly_report.json`)
- Vector DB should be initialized (run `vector-db-init` first)

**Outputs:**
- `log/rca_<record_id>.json` - RCA report in JSON format

**Example:**
```bash
python manage.py rca PH201432
```

**Sample RCA Report:**
```json
{
  "incident_id": "PH201432",
  "record_type": "PHARMACY_CLAIM",
  "severity": "MEDIUM",
  "summary": "...",
  "likely_root_cause": "Duration-based pharmacy authorization mismatch; claim exceeded allowed days-supply for the selected drug.",
  "confidence": 0.88,
  "recommended_actions": [
    "Validate days-supply against plan policy.",
    "Check if the drug authorization rules were applied correctly.",
    "Escalate to pharmacy adjudication for exception review."
  ],
  "additional_checks_required": [
    "Check if the claim was denied under a duration-policy rule instead of a true data-quality error.",
    "Validate the drug authorization and days-supply against payer policy."
  ]
}
```

---

### `python manage.py list-anomalies [--report PATH] [--limit N]`

Lists flagged anomalies from the latest ML report.

**Arguments:**
- `--report PATH` (optional): Custom path to anomaly report (default: `log/final_anomaly_report.json`)
- `--limit N` (optional): Max anomalies to display (default: 10)

**Output:**
```
[INFO] Total records: 10000, Flagged anomalies: 815
[INFO] Showing first 5 anomalies:

1. PH201178 | Type: PHARMACY_CLAIM | Severity: 0.66 | Denial: N/A
2. PH200401 | Type: PHARMACY_CLAIM | Severity: 0.54 | Denial: N/A
3. PH200153 | Type: PHARMACY_CLAIM | Severity: 0.64 | Denial: N/A
4. PH201990 | Type: PHARMACY_CLAIM | Severity: 0.50 | Denial: N/A
5. PA301107 | Type: PRIOR_AUTH | Severity: 0.83 | Denial: N/A
```

**Example:**
```bash
python manage.py list-anomalies --limit 20
```

---

### `python manage.py full-pipeline <input_file> [--sample-records N]`

Runs the complete end-to-end pipeline:
1. ML anomaly detection
2. Vector DB initialization
3. RCA on flagged records

**Arguments:**
- `input_file` (required): Path to input CSV or Excel file
- `--sample-records N` (optional): Limit RCA to first N records (useful for testing)

**Workflow:**
```
Input Data
    ↓
[STEP 1] ML Pipeline → final_anomaly_report.json
    ↓
[STEP 2] Initialize Vector KB
    ↓
[STEP 3] Run RCA on Flagged Anomalies → rca_<record_id>.json files
    ↓
Summary & Results
```

**Example - Full Pipeline:**
```bash
python manage.py full-pipeline Data/claims_pharmacy_auth_monitor_dataset_final.xlsx
```

**Example - Test with 5 Records:**
```bash
python manage.py full-pipeline Data/claims_pharmacy_auth_monitor_dataset_final.xlsx --sample-records 5
```

**Output:**
```
======================================================================
STARTING FULL PIPELINE
======================================================================

[STEP 1] Running ML anomaly detection...
ML pipeline completed. Report saved to: log/final_anomaly_report.json

[STEP 2] Initializing vector knowledge base...
Vector KB initialized with 352 cases from: healthcare_claims_anomaly_RAG_knowledge_base_REBUILT.xlsx

[STEP 3] Running RCA on flagged anomalies...
Processing 815 flagged records (out of 815 total)...

[1/5] Processing PH201178...
RCA report saved to: log/rca_PH201178.json

[2/5] Processing PH200401...
RCA report saved to: log/rca_PH200401.json

...

======================================================================
PIPELINE SUMMARY
======================================================================
ML Pipeline: Complete
Vector DB: Initialized with workbook KB
RCA Results: 5/5 successful
  PH201178: SUCCESS
  PH200401: SUCCESS
  PH200153: SUCCESS
  PH201990: SUCCESS
  PA301107: SUCCESS
======================================================================
```

---

## Typical Workflows

### Workflow 1: Quick Analysis of Existing Data

```bash
# 1. View anomalies
python manage.py list-anomalies --limit 5

# 2. Analyze one record
python manage.py rca PH201178
```

### Workflow 2: Full Pipeline on New Dataset

```bash
# 1. Run ML pipeline on new data
python manage.py ml-pipeline new_claims_data.csv

# 2. Initialize vector KB (if not already done)
python manage.py vector-db-init

# 3. View results
python manage.py list-anomalies --limit 10

# 4. Analyze top anomaly
python manage.py rca PH201178
```

### Workflow 3: End-to-End Pipeline

```bash
# Complete pipeline in one command
python manage.py full-pipeline data/claims_data.xlsx --sample-records 50
```

---

## Output Files

| Command | Output File | Description |
|---------|------------|-------------|
| `ml-pipeline` | `log/final_anomaly_report.json` | Array of all records with ML anomaly flags |
| `ml-pipeline` | `outputs/data_profile.json` | Data quality profile statistics |
| `ml-pipeline` | `outputs/quality_report.json` | Detailed quality check results |
| `vector-db-init` | `data/vector_kb/` | Chroma collection files |
| `rca` | `log/rca_<record_id>.json` | RCA report for a specific record |

---

## Help & Troubleshooting

### View All Commands
```bash
python manage.py --help
```

### View Command-Specific Help
```bash
python manage.py ml-pipeline --help
python manage.py rca --help
python manage.py full-pipeline --help
```

### Common Issues

**Issue: "Report not found"**
```
[ERROR] Report not found: log/final_anomaly_report.json. Run ml-pipeline first.
```
**Solution:** Run the ML pipeline first:
```bash
python manage.py ml-pipeline Data/claims_pharmacy_auth_monitor_dataset_final.xlsx
```

**Issue: Vector DB shows 0 cases**
```
[WARNING] Vector KB is empty. Check workbook path and try again.
```
**Solution:** Ensure the workbook exists:
```
healthcare_claims_anomaly_RAG_knowledge_base_REBUILT.xlsx
```

**Issue: LM Studio endpoint unavailable (uses fallback)**
```
[INFO] Root Cause: provider behavior, patient mix, coding, contract, credentialing, location, or source-data issue.
[INFO] Confidence: 0.5
```
The system falls back to vector DB retrieval when LM Studio is unavailable.

---

## Architecture Overview

```
manage.py (Main CLI Entry Point)
    │
    ├─→ ml-pipeline
    │        └─→ ML/main.py:run_pipeline()
    │             ├─ Feature Engineering
    │             ├─ Statistical Detection
    │             ├─ Isolation Forest (ML)
    │             ├─ Correlation Analysis
    │             └─ Data Quality Checks
    │
    ├─→ rca
    │        └─→ UC10_Anomaly_Monitor/main.py:main()
    │             ├─ Evidence Builder
    │             ├─ Vector KB Search (ChromaDB)
    │             ├─ Hybrid KB Search
    │             └─ LLM/Fallback RCA
    │
    ├─→ vector-db-init
    │        └─→ ChromaCaseKB()
    │             ├─ Load Excel workbook
    │             ├─ Build embeddings
    │             └─ Index in Chroma
    │
    ├─→ list-anomalies
    │        └─→ Read final_anomaly_report.json
    │             └─ Display flagged records
    │
    └─→ full-pipeline
             ├─ Run ml-pipeline
             ├─ Run vector-db-init
             └─ Run rca for each flagged record
```

---

## Configuration

### Environment Variables

Configure LM Studio endpoint in `.env`:
```bash
LM_STUDIO_URL=http://127.0.0.1:1234/v1
LM_STUDIO_MODEL=qwen/qwen3-4b
LM_TIMEOUT=300
```

### Default Directories

- **Input data:** `Data/`
- **ML outputs:** `log/`, `outputs/`
- **Vector DB:** `data/vector_kb/`
- **RCA reports:** `log/rca_*.json`

---

## Performance Notes

- **ML Pipeline:** ~30-60 seconds for 10,000 records
- **Vector DB Init:** ~30 seconds (first time), <5 seconds (cached)
- **RCA per Record:** 1-5 seconds (vector search + LLM or fallback)
- **Full Pipeline:** 5-10 minutes for 10,000 records with top 100 RCAs

---

## Support

For issues or questions:
1. Check `.env` configuration
2. Verify input file format (CSV or XLSX)
3. Run `python manage.py --help` for command options
4. Check output files in `log/` and `outputs/` for detailed results
