"""
backend/models.py

Lightweight data models for API and database interactions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class User:
    id: int
    email: str
    is_active: bool
    created_at: str

    @classmethod
    def from_row(cls, row: dict) -> "User":
        return cls(
            id=int(row["id"]),
            email=str(row["email"]),
            is_active=bool(row["is_active"]),
            created_at=str(row["created_at"]),
        )


@dataclass(frozen=True)
class NotificationSettings:
    user_id: int
    threshold_seconds: int
    enabled: bool
    cooldown_seconds: int
    last_notified_at: str | None

    @classmethod
    def from_row(cls, row: dict) -> "NotificationSettings":
        return cls(
            user_id=int(row["user_id"]),
            threshold_seconds=int(row["threshold_seconds"]),
            enabled=bool(row["enabled"]),
            cooldown_seconds=int(row["cooldown_seconds"]),
            last_notified_at=row["last_notified_at"],
        )


@dataclass(frozen=True)
class CryEvent:
    id: int
    started_at: str
    ended_at: str | None
    duration_seconds: int | None

    @classmethod
    def from_row(cls, row: dict) -> "CryEvent":
        return cls(
            id=int(row["id"]),
            started_at=str(row["started_at"]),
            ended_at=row["ended_at"],
            duration_seconds=row["duration_seconds"],
        )
