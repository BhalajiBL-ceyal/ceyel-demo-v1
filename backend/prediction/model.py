"""
Predictive Module — ML-based remaining time and delay risk prediction.
Uses scikit-learn RandomForestRegressor trained on historical event data.
Since this is a local prototype, it trains on the fly from stored events.
"""

import numpy as np
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from collections import defaultdict
from datetime import datetime

from backend.database.db import EventModel
from backend.ingestion.service import get_all_events


def _parse_ts(ts_str: str) -> datetime:
    """Parse an ISO 8601 timestamp string into a datetime object."""
    return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))


def _build_training_data(db: Session):
    """
    Build training features and targets from completed cases.
    
    Features per event (within a case):
      - progress_pct: how far through the case we are (0–1)
      - activity_index: position of this event's activity in the global list
      - cumulative_cost: sum of costs up to this event
      - step_number: sequential index within the case
    
    Target:
      - remaining_hours: time from this event to case end
    """
    all_events = get_all_events(db)

    # Group by case
    traces: Dict[str, List[EventModel]] = defaultdict(list)
    for ev in all_events:
        traces[ev.case_id].append(ev)

    # Build unique activity index
    all_activities = list({ev.activity for ev in all_events})
    act_idx = {act: i for i, act in enumerate(all_activities)}

    X, y = [], []

    for case_id, events in traces.items():
        events.sort(key=lambda e: e.timestamp)
        if len(events) < 2:
            continue
        try:
            t_start = _parse_ts(events[0].timestamp)
            t_end = _parse_ts(events[-1].timestamp)
            total_duration = (t_end - t_start).total_seconds() / 3600
            if total_duration <= 0:
                continue

            cum_cost = 0.0
            for step, ev in enumerate(events):
                t_now = _parse_ts(ev.timestamp)
                elapsed = (t_now - t_start).total_seconds() / 3600
                remaining = total_duration - elapsed
                if remaining < 0:
                    remaining = 0.0

                progress = elapsed / total_duration
                cum_cost += ev.cost or 0.0

                features = [
                    progress,
                    act_idx.get(ev.activity, 0),
                    cum_cost,
                    step,
                    len(events),
                ]
                X.append(features)
                y.append(remaining)
        except Exception:
            continue

    return np.array(X), np.array(y), act_idx, all_activities


def predict_for_case(case_id: str, db: Session) -> Dict[str, Any]:
    """
    Train a RandomForest model on all available data and predict:
      - remaining_time_hours: estimated hours until case completion
      - delay_risk: probability (0–1) of being above average cycle time
    
    Falls back to heuristic if insufficient training data.
    """
    from sklearn.ensemble import RandomForestRegressor

    X, y, act_idx, all_activities = _build_training_data(db)

    # Get current case events
    all_events = get_all_events(db)
    case_events = sorted(
        [ev for ev in all_events if ev.case_id == case_id],
        key=lambda e: e.timestamp
    )

    if not case_events:
        return {
            "case_id": case_id,
            "error": "No events found for this case.",
            "remaining_time_hours": None,
            "delay_risk": None,
        }

    # Compute features for the LAST event in this case (current state)
    try:
        t_start = _parse_ts(case_events[0].timestamp)
        t_now = _parse_ts(case_events[-1].timestamp)
        elapsed = (t_now - t_start).total_seconds() / 3600
    except Exception:
        elapsed = 0.0

    cum_cost = sum(ev.cost or 0.0 for ev in case_events)
    step = len(case_events)

    # Estimate total steps from training data (average case length)
    avg_total_steps = float(np.mean([x[4] for x in X])) if len(X) > 0 else 5.0
    progress = min(elapsed / max(elapsed + 1, 1), 1.0)

    last_ev = case_events[-1]
    features = np.array([[
        progress,
        act_idx.get(last_ev.activity, 0),
        cum_cost,
        step,
        avg_total_steps,
    ]])

    # Need at least 5 samples to train
    if len(X) >= 5:
        model = RandomForestRegressor(n_estimators=50, random_state=42)
        model.fit(X, y)
        remaining = float(model.predict(features)[0])
        remaining = max(0.0, round(remaining, 2))

        # Delay risk: predicted remaining > 1 std above mean remaining in training data
        mean_rem = float(np.mean(y))
        std_rem = float(np.std(y)) + 1e-9
        z_score = (remaining - mean_rem) / std_rem
        # Sigmoid of z-score to map to 0–1 probability
        delay_risk = round(float(1 / (1 + np.exp(-z_score))), 3)
    else:
        # Heuristic: remaining = (1 - progress) * average cycle time
        avg_cycle = float(np.mean(y)) if len(y) > 0 else 8.0
        remaining = round((1.0 - progress) * avg_cycle, 2)
        delay_risk = round(1.0 - progress, 3)

    return {
        "case_id": case_id,
        "current_step": step,
        "progress_pct": round(progress * 100, 1),
        "elapsed_hours": round(elapsed, 2),
        "remaining_time_hours": remaining,
        "delay_risk": delay_risk,
        "delay_risk_level": "HIGH" if delay_risk > 0.7 else "MEDIUM" if delay_risk > 0.4 else "LOW",
    }
