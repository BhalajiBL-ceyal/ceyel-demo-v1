"""
FastAPI Router — Prediction endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database.db import get_db
from backend.prediction.model import predict_for_case
from backend.ingestion.service import get_all_events

router = APIRouter(prefix="/api/prediction", tags=["Prediction"])


@router.get("/{case_id}", summary="Predict remaining time and delay risk for a case")
def predict_case(case_id: str, db: Session = Depends(get_db)):
    """
    Use a RandomForest model (trained on historical event data) to predict:
      - remaining_time_hours: estimated time to case completion
      - delay_risk: probability (0–1) that this case will exceed average cycle time
      - delay_risk_level: LOW / MEDIUM / HIGH
    """
    result = predict_for_case(case_id, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("", summary="Get predictions for all active cases")
def predict_all(db: Session = Depends(get_db)):
    """Return predictions for every unique case in the database."""
    events = get_all_events(db)
    case_ids = list({ev.case_id for ev in events})
    results = []
    for case_id in case_ids:
        result = predict_for_case(case_id, db)
        results.append(result)
    # Sort by delay_risk descending so high-risk cases appear first
    results.sort(key=lambda r: r.get("delay_risk") or 0, reverse=True)
    return results
