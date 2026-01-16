"""
backend/database.py

SQLite helpers for the Baby Monitor backend.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from backend.config import settings, ensure_runtime_dirs


_CONNECTION: sqlite3.Connection | None = None


def get_db() -> sqlite3.Connection:
    global _CONNECTION
    if _CONNECTION is None:
        ensure_runtime_dirs()
        db_path = Path(settings.database_path)
        _CONNECTION = sqlite3.connect(db_path, check_same_thread=False)
        _CONNECTION.row_factory = sqlite3.Row
    return _CONNECTION


def init_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS notification_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            threshold_seconds INTEGER NOT NULL DEFAULT 20,
            enabled INTEGER NOT NULL DEFAULT 1,
            cooldown_seconds INTEGER NOT NULL DEFAULT 60,
            last_notified_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS cry_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            duration_seconds INTEGER
        );

        CREATE TABLE IF NOT EXISTS volume_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at TEXT NOT NULL,
            rms REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS device_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            platform TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )
    db.commit()


Params = Sequence[Any] | Mapping[str, Any]


def execute(query: str, params: Params = ()) -> sqlite3.Cursor:
    db = get_db()
    cur = db.execute(query, params)
    db.commit()
    return cur


def query_one(query: str, params: Params = ()) -> sqlite3.Row | None:
    cur = execute(query, params)
    return cur.fetchone()


def query_all(query: str, params: Params = ()) -> list[sqlite3.Row]:
    cur = execute(query, params)
    return list(cur.fetchall())
