"""
Process Mining Engine — Directly-Follows Graph and analytics.
Builds a DFG from stored events, computes process variants,
cycle times, and activity frequency statistics.
"""

from collections import defaultdict
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.database.db import EventModel
from backend.ingestion.service import get_all_events
from datetime import datetime


def _get_case_traces(db: Session) -> Dict[str, List[EventModel]]:
    """
    Group events by case_id, sorted by timestamp.
    Returns dict: {case_id -> [EventModel, ...]}
    """
    events = get_all_events(db)
    traces: Dict[str, List[EventModel]] = defaultdict(list)
    for ev in events:
        traces[ev.case_id].append(ev)
    # Sort each case by timestamp
    for case_id in traces:
        traces[case_id].sort(key=lambda e: e.timestamp)
    return dict(traces)


def build_dfg(db: Session) -> Dict[str, Any]:
    """
    Build a Directly-Follows Graph (DFG) from all stored events.

    A DFG edge A -> B means activity A was directly followed by activity B
    in at least one case trace.

    Returns:
      nodes: list of {id, label, frequency}
      edges: list of {from, to, frequency}
    """
    traces = _get_case_traces(db)

    activity_freq: Dict[str, int] = defaultdict(int)
    edge_freq: Dict[Tuple[str, str], int] = defaultdict(int)

    for events in traces.values():
        for ev in events:
            activity_freq[ev.activity] += 1
        for i in range(len(events) - 1):
            edge = (events[i].activity, events[i + 1].activity)
            edge_freq[edge] += 1

    nodes = [
        {"id": act, "label": act, "frequency": freq}
        for act, freq in activity_freq.items()
    ]
    edges = [
        {"from": frm, "to": to, "frequency": freq}
        for (frm, to), freq in edge_freq.items()
    ]

    return {"nodes": nodes, "edges": edges}


def get_process_variants(db: Session) -> List[Dict[str, Any]]:
    """
    Compute process variants — distinct activity sequences across all cases.

    Returns a list of dicts sorted by frequency desc:
      {variant: [...activities], count, cases: [...case_ids]}
    """
    traces = _get_case_traces(db)
    variant_map: Dict[Tuple, List[str]] = defaultdict(list)

    for case_id, events in traces.items():
        variant_tuple = tuple(ev.activity for ev in events)
        variant_map[variant_tuple].append(case_id)

    variants = [
        {
            "variant": list(variant),
            "count": len(cases),
            "cases": cases,
        }
        for variant, cases in variant_map.items()
    ]
    variants.sort(key=lambda v: v["count"], reverse=True)
    return variants


def get_cycle_time_stats(db: Session) -> Dict[str, Any]:
    """
    Compute cycle time (start-to-end duration) per case and overall stats.

    Cycle time = timestamp of last event - timestamp of first event, in hours.
    """
    traces = _get_case_traces(db)
    cycle_times: Dict[str, float] = {}

    for case_id, events in traces.items():
        if len(events) < 2:
            cycle_times[case_id] = 0.0
            continue
        try:
            t_start = datetime.fromisoformat(events[0].timestamp.replace("Z", "+00:00"))
            t_end = datetime.fromisoformat(events[-1].timestamp.replace("Z", "+00:00"))
            diff_hours = (t_end - t_start).total_seconds() / 3600
            cycle_times[case_id] = round(diff_hours, 2)
        except Exception:
            cycle_times[case_id] = 0.0

    values = list(cycle_times.values())
    avg = round(sum(values) / len(values), 2) if values else 0.0
    max_ct = round(max(values), 2) if values else 0.0
    min_ct = round(min(values), 2) if values else 0.0

    return {
        "per_case": cycle_times,
        "average_hours": avg,
        "max_hours": max_ct,
        "min_hours": min_ct,
        "total_cases": len(cycle_times),
    }


def get_summary_stats(db: Session) -> Dict[str, Any]:
    """
    High-level statistics for the dashboard overview cards.
    """
    from backend.database.db import EventModel as EM
    total_events = db.query(EM).count()
    case_ids = [r[0] for r in db.query(EM.case_id).distinct().all()]
    total_cases = len(case_ids)
    activities = [r[0] for r in db.query(EM.activity).distinct().all()]

    ct_stats = get_cycle_time_stats(db)
    variants = get_process_variants(db)

    return {
        "total_events": total_events,
        "total_cases": total_cases,
        "unique_activities": len(activities),
        "average_cycle_time_hours": ct_stats["average_hours"],
        "process_variants_count": len(variants),
    }
