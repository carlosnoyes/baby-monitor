"""
backend/api/status.py

Status API for current cry state.
"""

from __future__ import annotations

from flask import jsonify, Flask, Response

from backend.audio.state import get_state


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
