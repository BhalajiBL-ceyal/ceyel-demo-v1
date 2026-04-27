"""
FastAPI Router — Blockchain Simulation endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.db import get_db
from backend.ingestion.service import get_all_events
from backend.trust.merkle import get_merkle_root
from backend.blockchain import ledger as chain

router = APIRouter(prefix="/api/blockchain", tags=["Blockchain"])


@router.post("/commit", summary="Commit current Merkle root as a new block")
def commit_block(db: Session = Depends(get_db)):
    """
    Compute the Merkle root of all current events and append it
    as a new immutable block on the local ledger.
    Returns the newly created block.
    """
    events = get_all_events(db)
    leaf_hashes = [ev.event_hash for ev in events]
    root = get_merkle_root(leaf_hashes)
    block = chain.commit_block(root)
    return {"message": "Block committed successfully.", "block": block}


@router.get("/chain", summary="Retrieve the full blockchain ledger")
def get_chain():
    """Return the full append-only blockchain ledger."""
    return {"chain": chain.get_chain(), "length": len(chain.get_chain())}


@router.get("/verify", summary="Verify blockchain integrity")
def verify_chain():
    """
    Re-validate every block's hash and chain linkage.
    Returns whether the chain is valid and the length.
    """
    return chain.verify_chain_integrity()
