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
            "started_at": state.started_at.isoformat() if state.started_at else None,
            "duration_seconds": state.duration_seconds,
            "last_updated_at": state.last_updated_at.isoformat(),
        }
        return jsonify(payload), 200
