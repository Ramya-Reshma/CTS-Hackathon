# RAG + Hybrid Knowledge Base for Claims RCA

This project now includes a hybrid knowledge base and retrieval flow for healthcare claims root-cause analysis.

## What it does

- Runs the anomaly ML pipeline on the claim dataset
- Builds a compact evidence package for a flagged record
- Searches historical resolved cases using:
  - exact match on record type, status, denial reason
  - similarity on days-supply, quantity, price, authorization flags
  - lightweight semantic-overlap matching on textual fields
- Provides the current record and historical cases to the LLM as RCA context
- Returns a recommendation JSON with likely root cause, actions, checks, and confidence

## Files involved

- [UC10_Anomaly_Monitor/main.py](UC10_Anomaly_Monitor/main.py)
- [UC10_Anomaly_Monitor/rca/rag.py](UC10_Anomaly_Monitor/rca/rag.py)
- [UC10_Anomaly_Monitor/rca/hybrid_kb.py](UC10_Anomaly_Monitor/rca/hybrid_kb.py)
- [log/historical_resolution_cases.json](log/historical_resolution_cases.json)

## Usage

From the project root:

```bash
python -m UC10_Anomaly_Monitor.main PH201432
```

This writes the final RCA result to:

```text
log/rca_PH201432.json
```

## Historical KB format

Each historical record should include:

```json
{
  "incident_id": "PH201771",
  "record_type": "PHARMACY_CLAIM",
  "status": "REJECTED",
  "denial_reason_code": "88_DUR_REJECT",
  "auth_required_flag": "Y",
  "days_supply": 92,
  "quantity_dispensed": 96,
  "billed_amount": 248000,
  "allowed_amount": 2100,
  "paid_amount": 2100,
  "iso_anomaly": true,
  "iso_severity": 0.95,
  "root_cause": "Duration-based pharmacy authorization mismatch.",
  "resolution_used": "Validated the plan duration rule and routed to exception review.",
  "recommended_actions": [
    "Validate days-supply against the plan policy."
  ],
  "confidence": 0.88
}
```

## Testing

```bash
python -m pytest tests/test_rag_flow.py tests/test_hybrid_kb.py -q
```

## Optional production upgrades

- Add FAISS or Chroma vector search
- Store cases in Postgres with pgvector
- Use sentence-transformers to create embeddings for natural-language similarity
- Use SQL filtering + vector retrieval together for a hybrid production pipeline
