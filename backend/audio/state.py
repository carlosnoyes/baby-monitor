"""
backend/audio/state.py

Global crying state tracker.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock


@dataclass(frozen=True)
class CryState:
    is_crying: bool
    started_at: datetime | None
    duration_seconds: int
    last_updated_at: datetime


_LOCK = Lock()
_STATE = CryState(
    is_crying=False,
    started_at=None,
    duration_seconds=0,
    last_updated_at=datetime.now(timezone.utc),
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def update(is_crying: bool) -> CryState:
    """
    Update global cry state based on the latest detector output.
    """
    global _STATE
    with _LOCK:
        now = _now()
        if is_crying:
            if _STATE.started_at is None:
                started_at = now
            else:
                started_at = _STATE.started_at
            duration = int((now - started_at).total_seconds())
            _STATE = CryState(
                is_crying=True,
                started_at=started_at,
                duration_seconds=duration,
                last_updated_at=now,
            )
        else:
            _STATE = CryState(
                is_crying=False,
                started_at=None,
                duration_seconds=0,
                last_updated_at=now,
            )
        return _STATE


def get_state() -> CryState:
    """
    Read the current cry state.
    """
    with _LOCK:
        return _STATE
