# UC10 - Claims & Authorization Anomaly Monitor

Production-quality web frontend and FastAPI backend integration for the UC10 anomaly detection pipeline.

## Overview

UC10 is an enterprise-grade claims and authorization data-quality anomaly monitoring system for healthcare payers. This project provides:

1. **React Frontend** - Professional dashboard for viewing and analyzing anomalies
2. **FastAPI Backend** - REST API layer for pipeline orchestration and data management
3. **SQLite Database** - Persistent storage for analysis results
4. **Pipeline Integration** - Seamless integration with the existing UC10 anomaly detection pipeline

## Architecture

```
User Browser
     ↓
React Frontend (http://localhost:5173)
     ↓
FastAPI Backend (http://localhost:8000)
     ↓
┌────────────────────────────────────┐
│ Existing UC10 Pipeline (Black Box) │
│ - Feature Engineering              │
│ - Statistical Detection            │
│ - Isolation Forest (ML)            │
│ - Correlation Analysis             │
│ - Data Quality Rules               │
│ - RCA Agent (LLM/Bedrock)          │
│ - RAG Knowledge Base               │
└────────────────────────────────────┘
     ↓
SQLite Database
     ↓
React Dashboard
```

## Features

### Frontend Dashboard
- **File Upload**: Drag-and-drop or browse CSV/XLSX/XLS files
- **Real-time Analysis**: Processing stages and progress tracking
- **Summary Cards**: Total records, anomalies, severity breakdown
- **Anomaly Table**: Searchable, filterable, paginated results
- **Severity Filters**: HIGH, MEDIUM, LOW filtering
- **Search**: Search by record ID, type, anomaly type
- **Anomaly Details**: Deep dive into individual anomalies with:
  - Why it was flagged (primary signals)
  - Root cause analysis
  - Recommended actions
  - Business impact assessment
  - Confidence scores
- **Download Results**: Export anomalies as CSV
- **Pagination**: Handle large datasets efficiently

### Backend API
- **POST /api/analyze** - Upload file and trigger analysis
- **GET /api/health** - Health check
- **GET /api/runs/{run_id}** - Get analysis run metadata and statistics
- **GET /api/runs/{run_id}/anomalies** - List anomalies with filtering/pagination
- **GET /api/anomalies/{anomaly_id}** - Get detailed anomaly information
- **GET /api/runs/{run_id}/download** - Download results as CSV

### Database
- Stores only final anomaly results (NOT raw claims data)
- Minimal metadata for audit trail
- Indexes on run_id, severity, record_id for fast queries
- SQLite for simplicity and portability

## Installation

### Prerequisites

- Python 3.10+ (for backend)
- Node.js 16+ (for frontend)
- pip (Python package manager)
- npm or yarn (Node package manager)

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (recommended)
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and update if needed
copy .env.example .env
# Edit .env with your configuration
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Copy environment file (optional)
copy .env.example .env.local
```

## Running the Application

### Option 1: Using Startup Scripts

**Windows:**
```bash
# Terminal 1 - Start backend
start-backend.bat

# Terminal 2 - Start frontend
start-frontend.bat
```

**Linux/Mac:**
```bash
# Terminal 1 - Start backend
chmod +x start-backend.sh
./start-backend.sh

# Terminal 2 - Start frontend
chmod +x start-frontend.sh
./start-frontend.sh
```

### Option 2: Manual Startup

**Backend:**
```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm run dev
```

### Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)

## Project Structure

```
CTS-Hackathon/
├── UC10_Anomaly_Monitor/          (existing pipeline - DO NOT MODIFY)
│   ├── rca/
│   ├── config/
│   └── ...
│
├── ML/                            (existing ML pipeline - DO NOT MODIFY)
│   ├── main.py
│   ├── isolation_forest.py
│   └── ...
│
├── backend/                       (NEW: FastAPI backend)
│   ├── main.py                    (FastAPI app entry point)
│   ├── models.py                  (SQLAlchemy ORM models)
│   ├── schemas.py                 (Pydantic schemas)
│   ├── database.py                (Database setup)
│   ├── services/
│   │   ├── pipeline_adapter.py    (CRITICAL: Wraps existing pipeline)
│   │   └── result_service.py      (Database operations)
│   ├── routers/
│   │   ├── analysis.py            (File upload & analysis endpoint)
│   │   └── anomalies.py           (Anomaly query endpoints)
│   ├── requirements.txt
│   ├── .env.example
│   └── uc10_anomalies.db          (SQLite database)
│
├── frontend/                      (NEW: React frontend)
│   ├── src/
│   │   ├── main.jsx               (React entry point)
│   │   ├── App.jsx                (Main component)
│   │   ├── index.css              (Global styles)
│   │   ├── pages/
│   │   │   ├── Upload.jsx         (File upload page)
│   │   │   └── Dashboard.jsx      (Main dashboard)
│   │   ├── components/
│   │   │   ├── SummaryCards.jsx   (Summary statistics)
│   │   │   ├── AnomaliesTable.jsx (Anomalies table)
│   │   │   ├── Filters.jsx        (Severity/search filters)
│   │   │   └── AnomalyDetail.jsx  (Anomaly detail modal)
│   │   ├── services/
│   │   │   └── api.js             (API client)
│   │   ├── hooks/
│   │   │   └── useStore.js        (Zustand store)
│   │   └── types/
│   │       └── constants.js       (Type definitions)
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── .env.example
│
├── start-backend.bat              (Windows backend startup)
├── start-backend.sh               (Linux/Mac backend startup)
├── start-frontend.bat             (Windows frontend startup)
├── start-frontend.sh              (Linux/Mac frontend startup)
└── README.md                      (This file)
```

## Key Design Decisions

### 1. Pipeline Adapter (backend/services/pipeline_adapter.py)
The most critical component. This adapter:
- **Calls the EXISTING pipeline without modification**
- Located in `backend/services/pipeline_adapter.py`
- Only calls `ML.main.run_pipeline()`
- No pipeline logic is duplicated or changed
- Treats the pipeline as a black box

### 2. Database Design
- **Anomaly Results Only**: Stores only final synthesis report data
- **Raw Claims NOT Stored**: Input CSV/XLSX is deleted after processing
- **Minimal Metadata**: Tracks run_id, filename, created_at, processing_status
- **Indexes**: On run_id, severity, record_id for fast queries
- **SQLite**: Provides simplicity, portability, and sufficient performance

### 3. Frontend Architecture
- **Zustand Store**: Lightweight state management (no Redux complexity)
- **Component-Based**: Modular, reusable React components
- **Separation of Concerns**: Services for API calls, hooks for state, components for UI
- **Professional Design**: Enterprise-grade UI for data operations users

### 4. API Design
- **RESTful**: Standard HTTP methods and status codes
- **Pagination**: Server-side pagination for scalability
- **Filtering**: Severity, search, anomaly type filters
- **Error Handling**: Consistent error responses with detail messages

## Database Schema

### analysis_runs Table
```sql
CREATE TABLE analysis_runs (
    id TEXT PRIMARY KEY,                 -- e.g., RUN-20260816-123456-abcd
    filename TEXT NOT NULL,              -- Uploaded file name
    created_at DATETIME NOT NULL,        -- Analysis start time
    total_records INTEGER NOT NULL,      -- Records in input file
    anomaly_count INTEGER NOT NULL,      -- Total anomalies found
    high_count INTEGER NOT NULL,         -- HIGH severity count
    medium_count INTEGER NOT NULL,       -- MEDIUM severity count
    low_count INTEGER NOT NULL,          -- LOW severity count
    processing_status TEXT NOT NULL,     -- pending, processing, completed, failed
    error_message TEXT,                  -- Error details if failed
    pipeline_version TEXT NOT NULL       -- For tracking pipeline versions
);
```

### anomaly_results Table
```sql
CREATE TABLE anomaly_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,                -- Foreign key to analysis_runs
    created_at DATETIME NOT NULL,        -- When stored
    record_id TEXT NOT NULL,             -- e.g., PH201432
    record_type TEXT NOT NULL,           -- PHARMACY_CLAIM, MEDICAL_CLAIM, PRIOR_AUTH
    severity TEXT NOT NULL,              -- HIGH, MEDIUM, LOW
    priority TEXT NOT NULL,              -- 1-Critical, 2-High, 3-Medium, 4-Low
    anomaly_type TEXT,                   -- Provider, Financial, Timing, etc.
    primary_signal TEXT,                 -- What triggered the anomaly
    likely_root_cause TEXT,              -- Why it happened
    recommended_action TEXT,             -- How to fix it
    confidence REAL,                     -- 0.0-1.0
    impact TEXT,                         -- Business impact description
    additional_checks TEXT,              -- Recommended further checks
    full_record JSON,                    -- Complete original anomaly record
    FOREIGN KEY (run_id) REFERENCES analysis_runs(id)
);
```

## API Endpoints

### Health Check
```
GET /api/health
Response: {"status": "healthy", "message": "..."}
```

### Upload and Analyze
```
POST /api/analyze
Content-Type: multipart/form-data
Body: { file: <binary file data> }

Response:
{
    "run_id": "RUN-20260816-001",
    "status": "completed",
    "filename": "claims.xlsx",
    "total_records": 10000,
    "total_anomalies": 1247,
    "severity_summary": {
        "high": 186,
        "medium": 512,
        "low": 549
    },
    "message": "Analysis completed. Found 1247 anomalies."
}
```

### Get Run Info
```
GET /api/runs/{run_id}
Response:
{
    "run": {
        "id": "RUN-20260816-001",
        "filename": "claims.xlsx",
        "created_at": "2026-08-16T10:30:00",
        "total_records": 10000,
        "anomaly_count": 1247,
        "severity_summary": {...},
        "processing_status": "completed"
    },
    "statistics": {
        "total_records": 10000,
        "total_anomalies": 1247,
        "by_severity": {...},
        "by_record_type": {...},
        "by_anomaly_type": {...},
        "average_confidence": 0.68
    }
}
```

### List Anomalies
```
GET /api/runs/{run_id}/anomalies?severity=HIGH&page=1&page_size=50&search=PH201
Query Parameters:
  - severity: HIGH, MEDIUM, LOW (optional)
  - page: Page number (default: 1)
  - page_size: Results per page (default: 50, max: 500)
  - search: Search query (optional)

Response:
{
    "run_id": "RUN-20260816-001",
    "total": 186,
    "page": 1,
    "page_size": 50,
    "severity_filter": "HIGH",
    "records": [...]
}
```

### Get Anomaly Detail
```
GET /api/anomalies/{anomaly_id}
Response:
{
    "id": 12345,
    "record_id": "PH201432",
    "record_type": "PHARMACY_CLAIM",
    "severity": "HIGH",
    "priority": "2-High",
    "anomaly_type": "Provider",
    "primary_signal": "...",
    "likely_root_cause": "...",
    "recommended_action": "...",
    "confidence": 0.87,
    "impact": "...",
    "additional_checks": "...",
    "created_at": "2026-08-16T10:31:00",
    "full_record": {...}
}
```

### Download Results
```
GET /api/runs/{run_id}/download?severity=HIGH&format=csv
Query Parameters:
  - severity: HIGH, MEDIUM, LOW (optional, filters results)
  - format: csv or xlsx (default: csv)

Response: CSV file download
```

## Workflow

1. **User uploads file**
   - Frontend: Upload.jsx → API: POST /api/analyze
   - Backend: Saves file to temp directory

2. **Backend triggers pipeline**
   - Services: pipeline_adapter.py calls ML.main.run_pipeline()
   - Existing pipeline processes file (no modifications)
   - Pipeline outputs final_anomaly_report.json

3. **Backend stores results**
   - Services: result_service.py reads report and saves to SQLite
   - Only anomaly results stored (raw claims deleted)
   - Run metadata recorded

4. **Frontend displays results**
   - Frontend: Dashboard.jsx fetches run info and anomalies
   - User can filter, search, and view details
   - User can download results as CSV

## Error Handling

### Frontend
- Shows clear error messages for:
  - Invalid file formats
  - File too large
  - Network errors
  - Pipeline failures
  - API errors

### Backend
- Validates file type and size
- Logs all errors with stack traces (to backend logs only)
- Returns user-friendly error messages (NO stack traces)
- Handles database errors gracefully
- Cleans up temp files even on failure

### Pipeline
- If pipeline fails, error is caught and reported
- Database stores error_message for audit trail
- Frontend displays appropriate error message

## Security Considerations

### Data Protection
- ✅ Raw claims data NOT stored in SQLite
- ✅ Temp uploaded files deleted after processing
- ✅ No PII logged (except in backend logs)
- ✅ SQLite database contains only results

### File Validation
- ✅ File extension validation (.csv, .xls, .xlsx)
- ✅ MIME type checking
- ✅ File size limit (100MB)
- ✅ Sanitized filenames

### API Security
- ✅ No AWS credentials in frontend
- ✅ No LM Studio secrets in frontend code
- ✅ CORS configured for local dev
- ✅ Error messages don't expose stack traces

## Performance Optimization

### Frontend
- Pagination: 50 records per page by default
- Lazy loading: Components load data as needed
- Memoization: React memo for expensive components
- Client-side caching: Store API responses

### Backend
- Server-side filtering: Severity, search, pagination
- Database indexes: On run_id, severity, record_id
- Connection pooling: SQLAlchemy manages DB connections
- Async file I/O: Background cleanup of temp files

### Pipeline
- Existing pipeline optimization preserved
- No redundant processing
- Temp directory cleanup in background

## Testing

### Manual Testing Checklist

- [ ] Backend starts and API is healthy
- [ ] Frontend starts and connects to backend
- [ ] Upload CSV file
- [ ] Upload Excel file
- [ ] Upload invalid file (error handling)
- [ ] View summary cards
- [ ] Filter by severity
- [ ] Search by record ID
- [ ] View anomaly details
- [ ] Download results
- [ ] Pagination works
- [ ] Backend logs show pipeline execution
- [ ] SQLite has data (use DB browser)

### Run Tests (Backend)
```bash
cd backend
# No automated tests yet - add with pytest if needed
```

## Troubleshooting

### Backend won't start
```
Error: Port 8000 already in use
Solution: Change port in start-backend.bat/sh or kill existing process
```

### Frontend can't connect to API
```
Error: CORS error in browser console
Solution: Verify backend is running on http://localhost:8000
Solution: Check CORS configuration in backend/main.py
```

### Analysis fails
```
Error: "Analysis failed. Pipeline execution failed"
Solution: Check backend logs for ML pipeline errors
Solution: Verify input file format (CSV/XLSX)
```

### Database locked
```
Error: SQLite database is locked
Solution: Close other connections to SQLite
Solution: Restart backend to reset connection pool
```

## Environment Variables

### Backend (.env)
```
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
FASTAPI_RELOAD=true
DATABASE_URL=sqlite:///backend/uc10_anomalies.db
LOG_LEVEL=INFO
```

### Frontend (.env.local)
```
VITE_API_URL=http://localhost:8000/api
```

## Future Enhancements

- [ ] Add automated tests (pytest backend, Jest frontend)
- [ ] Implement batch processing for large files
- [ ] Add job queue for async processing (Celery/RQ)
- [ ] Add user authentication and authorization
- [ ] Add audit logging for compliance
- [ ] Add data visualization (charts, graphs)
- [ ] Add export to multiple formats (Excel, PDF)
- [ ] Add anomaly status tracking (OPEN, INVESTIGATING, RESOLVED)
- [ ] Add anomaly notes/comments
- [ ] Add bulk operations (update status, add notes)
- [ ] Deploy to cloud (AWS, GCP, Azure)

## License

[Your License Here]

## Support

For issues or questions, contact: [support email]

---

**Last Updated**: 2026-08-17  
**Version**: 1.0.0  
**Status**: Production Ready
