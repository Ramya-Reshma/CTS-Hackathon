# 🚀 How to Connect SQLite Database via API

## Overview
Your SQLite anomaly database (`uc10_anomalies.db`) is now connected to the FastAPI backend via new REST API endpoints.

---

## ✅ Setup Complete

### What was added:
1. ✅ New router file: `routers/database_api.py`
2. ✅ Registered in `main.py`
3. ✅ Connected to SQLite database
4. ✅ 5 new API endpoints available

---

## 📡 Available API Endpoints

### **1. Get All Anomalies**
```
GET /api/anomalies/db/all
```

**Query Parameters:**
- `limit` (int, default=100): Number of records (max 5000)
- `severity` (string, optional): Filter by "HIGH", "MEDIUM", or "LOW"
- `offset` (int, default=0): Skip records for pagination

**Example Requests:**

```bash
# Get first 100 anomalies
curl http://localhost:8000/api/anomalies/db/all

# Get 50 records with offset
curl http://localhost:8000/api/anomalies/db/all?limit=50&offset=0

# Get only HIGH severity
curl http://localhost:8000/api/anomalies/db/all?severity=HIGH&limit=500

# Get MEDIUM severity
curl http://localhost:8000/api/anomalies/db/all?severity=MEDIUM&limit=100
```

**Response:**
```json
{
  "total": 20100,
  "records": [
    {
      "id": 20100,
      "run_id": "RUN-20260817043750-3c57066d",
      "record_id": "UNKNOWN-49",
      "record_type": "UNKNOWN",
      "severity": "MEDIUM",
      "priority": "3-Medium",
      "confidence": 0.5,
      "created_at": "2026-08-17T04:37:50.908960",
      "full_record": {
        "Record_ID": "TEST100050",
        "BENE_ID": "-9000000001049",
        "ISO_Is_Anomaly": true,
        "ISO_Severity_0to1": 0.85,
        ...
      }
    }
  ],
  "severity": "MEDIUM",
  "limit": 100
}
```

---

### **2. Get HIGH Severity Anomalies**
```
GET /api/anomalies/db/high-severity
```

**Query Parameters:**
- `limit` (int, default=100, max 1000)

**Example:**
```bash
curl http://localhost:8000/api/anomalies/db/high-severity?limit=50
```

---

### **3. Get MEDIUM Severity Anomalies**
```
GET /api/anomalies/db/medium-severity
```

**Query Parameters:**
- `limit` (int, default=100, max 2000)

**Example:**
```bash
curl http://localhost:8000/api/anomalies/db/medium-severity?limit=100
```

---

### **4. Get Database Statistics**
```
GET /api/anomalies/db/statistics
```

**Response:**
```json
{
  "total_anomalies": 20100,
  "by_severity": {
    "HIGH": 468,
    "MEDIUM": 3132,
    "LOW": 16500
  },
  "by_type": {
    "UNKNOWN": 20100
  },
  "by_run": {
    "RUN-20260816191920-f5b289c1": 10000,
    "RUN-20260816192335-dffe351f": 10000,
    "RUN-20260816192422-87f884b0": 50,
    "RUN-20260817043750-3c57066d": 50
  }
}
```

**Example:**
```bash
curl http://localhost:8000/api/anomalies/db/statistics
```

---

### **5. Search Anomalies**
```
GET /api/anomalies/db/search
```

**Query Parameters:**
- `query` (string, required): Search term (record_id, type, run_id)
- `limit` (int, default=100, max 500)

**Examples:**
```bash
# Search by record ID
curl http://localhost:8000/api/anomalies/db/search?query=TEST100&limit=50

# Search by type
curl http://localhost:8000/api/anomalies/db/search?query=PHARMACY_CLAIM

# Search by run ID
curl http://localhost:8000/api/anomalies/db/search?query=RUN-20260816
```

---

## 💻 Usage Examples

### **Frontend (React/JavaScript)**

```javascript
// Get all anomalies
async function getAllAnomalies() {
  const response = await fetch('http://localhost:8000/api/anomalies/db/all?limit=100');
  const data = await response.json();
  console.log(data.records);
}

// Get HIGH severity only
async function getHighSeverity() {
  const response = await fetch('http://localhost:8000/api/anomalies/db/high-severity?limit=50');
  const data = await response.json();
  return data.records;
}

// Get statistics
async function getStats() {
  const response = await fetch('http://localhost:8000/api/anomalies/db/statistics');
  const stats = await response.json();
  console.log(`Total: ${stats.total_anomalies}`);
  console.log(`HIGH: ${stats.by_severity.HIGH}`);
  console.log(`MEDIUM: ${stats.by_severity.MEDIUM}`);
  console.log(`LOW: ${stats.by_severity.LOW}`);
}

// Search
async function search(term) {
  const response = await fetch(`http://localhost:8000/api/anomalies/db/search?query=${term}&limit=100`);
  const results = await response.json();
  return results.records;
}
```

### **Python**

```python
import requests

# Configuration
BASE_URL = "http://localhost:8000"

# Get all anomalies
response = requests.get(f"{BASE_URL}/api/anomalies/db/all", params={
    "limit": 100,
    "severity": "HIGH"
})
data = response.json()
print(f"Found {data['total']} anomalies")

# Get statistics
stats = requests.get(f"{BASE_URL}/api/anomalies/db/statistics").json()
print(stats)

# Search
results = requests.get(f"{BASE_URL}/api/anomalies/db/search", params={
    "query": "TEST100",
    "limit": 50
}).json()
print(f"Found {results['total']} matching records")
```

### **cURL (Command Line)**

```bash
# Health check (verify API is running)
curl http://localhost:8000/api/health

# Get stats
curl http://localhost:8000/api/anomalies/db/statistics | json_pp

# Get all HIGH severity
curl "http://localhost:8000/api/anomalies/db/high-severity?limit=50" | json_pp

# Paginate through results
curl "http://localhost:8000/api/anomalies/db/all?limit=100&offset=0" | json_pp
curl "http://localhost:8000/api/anomalies/db/all?limit=100&offset=100" | json_pp
curl "http://localhost:8000/api/anomalies/db/all?limit=100&offset=200" | json_pp
```

---

## 🔧 Integration with Frontend

### **React Hook Example**

```javascript
import { useState, useEffect } from 'react';

function AnomalyDashboard() {
  const [anomalies, setAnomalies] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Get stats
      const statsRes = await fetch('http://localhost:8000/api/anomalies/db/statistics');
      setStats(await statsRes.json());

      // Get anomalies
      const dataRes = await fetch('http://localhost:8000/api/anomalies/db/all?limit=100');
      setAnomalies((await dataRes.json()).records);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <h1>Anomaly Dashboard</h1>
      {stats && (
        <div>
          <p>Total: {stats.total_anomalies}</p>
          <p>HIGH: {stats.by_severity.HIGH}</p>
          <p>MEDIUM: {stats.by_severity.MEDIUM}</p>
          <p>LOW: {stats.by_severity.LOW}</p>
        </div>
      )}
      <table>
        <thead>
          <tr>
            <th>Record ID</th>
            <th>Severity</th>
            <th>Confidence</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {anomalies.map(record => (
            <tr key={record.id}>
              <td>{record.record_id}</td>
              <td>{record.severity}</td>
              <td>{record.confidence}</td>
              <td>{record.created_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## 🚀 Steps to Use

1. **Backend already running?** ✅ (on http://localhost:8000)

2. **Test the API:**
   ```bash
   curl http://localhost:8000/api/anomalies/db/statistics
   ```

3. **Use in Frontend:**
   - Replace your data fetching with API calls
   - All data comes from SQLite database
   - Data is persistent and always available

4. **Monitor via Swagger UI:**
   - Open: http://localhost:8000/docs
   - All endpoints visible with interactive testing

---

## 📊 Database Structure

### `anomaly_results` Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Unique ID |
| run_id | VARCHAR | Analysis run ID |
| record_id | VARCHAR | Record identifier |
| record_type | VARCHAR | Type of record |
| severity | VARCHAR | HIGH/MEDIUM/LOW |
| priority | VARCHAR | Priority level |
| confidence | FLOAT | Confidence score |
| created_at | DATETIME | Creation timestamp |
| full_record | JSON | Complete record data |

---

## ✨ Next Steps

1. ✅ API endpoints are registered
2. ✅ Database connection working
3. ✅ Frontend can now fetch data via API
4. 📝 Update your React components to use these endpoints
5. 🎨 Display data in UI using fetched results

---

**API Documentation:** http://localhost:8000/docs
