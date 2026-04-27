"""
Database layer: SQLite via SQLAlchemy.
Defines tables for events and provides session management.
"""

import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# Resolve the data directory relative to this file's location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'ceyel.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class EventModel(Base):
    """
    Represents a single process event ingested from an external source.
    Each event is hashed for tamper-evident storage.
    """
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(String, index=True, nullable=False)
    timestamp = Column(String, nullable=False)          # ISO 8601 string
    activity = Column(String, nullable=False)
    actor = Column(String, nullable=True, default="")
    cost = Column(Float, nullable=True, default=0.0)
    duration = Column(Float, nullable=True, default=0.0)  # in minutes
    event_hash = Column(String, nullable=False)           # SHA-256 of canonical JSON


def init_db():
    """Create all tables if they do not already exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency to provide a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
