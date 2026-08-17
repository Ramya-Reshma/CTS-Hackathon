# UC10 ANOMALY MONITOR - COMPREHENSIVE END-TO-END AUDIT REPORT

**Date**: 2025-01-16  
**Status**: CRITICAL ISSUES IDENTIFIED - Ready for Fix Implementation  
**Constraint**: All anomaly detection logic remains UNCHANGED per user requirement

---

## EXECUTIVE SUMMARY

The comprehensive audit has identified **3 CRITICAL BUGS** and **4 INTEGRATION ISSUES** causing:
- ❌ Frontend shows **50/50 records as anomalies** instead of actual **8/50**
- ❌ Record IDs display as **UNKNOWN** instead of real IDs
- ❌ RCA details (root cause, recommendations) **NOT stored or displayed**
- ❌ Database design **doesn't support multi-run isolation**

**Root Cause**: Data flow breaks at the **backend persistence layer** (result_service.py), not in ML logic.

---

## DETAILED FINDINGS

### ISSUE #1: 50/50 ANOMALY BUG (CRITICAL)
**Severity**: CRITICAL  
**Current Behavior**: Frontend shows "TOTAL ANOMALIES = 50"  
**Expected Behavior**: Frontend shows "TOTAL ANOMALIES = 8"  
**Root Cause**: Backend loads ALL records from final_anomaly_report.json and treats them as anomalies

**Test Results on 50-Row File**:
```
Total input records: 50
Actual anomalies (ML_Is_Anomalous=true): 8
Normal records: 42

Breakdown:
  - 7 records with 1 signal (Isolation Forest)
  - 1 record with 2 signals (ISO + Correlation)
```

**Evidence Chain**:
1. ✅ ML/main.py correctly generates final_anomaly_report.json with ALL 50 records + ML_Is_Anomalous flag
2. ✅ final_anomaly_report.json contains correct flags (8 records marked true, 42 marked false)
3. ❌ backend/services/result_service.py loads ALL records as anomalies:

```python
# Line ~57 in result_service.py
anomalies = report_data  # ← WRONG: Takes ALL 50 records

# Should be:
anomalies = [r for r in report_data if r.get('ML_Is_Anomalous')]  # ← CORRECT: Only 8
```

**Fix Required**:
File: [backend/services/result_service.py](backend/services/result_service.py#L55-L75)
```python
# CHANGE THIS:
anomalies = report_data

# TO THIS:
anomalies = [r for r in report_data if r.get('ML_Is_Anomalous')]
```

**Impact**: Once fixed, anomaly_count will be 8 instead of 50, and frontend displays will auto-correct.

---

### ISSUE #2: UNKNOWN RECORD IDs (CRITICAL)
**Severity**: CRITICAL  
**Current Behavior**: Frontend displays "UNKNOWN_49", "UNKNOWN_48", etc.  
**Expected Behavior**: Frontend displays actual record IDs like "TEST100004", "TEST100006", etc.  
**Root Cause**: Field name mapping mismatch in result_service.py

**Evidence**:
- final_anomaly_report.json contains field: `"Record_ID": "TEST100004"`
- result_service.py looks for: `anomaly.get("Record ID", f"UNKNOWN-{idx}")` ← UNDERSCORE vs SPACE

File: [backend/services/result_service.py](backend/services/result_service.py#L105)
```python
record_id=anomaly.get("Record ID", f"UNKNOWN-{idx}"),  # ← WRONG: "Record ID" (space)
```

**Actual Field Name**: `Record_ID` (underscore, not space)

**Fix Required**:
```python
# CHANGE THIS:
record_id=anomaly.get("Record ID", f"UNKNOWN-{idx}"),

# TO THIS:
record_id=anomaly.get("Record_ID", f"UNKNOWN-{idx}"),
```

**Verification**: Confirmed by inspecting final_anomaly_report.json structure.

---

### ISSUE #3: RECORD_TYPE DEFAULTS TO UNKNOWN (CRITICAL)
**Severity**: CRITICAL  
**Current Behavior**: record_type shows as "UNKNOWN"  
**Expected Behavior**: Shows "PHARMACY_CLAIM", "MEDICAL_CLAIM", "PRIOR_AUTH", etc.  
**Root Cause**: Same field name mismatch

File: [backend/services/result_service.py](backend/services/result_service.py#L106)
```python
record_type=anomaly.get("Type", "UNKNOWN"),  # ← WRONG: "Type" doesn't exist
```

**Actual Field Name**: `Record_Type` (not "Type")

**Fix Required**:
```python
# CHANGE THIS:
record_type=anomaly.get("Type", "UNKNOWN"),

# TO THIS:
record_type=anomaly.get("Record_Type", "UNKNOWN"),
```

**Actual Values Found**:
- TEST100004: PHARMACY_CLAIM
- TEST100006: MEDICAL_CLAIM
- TEST100007: MEDICAL_CLAIM
- TEST100011: PRIOR_AUTH
- TEST100021: PHARMACY_CLAIM

---

### ISSUE #4: RCA OUTPUT NOT PRESERVED (HIGH)
**Severity**: HIGH  
**Current Behavior**: RCA fields (likely_root_cause, recommended_action, observed_facts, possible_causes, etc.) stored as NULL  
**Expected Behavior**: Full RCA output from UC10_Anomaly_Monitor.rca.agent.RCAOutput available in database and API  
**Root Cause**: Backend doesn't extract or store RCA data from pipeline output

**Required RCA Fields** (from UC10_Anomaly_Monitor/rca/schemas.py):
```python
incident_id: str
record_type: str
severity: str
summary: str
anomaly_signals: dict
evidence: List[str]
observed_facts: List[str]
possible_causes: List[str]
likely_root_cause: str
confidence: float
impact: Optional[str]
recommended_actions: List[str]  # Note: PLURAL in RCA schema
additional_checks_required: List[str]  # Note: DIFFERENT name than DB schema
```

**Current Database Schema** (from [backend/models.py](backend/models.py)):
- ✅ likely_root_cause
- ✅ recommended_action (singular, not plural)
- ❌ observed_facts (not stored)
- ❌ possible_causes (not stored)
- ❌ evidence (not stored)
- ❌ anomaly_signals (not stored)

**Data Flow Broken At**: [backend/services/result_service.py](backend/services/result_service.py#L95-L125)
```python
# The save_analysis_run() function receives final_anomaly_report.json
# BUT final_anomaly_report.json doesn't contain RCA data!
# RCA data is generated SEPARATELY and saved as rca_<record_id>.json

# Missing: Load individual rca_<record_id>.json files and merge into results
```

**Fix Strategy**:
1. After loading final_anomaly_report.json, for each anomaly with ML_Is_Anomalous=true:
2. Try to load log/rca_<Record_ID>.json (if it exists)
3. Extract RCA fields and populate database
4. Extend AnomalyResult model to store all RCA fields

---

### ISSUE #5: DATABASE SCHEMA DOESN'T SUPPORT RCA FIELDS (HIGH)
**Severity**: HIGH  
**Current**: [backend/models.py](backend/models.py) has only 3 of 8 RCA fields  
**Required Changes**:

```python
# Add these fields to AnomalyResult model:
observed_facts = Column(JSON, nullable=True)  # List of string facts
possible_causes = Column(JSON, nullable=True)  # List of string causes
evidence = Column(JSON, nullable=True)  # List of evidence items
anomaly_signals = Column(JSON, nullable=True)  # Dict of signal details
```

---

### ISSUE #6: FRONTEND RCA DISPLAY READY BUT DATA MISSING (HIGH)
**Severity**: HIGH  
**Current**: [frontend/src/components/AnomalyDetail.jsx](frontend/src/components/AnomalyDetail.jsx) has sections for:
- ✅ "Why Was This Flagged?" (primary_signal)
- ✅ "Likely Root Cause" (likely_root_cause)
- ✅ "Recommended Action" (recommended_action)
- ✅ "Business Impact" (impact)
- ✅ "Additional Checks Required" (additional_checks)
- ✅ "Technical Details" (full_record)

**But Missing**:
- No display section for "Evidence"
- No display section for "Observed Facts"
- No display section for "Possible Causes"
- No display section for "Anomaly Signals"

**Status**: Component structure is correct, just needs data flow fixes in backend.

---

### ISSUE #7: API RESPONSE SCHEMAS INCOMPLETE (MEDIUM)
**Severity**: MEDIUM  
**File**: [backend/schemas.py](backend/schemas.py)  
**Current**: AnomalyResultBase missing RCA fields  
**Fix**: Add optional fields to schemas:

```python
class AnomalyResultBase(BaseModel):
    # ... existing fields ...
    observed_facts: Optional[List[str]] = None
    possible_causes: Optional[List[str]] = None
    evidence: Optional[List[str]] = None
    anomaly_signals: Optional[Dict[str, Any]] = None
```

---

### ISSUE #8: DATABASE PERSISTENCE FOR MULTI-RUN SUPPORT (MEDIUM)
**Severity**: MEDIUM  
**Current Status**: Database has run_id scoping but implementation incomplete

**Requirements**:
- ✅ Unique run_id generated (RUN-<timestamp>-<suffix>)
- ✅ Anomalies linked to run_id via foreign key
- ✅ Same Record_ID in different runs allowed
- ❌ RCA data NOT preserved across runs
- ❌ No run metadata storage (upload timestamp, filename, status)

**Partially Complete**: analysis_runs table exists but:
- run_id generated after pipeline completes (delayed)
- Should generate BEFORE pipeline starts for immediate use

---

## DATA FLOW ANALYSIS

### CURRENT BROKEN FLOW:
```
Input File (50 rows)
    ↓
ML Pipeline (ML/main.py)
    ↓
final_anomaly_report.json (50 records + flags)
    ✅ CORRECT: Record_ID, Record_Type, ML_Is_Anomalous flags
    ↓
backend/services/result_service.py save_analysis_run()
    ❌ BUG #1: Treats ALL 50 as anomalies (should filter by ML_Is_Anomalous)
    ❌ BUG #2: Uses wrong field name "Record ID" (should be "Record_ID")
    ❌ BUG #3: Uses wrong field name "Type" (should be "Record_Type")
    ❌ BUG #4: RCA data never loaded (rca_*.json files ignored)
    ↓
SQLite Database (20,100 anomalies stored, but all from 50 records)
    ❌ WRONG: Stores 50 records as anomalies instead of 8
    ❌ WRONG: Record IDs as "UNKNOWN"
    ❌ WRONG: RCA fields NULL
    ↓
REST API Response (/api/runs/{run_id}/anomalies)
    ↓
React Frontend
    ❌ Display Issue: Shows 50/50 anomalies instead of 8/50
    ❌ Display Issue: Shows UNKNOWN record IDs
    ❌ Display Issue: Shows "—" for RCA fields
```

### CORRECTED FLOW (AFTER FIXES):
```
Input File (50 rows)
    ↓
ML Pipeline (ML/main.py) - UNCHANGED
    ↓
final_anomaly_report.json (50 records + flags)
    ↓
backend/services/result_service.py save_analysis_run()
    ✅ Filter: Only store records with ML_Is_Anomalous=true (8 records)
    ✅ Fixed: Use "Record_ID" field name
    ✅ Fixed: Use "Record_Type" field name
    ✅ Enhanced: Load individual rca_*.json files for RCA data
    ↓
SQLite Database
    ✅ Stores 8 actual anomalies with correct record IDs
    ✅ Stores full RCA details (root cause, recommendations, evidence, etc.)
    ↓
REST API Response
    ✓ Returns 8 anomalies with correct fields populated
    ↓
React Frontend
    ✓ Displays: TOTAL ANOMALIES = 8 (correct)
    ✓ Displays: Real record IDs (TEST100004, etc.)
    ✓ Displays: Full RCA details (root cause, evidence, recommendations)
```

---

## PRIORITY FIX ORDER

### PHASE 1: CRITICAL (Fixes 50/50 bug) - ~30 minutes
1. Filter anomalies by ML_Is_Anomalous in result_service.py
2. Fix field names: "Record ID" → "Record_ID" and "Type" → "Record_Type"
3. Restart backend
4. Test: Upload 50-row file, verify 8 anomalies in database

### PHASE 2: HIGH (Preserves RCA data) - ~1 hour
1. Add JSON columns to AnomalyResult model (observed_facts, possible_causes, evidence, anomaly_signals)
2. Enhance save_analysis_run() to load and merge RCA data
3. Update schemas to include RCA fields
4. Test: Verify rca_*.json data stored in database

### PHASE 3: MEDIUM (Display RCA) - ~30 minutes
1. Add RCA display sections to AnomalyDetail.jsx
2. Update API contract testing
3. Test: Click anomaly, verify RCA details visible

### PHASE 4: OPTIONAL (Multi-run optimization) - ~1 hour
1. Generate run_id before pipeline execution
2. Pass run_id to pipeline for immediate use
3. Add run_id to RCA filenames (rca_<run_id>_<record_id>.json)

---

## FILE CHECKLIST FOR FIXES

**Must Modify**:
- [ ] [backend/services/result_service.py](backend/services/result_service.py) - Lines 55-75 (anomaly filtering)
- [ ] [backend/services/result_service.py](backend/services/result_service.py) - Lines 105-110 (field names)
- [ ] [backend/services/result_service.py](backend/services/result_service.py) - Add RCA loading logic
- [ ] [backend/models.py](backend/models.py) - Add RCA columns
- [ ] [backend/schemas.py](backend/schemas.py) - Add RCA fields
- [ ] [frontend/src/components/AnomalyDetail.jsx](frontend/src/components/AnomalyDetail.jsx) - Add RCA display sections

**Testing Files**:
- [log/final_anomaly_report.json](log/final_anomaly_report.json) - Verified correct (50 records, 8 anomalous)
- [audit_report.py](audit_report.py) - Created for verification

**No Changes Required** (Per Constraint):
- ML/ - All detection logic preserved
- UC10_Anomaly_Monitor/ - RCA logic preserved (only data flow fixed)

---

## TESTING STRATEGY

### Test 1: 50-Row File (Current)
```
Input: UC10_sample_input_50_rows.xlsx
Expected Output:
  - total_anomalies: 8
  - Anomalies: TEST100004, TEST100006, TEST100007, TEST100011, TEST100021, TEST100022, TEST100037, TEST100043
  - No UNKNOWN record IDs
```

### Test 2: Verify Record IDs
```
Query database:
  SELECT DISTINCT record_id FROM anomaly_results WHERE run_id = 'RUN-...'
Should return:
  TEST100004, TEST100006, etc. (no UNKNOWN values)
```

### Test 3: Verify RCA Data
```
Query database:
  SELECT likely_root_cause, observed_facts, evidence FROM anomaly_results WHERE run_id = 'RUN-...'
Should return:
  Non-NULL values for RCA fields
```

### Test 4: Frontend Display
```
1. Upload 50-row file
2. Verify summary shows: TOTAL ANOMALIES = 8
3. Click anomaly
4. Verify detail shows: Record ID (real ID, not UNKNOWN)
5. Verify detail shows: All RCA fields populated
```

---

## SUMMARY TABLE

| Issue | Type | Severity | File | Line | Status |
|-------|------|----------|------|------|--------|
| Treats all records as anomalies | Bug | CRITICAL | result_service.py | 57 | Ready |
| Wrong field name "Record ID" | Bug | CRITICAL | result_service.py | 105 | Ready |
| Wrong field name "Type" | Bug | CRITICAL | result_service.py | 106 | Ready |
| RCA data not loaded/stored | Bug | HIGH | result_service.py | N/A | Ready |
| Database missing RCA columns | Design | HIGH | models.py | N/A | Ready |
| API schemas incomplete | Design | MEDIUM | schemas.py | N/A | Ready |
| Frontend needs RCA sections | UI | MEDIUM | AnomalyDetail.jsx | N/A | Ready |
| Multi-run optimization | Design | LOW | result_service.py | N/A | Optional |

---

## NEXT STEPS

1. Review this audit report ✓
2. Proceed to PHASE 1 fixes (Critical issues)
3. Run test suite after each phase
4. Measure improvement at each stage
5. Deploy and verify in production

All fixes are **non-invasive** to existing ML pipeline logic per user constraint.
