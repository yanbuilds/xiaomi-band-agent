"""Deterministic local state inference for Band health samples.

This deliberately reports probabilities and evidence instead of claiming that a
watch can directly observe posture.  Samples are normalized dictionaries with
``timestamp``, ``metric`` and ``value`` fields; ``steps`` may be interval or
cumulative data and is treated as a non-negative activity signal.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import median
from typing import Any, Iterable


STATES = ("SLEEPING", "AWAKE_IN_BED", "STATIONARY", "WALKING", "EXERCISING", "UNKNOWN")


@dataclass(frozen=True)
class StateResult:
    state: str
    confidence: float
    started_at: int | None
    evidence: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _samples(samples: Iterable[dict[str, Any]], metric: str, start: int, end: int) -> list[dict[str, Any]]:
    return [s for s in samples if s.get("metric") == metric and start <= int(s.get("timestamp", 0)) <= end]


def _activity(samples: list[dict[str, Any]], start: int, end: int) -> float:
    values = [max(0.0, float(s.get("value", 0))) for s in _samples(samples, "steps", start, end)]
    return sum(values)


def _heart_rate(samples: list[dict[str, Any]], start: int, end: int) -> float | None:
    values = [float(s["value"]) for s in _samples(samples, "heart_rate", start, end)]
    return float(median(values)) if values else None


def infer_state(
    *,
    now: int,
    samples: Iterable[dict[str, Any]],
    sleep: dict[str, Any] | None = None,
    resting_heart_rate: float | None = None,
) -> StateResult:
    """Infer a coarse state from a short local window.

    The result is suitable for a rule engine and Grok context, not medical or
    posture detection.  A missing/invalid sleep record never causes a crash.
    """
    rows = list(samples)
    sleep_start = int(sleep["start"]) if sleep and sleep.get("start") else None
    sleep_end = int(sleep["end"]) if sleep and sleep.get("end") else None

    if sleep_start is not None and sleep_end is not None and sleep_start <= now < sleep_end:
        return StateResult("SLEEPING", 0.94, sleep_start, {"sleep_end": sleep_end})

    if sleep_end is not None and now >= sleep_end:
        since_wake = max(0, now - sleep_end)
        steps = _activity(rows, sleep_end, now)
        hr = _heart_rate(rows, sleep_end, now)
        if since_wake <= 90 * 60 and steps < 50:
            confidence = min(0.95, 0.70 + (0.20 if since_wake >= 20 * 60 else 0.0))
            return StateResult("AWAKE_IN_BED", confidence, sleep_end, {
                "sleep_end": sleep_end, "minutes_since_sleep_end": since_wake // 60,
                "steps_since_sleep_end": round(steps), "heart_rate": hr,
            })

    recent_start = now - 15 * 60
    steps_15m = _activity(rows, recent_start, now)
    hr = _heart_rate(rows, recent_start, now)
    baseline = resting_heart_rate or 60.0
    if steps_15m >= 100 and hr is not None and (hr >= 110 or hr >= baseline + 25):
        return StateResult("EXERCISING", min(0.96, 0.68 + min(0.25, steps_15m / 2000)), recent_start, {
            "steps_15m": round(steps_15m), "heart_rate": hr, "resting_heart_rate": baseline,
        })
    if steps_15m >= 20:
        return StateResult("WALKING", min(0.93, 0.60 + min(0.28, steps_15m / 500)), recent_start, {
            "steps_15m": round(steps_15m), "heart_rate": hr,
        })
    if _activity(rows, now - 20 * 60, now) < 10:
        return StateResult("STATIONARY", 0.74, now - 20 * 60, {
            "steps_20m": round(_activity(rows, now - 20 * 60, now)), "heart_rate": hr,
        })
    return StateResult("UNKNOWN", 0.35, None, {"steps_15m": round(steps_15m), "heart_rate": hr})


def possible_oversleep(
    *,
    now: int,
    latest_wake_at: int | None,
    state: StateResult,
    workday: bool = True,
    grace_minutes: int = 10,
) -> dict[str, Any] | None:
    """Return a Grok-ready event when the configured wake deadline was missed."""
    if not workday or latest_wake_at is None or now <= latest_wake_at + grace_minutes * 60:
        return None
    if state.state not in {"AWAKE_IN_BED", "SLEEPING", "STATIONARY"}:
        return None
    late_minutes = (now - latest_wake_at) // 60
    return {
        "event": "possible_oversleep",
        "confidence": round(min(0.97, state.confidence * 0.9), 2),
        "priority": "high" if late_minutes >= 30 else "normal",
        "late_minutes": late_minutes,
        "state": state.as_dict(),
        "recommended_options": ["awake", "snooze_10m", "day_off"],
    }


__all__ = ["STATES", "StateResult", "infer_state", "possible_oversleep"]
