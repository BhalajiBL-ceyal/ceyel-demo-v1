"""
SHA-256 event hashing for tamper-evident event storage.
Each event is serialized to a canonical JSON string then hashed.
"""

import hashlib
import json
from typing import Dict, Any


def hash_event(event: Dict[str, Any]) -> str:
    """
    Compute a SHA-256 hash of an event.
    Fields are sorted to guarantee canonical serialization
    regardless of insertion order.
    
    Args:
        event: Dictionary with keys: case_id, timestamp, activity, actor, cost, duration
    
    Returns:
        Hex-encoded SHA-256 digest string
    """
    # Only hash the business-meaningful fields (not DB id or previous hash)
    canonical_fields = {
        "case_id":   str(event.get("case_id", "")),
        "timestamp": str(event.get("timestamp", "")),
        "activity":  str(event.get("activity", "")),
        "actor":     str(event.get("actor", "")),
        "cost":      float(event.get("cost", 0.0)),
        "duration":  float(event.get("duration", 0.0)),
    }
    # Serialize with sorted keys for determinism
    canonical_json = json.dumps(canonical_fields, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def hash_string(data: str) -> str:
    """Hash an arbitrary UTF-8 string with SHA-256."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
