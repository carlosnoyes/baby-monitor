"""
backend/notifications/dispatcher.py

Decide who should be notified based on cry state and user settings.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Iterable

from backend.config import settings
from backend.database import query_all, execute
from backend.audio.state import CryState


logger = logging.getLogger("baby_monitor.notifications")


@dataclass(frozen=True)
class NotificationCandidate:
    user_id: int
    email: str
    threshold_seconds: int
    cooldown_seconds: int
    last_notified_at: datetime | None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_candidates() -> list[NotificationCandidate]:
    rows = query_all(
        """
        SELECT u.id AS user_id,
               u.email AS email,
               ns.threshold_seconds AS threshold_seconds,
               ns.cooldown_seconds AS cooldown_seconds,
               ns.last_notified_at AS last_notified_at
        FROM users u
        JOIN notification_settings ns ON ns.user_id = u.id
        WHERE u.is_active = 1 AND ns.enabled = 1
        """
    )
    candidates = []
    for row in rows:
        candidates.append(
            NotificationCandidate(
                user_id=row["user_id"],
                email=row["email"],
                threshold_seconds=row["threshold_seconds"],
                cooldown_seconds=row["cooldown_seconds"],
                last_notified_at=_parse_dt(row["last_notified_at"]),
            )
        )
    return candidates


def _cooldown_ok(candidate: NotificationCandidate, now: datetime) -> bool:
    cooldown = candidate.cooldown_seconds or settings.notify_cooldown_seconds
    if not candidate.last_notified_at:
        return True
    return (now - candidate.last_notified_at).total_seconds() >= cooldown


def mark_notified(user_id: int, when: datetime | None = None) -> None:
    ts = (when or _now()).isoformat()
    execute(
        "UPDATE notification_settings SET last_notified_at = ? WHERE user_id = ?",
        (ts, user_id),
    )


def evaluate_notifications(state: CryState) -> list[int]:
    """
    Return list of user_ids that were notified.
    """
    if not state.is_crying:
        return []

    now = _now()
    notified: list[int] = []
    for candidate in _load_candidates():
        if state.duration_seconds < candidate.threshold_seconds:
            continue
        if not _cooldown_ok(candidate, now):
            continue
        _send_notification(candidate, state)
        mark_notified(candidate.user_id, now)
        notified.append(candidate.user_id)
    return notified


def _send_notification(candidate: NotificationCandidate, state: CryState) -> None:
    if not settings.fcm_enabled:
        logger.info(
            "Notify user %s (%s): crying for %ss",
            candidate.user_id,
            candidate.email,
            state.duration_seconds,
        )
        return

    try:
        from backend.notifications.push import send_push
    except Exception as exc:
        logger.error("Push notification failed to import: %s", exc)
        return

    title = "Baby is crying"
    body = f"Crying for {state.duration_seconds} seconds."
    tokens = query_all("SELECT token FROM device_tokens WHERE user_id = ?", (candidate.user_id,))
    if not tokens:
        logger.warning("No device tokens for user %s", candidate.user_id)
        return
    for row in tokens:
        send_push(row["token"], title, body)
