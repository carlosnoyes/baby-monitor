"""
backend/api/settings.py

User notification settings API.
"""

from __future__ import annotations

from flask import Flask, jsonify, request, Response

from backend.database import query_one, execute
from backend.auth.auth_utils import get_auth_payload


def _get_user(user_id: int) -> dict | None:
    row = query_one("SELECT id, email, is_active FROM users WHERE id = ?", (user_id,))
    if not row:
        return None
    return {"id": row["id"], "email": row["email"], "is_active": row["is_active"]}


def _get_settings(user_id: int) -> dict | None:
    row = query_one(
        """
        SELECT user_id, threshold_seconds, enabled, cooldown_seconds
        FROM notification_settings
        WHERE user_id = ?
        """,
        (user_id,),
    )
    if not row:
        return None
    return {
        "user_id": row["user_id"],
        "threshold_seconds": row["threshold_seconds"],
        "enabled": bool(row["enabled"]),
        "cooldown_seconds": row["cooldown_seconds"],
    }


def _ensure_settings(user_id: int) -> dict:
    existing = _get_settings(user_id)
    if existing:
        return existing
    execute(
        """
        INSERT INTO notification_settings (user_id, threshold_seconds, enabled, cooldown_seconds)
        VALUES (?, 20, 1, 60)
        """,
        (user_id,),
    )
    return _get_settings(user_id) or {
        "user_id": user_id,
        "threshold_seconds": 20,
        "enabled": True,
        "cooldown_seconds": 60,
    }


def register_routes(app: Flask) -> None:
    @app.get("/api/settings")
    def get_settings() -> tuple[Response, int]:
        payload = get_auth_payload(request)
        if not payload:
            return jsonify({"error": "unauthorized"}), 401
        token_user_id = payload.get("sub")
        if not isinstance(token_user_id, int):
            return jsonify({"error": "invalid token"}), 401

        user_id = request.args.get("user_id", type=int) or token_user_id
        if user_id != token_user_id:
            return jsonify({"error": "forbidden"}), 403
        if not _get_user(user_id):
            return jsonify({"error": "user not found"}), 404
        return jsonify(_ensure_settings(user_id)), 200

    @app.post("/api/settings")
    def update_settings() -> tuple[Response, int]:
        payload = get_auth_payload(request)
        if not payload:
            return jsonify({"error": "unauthorized"}), 401
        token_user_id = payload.get("sub")
        if not isinstance(token_user_id, int):
            return jsonify({"error": "invalid token"}), 401

        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id", token_user_id)
        if not isinstance(user_id, int):
            return jsonify({"error": "user_id is required"}), 400
        if user_id != token_user_id:
            return jsonify({"error": "forbidden"}), 403
        if not _get_user(user_id):
            return jsonify({"error": "user not found"}), 404

        threshold_seconds = data.get("threshold_seconds")
        enabled = data.get("enabled")
        cooldown_seconds = data.get("cooldown_seconds")

        if threshold_seconds is None and enabled is None and cooldown_seconds is None:
            return jsonify({"error": "no settings provided"}), 400

        current = _ensure_settings(user_id)
        new_threshold = (
            int(threshold_seconds) if threshold_seconds is not None else current["threshold_seconds"]
        )
        new_enabled = bool(enabled) if enabled is not None else current["enabled"]
        new_cooldown = int(cooldown_seconds) if cooldown_seconds is not None else current["cooldown_seconds"]

        execute(
            """
            UPDATE notification_settings
            SET threshold_seconds = ?, enabled = ?, cooldown_seconds = ?
            WHERE user_id = ?
            """,
            (new_threshold, int(new_enabled), new_cooldown, user_id),
        )

        return jsonify(_get_settings(user_id)), 200
