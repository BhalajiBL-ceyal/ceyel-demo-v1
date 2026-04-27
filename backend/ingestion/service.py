"""
Event Ingestion Service.
Normalizes incoming events, computes their SHA-256 hash,
and persists them to the SQLite database.
"""

from sqlalchemy.orm import Session
from backend.database.db import EventModel
from backend.ingestion.models import EventIn
from backend.trust.hasher import hash_event
from typing import List, Dict, Any


def normalize_and_store_event(event_in: EventIn, db: Session) -> EventModel:
    """
    Normalize an incoming event, hash it, and persist to the database.

    Normalization ensures:
      - cost and duration default to 0.0 when absent
      - actor defaults to empty string when absent
      - timestamp is stored as-is (ISO 8601 expected)

    Returns the created EventModel ORM instance.
    """
    event_dict = {
        "case_id":   event_in.case_id.strip(),
        "timestamp": event_in.timestamp,
        "activity":  event_in.activity.strip(),
        "actor":     (event_in.actor or "").strip(),
        "cost":      event_in.cost or 0.0,
        "duration":  event_in.duration or 0.0,
    }

    event_hash = hash_event(event_dict)

    db_event = EventModel(
        case_id=event_dict["case_id"],
        timestamp=event_dict["timestamp"],
        activity=event_dict["activity"],
        actor=event_dict["actor"],
        cost=event_dict["cost"],
        duration=event_dict["duration"],
        event_hash=event_hash,
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def bulk_store_events(events: List[EventIn], db: Session) -> Dict[str, Any]:
    """
    Ingest a list of events in bulk.
    Returns a summary of how many succeeded vs. failed.
    """
    ingested = 0
    failed = 0

    for event_in in events:
        try:
            normalize_and_store_event(event_in, db)
            ingested += 1
        except Exception:
            failed += 1

    return {"ingested": ingested, "failed": failed}


def get_all_events(db: Session) -> List[EventModel]:
    """Retrieve all events ordered by case_id and timestamp."""
    return (
        db.query(EventModel)
        .order_by(EventModel.case_id, EventModel.timestamp)
        .all()
    )


def get_events_for_case(case_id: str, db: Session) -> List[EventModel]:
    """Retrieve all events for a specific case ordered by timestamp."""
    return (
        db.query(EventModel)
        .filter(EventModel.case_id == case_id)
        .order_by(EventModel.timestamp)
        .all()
    )
