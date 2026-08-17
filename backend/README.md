# UC10 Backend - FastAPI

FastAPI REST API layer for UC10 anomaly detection pipeline.

## Quick Start

```bash
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Then visit: http://localhost:8000/docs for interactive API documentation.

## Project Structure

```
backend/
├── main.py                    # FastAPI application entry point
├── database.py                # SQLite connection and session
├── models.py                  # SQLAlchemy ORM models
├── schemas.py                 # Pydantic request/response schemas
├── services/
│   ├── pipeline_adapter.py    # CRITICAL: Wrapper for existing UC10 pipeline
│   └── result_service.py      # Database operations and data transformation
├── routers/
│   ├── analysis.py            # POST /api/analyze (file upload)
│   └── anomalies.py           # GET endpoints for anomaly queries
├── requirements.txt
├── .env.example
└── uc10_anomalies.db          # SQLite database (created on first run)
```

## API Endpoints

### Health
- `GET /api/health` - Check API status

### Analysis
- `POST /api/analyze` - Upload file and trigger analysis

### Queries
- `GET /api/runs/{run_id}` - Get run metadata and statistics
- `GET /api/runs/{run_id}/anomalies` - List anomalies with filtering/pagination
- `GET /api/anomalies/{anomaly_id}` - Get detailed anomaly
- `GET /api/runs/{run_id}/download` - Download results as CSV

## Key Components

### pipeline_adapter.py
**This is the most important file.**

- Calls the EXISTING UC10 pipeline without modification
- Only function: `run_existing_pipeline(input_file_path)`
- Wrapper around `ML.main.run_pipeline()`
- Treats pipeline as a black box
- **NO pipeline logic is duplicated or changed**

### models.py
SQLAlchemy ORM models:
- `AnalysisRun` - Metadata about each analysis
- `AnomalyResult` - Individual anomaly records

### database.py
- SQLite database setup
- SQLAlchemy engine and session factory
- Dependency injection via `get_db()`

### schemas.py
Pydantic schemas for:
- API request validation
- Response serialization
- Type safety

### routers/analysis.py
- File upload endpoint
- Calls pipeline_adapter to run analysis
- Handles background cleanup of temp files
- Error handling for file validation

### routers/anomalies.py
- Query endpoints for anomalies
- Server-side filtering and pagination
- Search capability

## Configuration

Copy `.env.example` to `.env` and configure:

```
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
FASTAPI_RELOAD=true
DATABASE_URL=sqlite:///backend/uc10_anomalies.db
LOG_LEVEL=INFO
```

## Database Schema

### analysis_runs
- `id` (TEXT, PRIMARY KEY) - Unique run ID
- `filename` (TEXT) - Uploaded file name
- `created_at` (DATETIME) - Analysis timestamp
- `total_records` (INTEGER) - Input record count
- `anomaly_count` (INTEGER) - Total anomalies
- `high_count`, `medium_count`, `low_count` (INTEGER) - By severity
- `processing_status` (TEXT) - pending/processing/completed/failed
- `error_message` (TEXT) - Error details if failed

### anomaly_results
- `id` (INTEGER, PRIMARY KEY) - Auto-increment
- `run_id` (TEXT, FK) - Reference to analysis_run
- `record_id` (TEXT) - Unique anomaly identifier
- `record_type` (TEXT) - PHARMACY_CLAIM, MEDICAL_CLAIM, PRIOR_AUTH
- `severity` (TEXT) - HIGH, MEDIUM, LOW
- `priority` (TEXT) - 1-Critical to 4-Low
- `anomaly_type` (TEXT) - Provider, Financial, Timing, etc.
- `primary_signal` (TEXT) - What triggered the anomaly
- `likely_root_cause` (TEXT) - Why it happened
- `recommended_action` (TEXT) - How to fix it
- `confidence` (FLOAT) - 0.0 to 1.0
- `impact` (TEXT) - Business impact
- `additional_checks` (TEXT) - Further investigation needed
- `full_record` (JSON) - Complete original record from pipeline
- `created_at` (DATETIME) - When stored

## Error Handling

- Invalid file format → HTTP 400
- File too large → HTTP 413
- Pipeline failure → HTTP 500 (with user-friendly message)
- Database error → HTTP 500 (logged internally)
- API errors → Consistent JSON error response

### Error Response Format
```json
{
    "error": "Human-readable error description",
    "message": "Detailed error message"
}
```

**Never returns stack traces to client (logged on server only)**

## Logging

All backend operations are logged with timestamps:

```
[2026-08-16 10:30:00] [UC10_API] [INFO] [STARTUP] Initializing database...
[2026-08-16 10:30:01] [UC10_API] [INFO] API received file: claims.xlsx (50MB)
[2026-08-16 10:30:02] [UC10_API] [INFO] [PIPELINE] Starting pipeline...
[2026-08-16 10:31:45] [UC10_API] [INFO] [DB] Created analysis run: RUN-20260816-...
```

Check terminal output for logs or configure file logging.

## Performance

- **Pagination**: Default 50 records/page, max 500
- **Database indexes**: On run_id, severity, record_id
- **Temp cleanup**: Background task deletes uploaded files
- **CORS enabled**: For frontend communication
- **Connection pooling**: SQLAlchemy manages DB connections

## Security

- ✅ File validation (type, size)
- ✅ Sanitized filenames
- ✅ No stack traces in API responses
- ✅ AWS credentials not in code
- ✅ Temp files deleted after processing
- ✅ Raw claims NOT stored in SQLite
- ✅ CORS configured for localhost

## Dependencies

See `requirements.txt`:
- fastapi - Web framework
- uvicorn - ASGI server
- sqlalchemy - ORM
- pydantic - Data validation
- pandas - Data processing
- python-multipart - File uploads
- python-dotenv - Environment configuration

## Development

### Install dev dependencies
```bash
pip install pytest pytest-cov black flake8
```

### Run tests
```bash
pytest tests/ -v
```

### Format code
```bash
black .
```

### Lint
```bash
flake8 .
```

## Deployment

### Production
```bash
# Use production ASGI server (not reload mode)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker (example)
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Troubleshooting

### "Column not found" error
The database schema might not be up to date. Delete `uc10_anomalies.db` and restart. It will recreate the schema.

### "Database is locked"
Another process is accessing SQLite. Restart the backend to reset connections.

### Pipeline returns empty results
Check that `ML.main.run_pipeline()` is being called correctly with valid input file.

## Testing with Real Data

1. Prepare CSV or XLSX file with claims data
2. Use frontend to upload file, or use curl:
   ```bash
   curl -X POST -F "file=@claims.xlsx" http://localhost:8000/api/analyze
   ```
3. Check logs for pipeline execution
4. Query results: `curl http://localhost:8000/api/runs/{run_id}/anomalies`

## Integration with Existing Pipeline

The critical integration point is in `services/pipeline_adapter.py`:

```python
from ML.main import run_pipeline

def run_existing_pipeline(input_file_path: str):
    # Call the EXISTING pipeline exactly as-is
    report_json_path = run_pipeline(input_file_path)
    return report_json_path
```

**This ensures the existing pipeline logic is preserved without any modifications.**

## API Documentation

Interactive Swagger documentation available at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

---

For detailed integration guide, see `INTEGRATION_GUIDE.md` in project root.
