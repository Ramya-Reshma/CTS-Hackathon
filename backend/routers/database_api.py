"""
API endpoints for querying the UC10 anomalies SQLite database.
Add these endpoints to your FastAPI backend.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
import sqlite3
import json
from datetime import datetime
from pydantic import BaseModel
from pathlib import Path

router = APIRouter(prefix="/api", tags=["database"])

# Database connection
DB_PATH = str(Path(__file__).resolve().parents[1] / "uc10_anomalies.db")


def _parse_full_record(value):
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {"raw": value}
    return {"raw": str(value)}

class AnomalyRecord(BaseModel):
    id: int
    run_id: str
    record_id: str
    record_type: str
    severity: str
    priority: str
    confidence: float
    created_at: str
    full_record: dict = None

    class Config:
        from_attributes = True

class AnomalyResponse(BaseModel):
    total: int
    records: List[AnomalyRecord]
    severity: Optional[str] = None
    limit: int

def get_db_connection():
    """Get SQLite database connection."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

@router.get("/anomalies/db/all", response_model=AnomalyResponse)
def get_all_anomalies(
    limit: int = Query(100, ge=1, le=5000),
    severity: Optional[str] = Query(None, description="Filter: HIGH, MEDIUM, LOW"),
    offset: int = Query(0, ge=0)
):
    """
    Get all anomalies from SQLite database.
    
    Query Parameters:
        limit: Number of records to return (max 5000)
        severity: Filter by severity level (HIGH, MEDIUM, LOW)
        offset: Skip first N records for pagination
    
    Returns:
        List of anomaly records with metadata
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query
        query = "SELECT * FROM anomaly_results"
        params = []
        
        if severity:
            query += " WHERE severity = ?"
            params.append(severity)
        
        # Get total count
        count_query = "SELECT COUNT(*) as total FROM anomaly_results"
        if severity:
            count_query += " WHERE severity = ?"
        
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # Get paginated results
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        records = []
        for row in rows:
            record = AnomalyRecord(
                id=row['id'],
                run_id=row['run_id'],
                record_id=row['record_id'],
                record_type=row['record_type'],
                severity=row['severity'],
                priority=row['priority'],
                confidence=row['confidence'],
                created_at=row['created_at'],
                full_record=_parse_full_record(row['full_record'])
            )
            records.append(record)
        
        conn.close()
        
        return AnomalyResponse(
            total=total,
            records=records,
            severity=severity,
            limit=limit
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")

@router.get("/anomalies/db/high-severity", response_model=AnomalyResponse)
def get_high_severity_anomalies(
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get only HIGH severity anomalies.
    
    Returns:
        List of HIGH severity anomaly records
    """
    return get_all_anomalies(limit=limit, severity="HIGH")

@router.get("/anomalies/db/medium-severity", response_model=AnomalyResponse)
def get_medium_severity_anomalies(
    limit: int = Query(100, ge=1, le=2000)
):
    """
    Get only MEDIUM severity anomalies.
    
    Returns:
        List of MEDIUM severity anomaly records
    """
    return get_all_anomalies(limit=limit, severity="MEDIUM")

@router.get("/anomalies/db/statistics")
def get_database_statistics():
    """
    Get database statistics and summary.
    
    Returns:
        Summary of anomalies by severity and type
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total records
        cursor.execute("SELECT COUNT(*) as total FROM anomaly_results")
        total = cursor.fetchone()['total']
        
        # By severity
        cursor.execute("""
            SELECT severity, COUNT(*) as count 
            FROM anomaly_results 
            GROUP BY severity
        """)
        severity_stats = {row['severity']: row['count'] for row in cursor.fetchall()}
        
        # By type
        cursor.execute("""
            SELECT record_type, COUNT(*) as count 
            FROM anomaly_results 
            GROUP BY record_type
        """)
        type_stats = {row['record_type']: row['count'] for row in cursor.fetchall()}
        
        # By run
        cursor.execute("""
            SELECT run_id, COUNT(*) as count 
            FROM anomaly_results 
            GROUP BY run_id
        """)
        run_stats = {row['run_id']: row['count'] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            "total_anomalies": total,
            "by_severity": severity_stats,
            "by_type": type_stats,
            "by_run": run_stats
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Statistics error: {str(e)}")

@router.get("/anomalies/db/search")
def search_anomalies(
    query: str = Query(..., min_length=1),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Search anomalies by record ID or other fields.
    
    Query Parameters:
        query: Search term
        limit: Maximum results
    
    Returns:
        Matching anomaly records
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        search_term = f"%{query}%"
        
        cursor.execute("""
            SELECT * FROM anomaly_results 
            WHERE record_id LIKE ? 
               OR record_type LIKE ?
               OR run_id LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (search_term, search_term, search_term, limit))
        
        rows = cursor.fetchall()
        records = []
        
        for row in rows:
            record = AnomalyRecord(
                id=row['id'],
                run_id=row['run_id'],
                record_id=row['record_id'],
                record_type=row['record_type'],
                severity=row['severity'],
                priority=row['priority'],
                confidence=row['confidence'],
                created_at=row['created_at'],
                full_record=_parse_full_record(row['full_record'])
            )
            records.append(record)
        
        conn.close()
        
        return {
            "total": len(records),
            "query": query,
            "records": records
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
