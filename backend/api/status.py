"""
backend/api/status.py

Status API for current cry state.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from flask import jsonify, Flask, Response, request

from backend.audio.state import get_state
from backend.config import settings
from backend.database import query_all


def register_routes(app: Flask) -> None:
    @app.get("/api/status")
    def status() -> tuple[Response, int]:
        state = get_state()
        payload = {
            "is_crying": state.is_crying,
            "current_minute_is_crying": state.current_minute_is_crying,
            "effective_cry_minutes": state.effective_cry_minutes,
            "consecutive_quiet_minutes": state.consecutive_quiet_minutes,
            "volume_level": state.last_volume,
            "volume_threshold": state.volume_threshold,
            "timeline": [
                {
                    "minute_start": event.minute_start.isoformat(),
                    "is_crying": event.is_crying,
                }
                for event in state.timeline
            ],
            "last_updated_at": state.last_updated_at.isoformat(),
        }
        return jsonify(payload), 200

    @app.get("/api/volume")
    def volume() -> tuple[Response, int]:
        minutes = request.args.get("minutes", type=int) or 15
        minutes = max(1, min(minutes, 8 * 60))
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        rows = query_all(
            """
            SELECT recorded_at, rms
            FROM volume_samples
            WHERE recorded_at >= ?
            ORDER BY recorded_at ASC
            """,
            (cutoff.isoformat(),),
        )
        samples = [{"t": row["recorded_at"], "rms": row["rms"]} for row in rows]
        payload = {
            "samples": samples,
            "threshold": settings.audio_volume_threshold,
            "minutes": minutes,
        }
        return jsonify(payload), 200
