"""
FastAPI Router — Event Ingestion endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database.db import get_db
from backend.ingestion.models import EventIn, EventOut, BulkIngestionResult
from backend.ingestion import service

router = APIRouter(prefix="/api/events", tags=["Ingestion"])


@router.post("", response_model=EventOut, summary="Ingest a single event")
def ingest_event(event: EventIn, db: Session = Depends(get_db)):
    """Accept a single process event and store it in the database."""
    db_event = service.normalize_and_store_event(event, db)
    return db_event


@router.post(
    "/bulk",
    response_model=BulkIngestionResult,
    summary="Ingest multiple events in bulk",
)
def ingest_bulk(events: List[EventIn], db: Session = Depends(get_db)):
    """Accept an array of events and bulk-insert them."""
    result = service.bulk_store_events(events, db)
    return BulkIngestionResult(
        ingested=result["ingested"],
        failed=result["failed"],
        message=f"Ingested {result['ingested']} events, {result['failed']} failed.",
    )


@router.get("", response_model=List[EventOut], summary="List all stored events")
def list_events(db: Session = Depends(get_db)):
    """Return all stored events ordered by case_id and timestamp."""
    return service.get_all_events(db)


@router.get(
    "/{case_id}",
    response_model=List[EventOut],
    summary="Get events for a specific case",
)
def get_case_events(case_id: str, db: Session = Depends(get_db)):
    """Return all events for a specific case, ordered by timestamp."""
    events = service.get_events_for_case(case_id, db)
    if not events:
        raise HTTPException(status_code=404, detail=f"No events found for case '{case_id}'")
    return events
