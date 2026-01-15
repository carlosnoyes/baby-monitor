"""
backend/api/devices.py

Device token registration for push notifications.
"""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Flask, jsonify, request, Response

from backend.auth.auth_utils import get_auth_payload
from backend.database import execute, query_one


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def register_routes(app: Flask) -> None:
    @app.post("/api/devices/register")
    def register_device() -> tuple[Response, int]:
        payload = get_auth_payload(request)
        if not payload:
            return jsonify({"error": "unauthorized"}), 401
        user_id = payload.get("sub")
        if not isinstance(user_id, int):
            return jsonify({"error": "invalid token"}), 401

        data = request.get_json(silent=True) or {}
        token = data.get("token")
        platform = data.get("platform")
        if not token or not isinstance(token, str):
            return jsonify({"error": "token is required"}), 400

        existing = query_one("SELECT id FROM device_tokens WHERE token = ?", (token,))
        if existing:
            execute(
                """
                UPDATE device_tokens
                SET user_id = ?, platform = ?, last_seen_at = ?
                WHERE token = ?
                """,
                (user_id, platform, _now_iso(), token),
            )
        else:
            execute(
                """
                INSERT INTO device_tokens (user_id, token, platform, last_seen_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, token, platform, _now_iso()),
            )

        return jsonify({"ok": True}), 200
