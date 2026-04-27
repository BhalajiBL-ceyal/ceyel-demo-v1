"""
Conformance Checking — compare actual case traces against a reference model.
Detects missing steps, extra steps, and order violations per case.
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.ingestion.service import get_events_for_case, get_all_events
from backend.database.db import EventModel


def check_conformance(
    reference_sequence: List[str], db: Session
) -> Dict[str, Any]:
    """
    Compare every case's actual activity sequence against the expected
    reference_sequence (ordered list of activities).

    Deviations detected:
      - missing_steps:   activities in the reference not present in the trace
      - extra_steps:     activities in the trace not in the reference
      - order_violations: activities that appear out of reference order

    Returns a full deviation report:
      {
        total_cases, conforming_cases, deviating_cases,
        fitness_score (0-1),
        deviations: [{case_id, missing_steps, extra_steps, order_violations, is_conforming}]
      }
    """
    all_events = get_all_events(db)
    # Group by case_id
    from collections import defaultdict
    traces: Dict[str, List[str]] = defaultdict(list)
    for ev in all_events:
        traces[ev.case_id].append(ev.activity)

    if not traces:
        return {
            "total_cases": 0,
            "conforming_cases": 0,
            "deviating_cases": 0,
            "fitness_score": 1.0,
            "deviations": [],
            "reference_sequence": reference_sequence,
        }

    ref_set = set(reference_sequence)
    deviations = []
    conforming = 0

    for case_id, activities in traces.items():
        actual_set = set(activities)

        missing = [a for a in reference_sequence if a not in actual_set]
        extra = [a for a in activities if a not in ref_set]

        # Order violations: for each consecutive pair (a, b) in trace,
        # check if their positions in the reference are out of order
        ref_index = {act: i for i, act in enumerate(reference_sequence)}
        order_violations = []
        for i in range(len(activities) - 1):
            curr = activities[i]
            nxt = activities[i + 1]
            if curr in ref_index and nxt in ref_index:
                if ref_index[curr] > ref_index[nxt]:
                    order_violations.append(f"{curr} -> {nxt}")

        is_conforming = (not missing and not extra and not order_violations)
        if is_conforming:
            conforming += 1

        deviations.append({
            "case_id": case_id,
            "actual_sequence": activities,
            "missing_steps": missing,
            "extra_steps": extra,
            "order_violations": order_violations,
            "is_conforming": is_conforming,
        })

    total = len(traces)
    fitness = round(conforming / total, 3) if total > 0 else 1.0

    return {
        "total_cases": total,
        "conforming_cases": conforming,
        "deviating_cases": total - conforming,
        "fitness_score": fitness,
        "deviations": deviations,
        "reference_sequence": reference_sequence,
    }
