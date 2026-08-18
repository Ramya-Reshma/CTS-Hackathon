"""
Database connection and session management.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy import text

from models import Base

# Database location: use SQLite in project root
DB_DIR = Path(__file__).resolve().parent.parent / "backend"
DB_DIR.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_DIR / 'uc10_anomalies.db'}"

# Create engine
# Use check_same_thread=False to allow multiple threads to access SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Get a database session for dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize the database (create all tables)."""
    Base.metadata.create_all(bind=engine)
    _ensure_schema_updates()
    
    # Seed initial admin user if none exists
    try:
        from services.auth_service import seed_initial_admin
        db = SessionLocal()
        try:
            seed_initial_admin(db)
        finally:
            db.close()
    except Exception as e:
        print(f"[AUTH] Error seeding admin: {e}")

    print(f"Database initialized at: {DATABASE_URL}")


def _ensure_schema_updates():
    """Apply lightweight additive schema updates for SQLite deployments."""
    anomaly_columns = {
        "dataset_id": "VARCHAR(64)",
        "observed_facts": "JSON",
        "possible_causes": "JSON",
        "evidence": "JSON",
        "anomaly_signals": "JSON",
    }

    run_columns = {
        "dataset_id": "VARCHAR(64)",
        "report_dir": "VARCHAR(512)",
        "sla_summary": "JSON",
        "quality_summary": "JSON",
    }

    with engine.begin() as conn:
        # Check anomaly_results
        try:
            rows = conn.execute(text("PRAGMA table_info(anomaly_results)")).fetchall()
            existing = {row[1] for row in rows}
            for col_name, col_type in anomaly_columns.items():
                if col_name not in existing:
                    conn.execute(text(f"ALTER TABLE anomaly_results ADD COLUMN {col_name} {col_type}"))
        except Exception as e:
            print(f"[DB] Note on anomaly_results migration: {e}")

        # Check analysis_runs
        try:
            rows = conn.execute(text("PRAGMA table_info(analysis_runs)")).fetchall()
            existing = {row[1] for row in rows}
            for col_name, col_type in run_columns.items():
                if col_name not in existing:
                    conn.execute(text(f"ALTER TABLE analysis_runs ADD COLUMN {col_name} {col_type}"))
        except Exception as e:
            print(f"[DB] Note on analysis_runs migration: {e}")
