"""
Blockchain Simulation — local append-only ledger.
Each block stores a Merkle root, timestamp, previous block hash,
and its own block hash (SHA-256 of root + ts + prev_hash).
Immutability is enforced by append-only writes.
"""

import json
import os
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any

# Ledger file path (resolved relative to project root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER_PATH = os.path.join(BASE_DIR, "data", "ledger.json")


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _load_chain() -> List[Dict[str, Any]]:
    """Load the current chain from the ledger file."""
    if not os.path.exists(LEDGER_PATH):
        return []
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_chain(chain: List[Dict[str, Any]]) -> None:
    """Persist the chain to the ledger file (atomic overwrite)."""
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    tmp_path = LEDGER_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(chain, f, indent=2)
    os.replace(tmp_path, LEDGER_PATH)  # Atomic rename


def get_chain() -> List[Dict[str, Any]]:
    """Return the full blockchain ledger."""
    return _load_chain()


def commit_block(merkle_root: str) -> Dict[str, Any]:
    """
    Append a new block to the chain containing the given Merkle root.

    Block structure:
      block_id    — sequential integer
      merkle_root — SHA-256 Merkle root of all current events
      timestamp   — UTC ISO 8601 string
      prev_hash   — block hash of the previous block (or '0'*64 for genesis)
      block_hash  — SHA-256(merkle_root + timestamp + prev_hash)

    Returns the newly created block dict.
    """
    chain = _load_chain()

    prev_hash = chain[-1]["block_hash"] if chain else ("0" * 64)
    timestamp = datetime.now(timezone.utc).isoformat()
    block_id = len(chain)

    raw = merkle_root + timestamp + prev_hash
    block_hash = _sha256(raw)

    block = {
        "block_id":    block_id,
        "merkle_root": merkle_root,
        "timestamp":   timestamp,
        "prev_hash":   prev_hash,
        "block_hash":  block_hash,
    }

    chain.append(block)
    _save_chain(chain)
    return block


def verify_chain_integrity() -> Dict[str, Any]:
    """
    Verify that every block's block_hash matches its recorded fields,
    and that each block correctly references the previous block's hash.
    Returns a dict with 'valid' bool and optional 'broken_at' block_id.
    """
    chain = _load_chain()
    if not chain:
        return {"valid": True, "chain_length": 0}

    for i, block in enumerate(chain):
        # Recompute block hash
        raw = block["merkle_root"] + block["timestamp"] + block["prev_hash"]
        expected_hash = _sha256(raw)
        if block["block_hash"] != expected_hash:
            return {"valid": False, "broken_at": block["block_id"], "reason": "hash_mismatch"}

        # Check linkage (except genesis block)
        if i > 0:
            if block["prev_hash"] != chain[i - 1]["block_hash"]:
                return {"valid": False, "broken_at": block["block_id"], "reason": "broken_chain"}

    return {"valid": True, "chain_length": len(chain)}
