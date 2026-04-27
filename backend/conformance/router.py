"""
FastAPI Router — Conformance Checking endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from backend.database.db import get_db
from backend.conformance.checker import check_conformance

router = APIRouter(prefix="/api/conformance", tags=["Conformance Checking"])


class ConformanceRequest(BaseModel):
    """Request body for conformance checking — the expected process sequence."""
    reference_sequence: List[str]


@router.post("/check", summary="Check conformance against a reference model")
def check(request: ConformanceRequest, db: Session = Depends(get_db)):
    """
    Compare all stored case traces against the provided reference activity sequence.
    Returns a deviation report: missing steps, extra steps, order violations per case.
    """
    return check_conformance(request.reference_sequence, db)


@router.get(
    "/default",
    summary="Check conformance using the default Loan Approval reference model",
)
def check_default(db: Session = Depends(get_db)):
    """
    Convenience endpoint that checks conformance against the built-in
    Loan Approval reference process used in the sample dataset.
    """
    default_reference = [
        "Application Received",
        "Document Verification",
        "Credit Check",
        "Risk Assessment",
        "Approval Decision",
        "Loan Disbursement",
    ]
    return check_conformance(default_reference, db)
