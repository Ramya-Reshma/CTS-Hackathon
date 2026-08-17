"""
Database connection and session management.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

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
    print(f"Database initialized at: {DATABASE_URL}")
