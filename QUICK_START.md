# UC10 Frontend & Backend - Quick Start Guide

## 5-Minute Setup

### Prerequisites
- Python 3.10+
- Node.js 16+
- Git

### Step 1: Backend Setup (2 minutes)

```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Frontend Setup (2 minutes)

```bash
cd frontend
npm install
```

### Step 3: Start Everything (1 minute)

**Windows:**
```bash
# Terminal 1
start-backend.bat

# Terminal 2  
start-frontend.bat
```

**Linux/Mac:**
```bash
# Terminal 1
./start-backend.sh

# Terminal 2
./start-frontend.sh
```

### Step 4: Access Application

1. Open http://localhost:5173 in your browser
2. Upload a CSV or Excel file
3. Wait for analysis to complete
4. View results in dashboard

## What Happens Next

1. **File Upload** → Upload page shows file info
2. **Processing** → See 5 processing stages
3. **Results** → Dashboard with:
   - Total records and anomalies
   - HIGH/MEDIUM/LOW severity counts
   - Table of anomalies
   - Filters and search
   - Download as CSV

4. **Details** → Click "View" on any anomaly to see:
   - Why it was flagged
   - Root cause analysis
   - Recommended fix
   - Confidence score

## Key Files

### Backend
- `backend/main.py` - FastAPI server
- `backend/services/pipeline_adapter.py` - Calls existing pipeline
- `backend/models.py` - Database models
- `backend/routers/analysis.py` - Upload endpoint
- `backend/routers/anomalies.py` - Query endpoints

### Frontend
- `frontend/src/App.jsx` - Main component
- `frontend/src/pages/Upload.jsx` - Upload page
- `frontend/src/pages/Dashboard.jsx` - Results dashboard
- `frontend/src/components/` - Reusable components
- `frontend/src/services/api.js` - API client

## Stopping the Application

Press `Ctrl+C` in both terminal windows to stop backend and frontend.

## Troubleshooting

### "Port 8000 already in use"
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8000
kill -9 <PID>
```

### "npm not found"
Install Node.js from https://nodejs.org/

### "pip not found"
Install Python 3.10+ from https://www.python.org/

### CORS Error
Make sure backend is running on http://localhost:8000
Check `backend/main.py` CORSMiddleware configuration

## Testing the API

### Using Swagger UI
1. Go to http://localhost:8000/docs
2. Try out endpoints interactively
3. Upload file via POST /api/analyze
4. Query results via GET /api/runs/{run_id}/anomalies

### Using curl
```bash
# Health check
curl http://localhost:8000/api/health

# Get run info (after uploading)
curl http://localhost:8000/api/runs/RUN-20260816-001

# Get anomalies with filter
curl "http://localhost:8000/api/runs/RUN-20260816-001/anomalies?severity=HIGH&page=1"
```

## Database

SQLite database is automatically created at:
```
backend/uc10_anomalies.db
```

To view data (Windows):
1. Download DB Browser from https://sqlitebrowser.org/
2. Open `backend/uc10_anomalies.db`
3. Browse `analysis_runs` and `anomaly_results` tables

## Next Steps

1. Read `INTEGRATION_GUIDE.md` for detailed documentation
2. Check `backend/README.md` for backend details
3. Check `frontend/README.md` for frontend details
4. Run with real claims data
5. Customize colors, branding, field names as needed

## Support

- Backend logs: Check terminal window running backend
- Frontend logs: Open browser dev tools (F12)
- API docs: http://localhost:8000/docs

---

**Questions?** Check INTEGRATION_GUIDE.md or review the code comments.
