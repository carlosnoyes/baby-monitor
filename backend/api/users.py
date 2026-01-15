"""
backend/api/users.py

Basic user management endpoints (minimal for v1).
"""

from __future__ import annotations

from flask import Flask, jsonify, request, Response

from backend.database import query_all, query_one, execute
from backend.auth.auth_utils import hash_password
from backend.auth.auth_utils import get_auth_payload


def register_routes(app: Flask) -> None:
    @app.get("/api/users")
    def list_users() -> tuple[Response, int]:
        payload = get_auth_payload(request)
        if not payload:
            return jsonify({"error": "unauthorized"}), 401
        rows = query_all("SELECT id, email, is_active, created_at FROM users ORDER BY id ASC")
        users = [
            {"id": r["id"], "email": r["email"], "is_active": bool(r["is_active"]), "created_at": r["created_at"]}
            for r in rows
        ]
        return jsonify({"users": users}), 200

    @app.post("/api/users")
    def create_user() -> tuple[Response, int]:
        payload = get_auth_payload(request)
        if not payload:
            return jsonify({"error": "unauthorized"}), 401
        data = request.get_json(silent=True) or {}
        email = data.get("email")
        password = data.get("password")
        if not email or not password:
            return jsonify({"error": "email and password required"}), 400

        existing = query_one("SELECT id FROM users WHERE email = ?", (email,))
        if existing:
            return jsonify({"error": "user already exists"}), 409

        password_hash = hash_password(str(password))
        execute(
            "INSERT INTO users (email, password_hash, is_active) VALUES (?, ?, 1)",
            (email, password_hash),
        )
        row = query_one("SELECT id, email, is_active, created_at FROM users WHERE email = ?", (email,))
        if not row:
            return jsonify({"error": "user creation failed"}), 500
        return jsonify({"user": {"id": row["id"], "email": row["email"], "is_active": bool(row["is_active"])}}), 201

    @app.post("/api/users/deactivate")
    def deactivate_user() -> tuple[Response, int]:
        payload = get_auth_payload(request)
        if not payload:
            return jsonify({"error": "unauthorized"}), 401
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id")
        if not isinstance(user_id, int):
            return jsonify({"error": "user_id required"}), 400
        execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
        return jsonify({"ok": True}), 200
