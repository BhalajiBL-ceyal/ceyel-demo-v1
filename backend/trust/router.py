"""
FastAPI Router — Trust Layer endpoints.
Provides Merkle root and inclusion proof generation for stored events.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database.db import get_db
from backend.ingestion.service import get_all_events, get_events_for_case
from backend.trust.merkle import get_merkle_root, get_merkle_proof, verify_merkle_proof

router = APIRouter(prefix="/api/trust", tags=["Trust Layer"])


@router.get("/root", summary="Get the Merkle root of all stored events")
def merkle_root(db: Session = Depends(get_db)):
    """
    Compute the SHA-256 Merkle root of all stored event hashes.
    This root cryptographically commits to the entire event log.
    """
    events = get_all_events(db)
    leaf_hashes = [ev.event_hash for ev in events]
    root = get_merkle_root(leaf_hashes)
    return {
        "merkle_root": root,
        "total_events": len(events),
        "leaf_hashes": leaf_hashes,
    }


@router.get("/proof/{case_id}", summary="Get Merkle inclusion proof for a case")
def merkle_proof(case_id: str, db: Session = Depends(get_db)):
    """
    Generate a Merkle inclusion proof for all events belonging to a case.
    Returns the proof path (sibling hashes) needed to verify the case events
    against the global Merkle root.
    """
    all_events = get_all_events(db)
    case_events = get_events_for_case(case_id, db)

    if not case_events:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

    all_hashes = [ev.event_hash for ev in all_events]
    case_hashes = [ev.event_hash for ev in case_events]
    root = get_merkle_root(all_hashes)

    proofs = []
    for ev in case_events:
        proof = get_merkle_proof(all_hashes, ev.event_hash)
        if proof:
            valid = verify_merkle_proof(proof)
            proofs.append({
                "activity": ev.activity,
                "timestamp": ev.timestamp,
                "event_hash": ev.event_hash,
                "proof_steps": proof["proof"],
                "root": proof["root"],
                "valid": valid,
            })

    return {
        "case_id": case_id,
        "merkle_root": root,
        "event_count": len(case_events),
        "proofs": proofs,
    }


@router.get("/hashes", summary="Get all event hashes")
def get_all_hashes(db: Session = Depends(get_db)):
    """Return all stored event hashes for audit purposes."""
    events = get_all_events(db)
    return [
        {"id": ev.id, "case_id": ev.case_id, "activity": ev.activity, "hash": ev.event_hash}
        for ev in events
    ]
