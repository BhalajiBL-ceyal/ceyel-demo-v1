"""
Merkle Tree implementation for cryptographic integrity verification.
Supports building a complete tree from event hashes, computing the root,
and generating/verifying inclusion proofs for individual events.
"""

import hashlib
from typing import List, Dict, Optional, Any


def sha256(data: str) -> str:
    """Compute SHA-256 of a string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def build_merkle_tree(leaf_hashes: List[str]) -> List[List[str]]:
    """
    Build a Merkle tree from a list of leaf hashes.
    Returns a list of levels, where level[0] = leaves and level[-1] = [root].
    
    If there is an odd number of nodes at a level, the last node is
    duplicated (standard Bitcoin-style Merkle tree padding).
    """
    if not leaf_hashes:
        return []

    current_level = list(leaf_hashes)
    levels = [current_level]

    while len(current_level) > 1:
        # Pad to even count if necessary
        if len(current_level) % 2 == 1:
            current_level.append(current_level[-1])

        next_level = []
        for i in range(0, len(current_level), 2):
            combined = current_level[i] + current_level[i + 1]
            next_level.append(sha256(combined))

        levels.append(next_level)
        current_level = next_level

    return levels


def get_merkle_root(leaf_hashes: List[str]) -> str:
    """
    Compute the Merkle root of a list of leaf hashes.
    Returns a zero-hash if the list is empty.
    """
    if not leaf_hashes:
        return "0" * 64

    tree = build_merkle_tree(leaf_hashes)
    return tree[-1][0]


def get_merkle_proof(leaf_hashes: List[str], target_hash: str) -> Optional[Dict[str, Any]]:
    """
    Generate a Merkle inclusion proof for a given leaf hash.
    
    Returns a dict containing:
      - leaf: the target hash
      - proof: list of {hash, position} dicts (position: 'left' | 'right')
      - root: the computed Merkle root
      
    Returns None if target_hash is not found in leaf_hashes.
    """
    if not leaf_hashes or target_hash not in leaf_hashes:
        return None

    tree = build_merkle_tree(leaf_hashes)
    proof_steps = []
    index = leaf_hashes.index(target_hash)

    for level in tree[:-1]:  # All levels except the root
        # Pad level if odd (mirrors build_merkle_tree logic)
        padded = list(level)
        if len(padded) % 2 == 1:
            padded.append(padded[-1])

        if index % 2 == 0:
            # Current node is left child; sibling is right
            sibling_index = index + 1
            proof_steps.append({"hash": padded[sibling_index], "position": "right"})
        else:
            # Current node is right child; sibling is left
            sibling_index = index - 1
            proof_steps.append({"hash": padded[sibling_index], "position": "left"})

        # Move to parent index in the next level
        index = index // 2

    return {
        "leaf": target_hash,
        "proof": proof_steps,
        "root": tree[-1][0],
    }


def verify_merkle_proof(proof: Dict[str, Any]) -> bool:
    """
    Verify that a Merkle inclusion proof is valid.
    Recomputes the root from the leaf and proof steps and compares
    to the expected root stored in the proof dict.
    """
    current = proof["leaf"]
    for step in proof["proof"]:
        if step["position"] == "right":
            combined = current + step["hash"]
        else:
            combined = step["hash"] + current
        current = sha256(combined)

    return current == proof["root"]
