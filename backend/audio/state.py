"""
backend/audio/state.py

Global crying state tracker.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from threading import Lock
import time

from backend.config import settings

@dataclass(frozen=True)
class CryMinuteEvent:
    minute_start: datetime
    is_crying: bool


@dataclass(frozen=True)
class CryState:
    is_crying: bool
    current_minute_start: datetime
    current_minute_is_crying: bool
    effective_cry_minutes: int
    consecutive_quiet_minutes: int
    timeline: list[CryMinuteEvent]
    last_volume: float
    volume_threshold: float
    last_updated_at: datetime


_LOCK = Lock()
_MAX_MINUTES = 480
_TIMELINE: deque[CryMinuteEvent] = deque(maxlen=_MAX_MINUTES)
_VOLUME_WINDOW_SECONDS = 2.0
_VOLUME_SAMPLES: deque[tuple[float, float]] = deque()


def _floor_minute(value: datetime) -> datetime:
    return value.replace(second=0, microsecond=0)


_STATE = CryState(
    is_crying=False,
    current_minute_start=_floor_minute(datetime.now(timezone.utc)),
    current_minute_is_crying=False,
    effective_cry_minutes=0,
    consecutive_quiet_minutes=0,
    timeline=[],
    last_volume=0.0,
    volume_threshold=settings.audio_volume_threshold,
    last_updated_at=datetime.now(timezone.utc),
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _apply_minute(
    is_crying: bool, effective_cry_minutes: int, consecutive_quiet_minutes: int
) -> tuple[int, int]:
    if is_crying:
        return effective_cry_minutes + 1, 0
    consecutive_quiet_minutes += 1
    if consecutive_quiet_minutes >= 2:
        return 0, consecutive_quiet_minutes
    return effective_cry_minutes, consecutive_quiet_minutes


def _append_minute(minute_start: datetime, is_crying: bool) -> None:
    _TIMELINE.append(CryMinuteEvent(minute_start=minute_start, is_crying=is_crying))


def _update_volume_window(level: float) -> float:
    now_ts = time.time()
    _VOLUME_SAMPLES.append((now_ts, level))
    cutoff = now_ts - _VOLUME_WINDOW_SECONDS
    while _VOLUME_SAMPLES and _VOLUME_SAMPLES[0][0] < cutoff:
        _VOLUME_SAMPLES.popleft()
    if not _VOLUME_SAMPLES:
        return 0.0
    total = sum(sample[1] for sample in _VOLUME_SAMPLES)
    return total / len(_VOLUME_SAMPLES)


def update(is_crying: bool, volume: float | None = None, threshold: float | None = None) -> CryState:
    """
    Update global cry state based on the latest detector output.
    """
    global _STATE
    with _LOCK:
        now = _now()
        minute_start = _floor_minute(now)

        effective = _STATE.effective_cry_minutes
        quiet_streak = _STATE.consecutive_quiet_minutes
        current_minute_is_crying = _STATE.current_minute_is_crying

        new_minute = minute_start != _STATE.current_minute_start
        if new_minute:
            prev_minute = _STATE.current_minute_start
            _append_minute(prev_minute, current_minute_is_crying)
            effective, quiet_streak = _apply_minute(
                current_minute_is_crying, effective, quiet_streak
            )

            gap_minutes = int((minute_start - prev_minute).total_seconds() // 60) - 1
            for i in range(gap_minutes):
                gap_start = prev_minute + timedelta(minutes=i + 1)
                _append_minute(gap_start, False)
                effective, quiet_streak = _apply_minute(False, effective, quiet_streak)

            current_minute_is_crying = False

        window_level = _STATE.last_volume
        if volume is not None:
            window_level = _update_volume_window(float(volume))

        threshold_value = _STATE.volume_threshold if threshold is None else float(threshold)
        is_crying_effective = window_level >= threshold_value

        if new_minute:
            current_minute_is_crying = is_crying_effective
        else:
            current_minute_is_crying = current_minute_is_crying or is_crying_effective

        timeline = list(_TIMELINE)
        timeline.append(
            CryMinuteEvent(minute_start=minute_start, is_crying=current_minute_is_crying)
        )

        _STATE = CryState(
            is_crying=is_crying_effective,
            current_minute_start=minute_start,
            current_minute_is_crying=current_minute_is_crying,
            effective_cry_minutes=effective,
            consecutive_quiet_minutes=quiet_streak,
            timeline=timeline[-_MAX_MINUTES:],
            last_volume=window_level,
            volume_threshold=threshold_value,
            last_updated_at=now,
        )
        return _STATE


def get_state() -> CryState:
    """
    Read the current cry state.
    """
    with _LOCK:
        return _STATE
