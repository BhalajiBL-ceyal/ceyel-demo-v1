"""
FastAPI Router — Process Mining endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.db import get_db
from backend.process_mining import graph as mining

router = APIRouter(prefix="/api/mining", tags=["Process Mining"])


@router.get("/dfg", summary="Get the Directly-Follows Graph")
def get_dfg(db: Session = Depends(get_db)):
    """
    Build and return the Directly-Follows Graph (DFG) from all stored events.
    Returns nodes (activities) and edges (transitions) with frequency counts.
    """
    return mining.build_dfg(db)


@router.get("/variants", summary="Get process variants")
def get_variants(db: Session = Depends(get_db)):
    """
    Return all distinct process variants (unique activity sequences)
    sorted by frequency (most common first).
    """
    return mining.get_process_variants(db)


@router.get("/cycle-time", summary="Get cycle time statistics")
def get_cycle_time(db: Session = Depends(get_db)):
    """
    Return per-case cycle times (start-to-end duration in hours)
    plus aggregate stats (avg, min, max).
    """
    return mining.get_cycle_time_stats(db)


@router.get("/stats", summary="Get high-level process statistics")
def get_stats(db: Session = Depends(get_db)):
    """
    Return summary statistics for the dashboard overview cards:
    total events, cases, unique activities, average cycle time, variant count.
    """
    return mining.get_summary_stats(db)
