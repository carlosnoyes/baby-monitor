"""
backend/auth/routes.py

Auth endpoints: login + register.
"""

from __future__ import annotations

from flask import Flask, jsonify, request, Response

from backend.database import query_one, execute
from backend.auth.auth_utils import hash_password, verify_password, create_token


def register_routes(app: Flask) -> None:
    @app.post("/auth/register")
    def register() -> tuple[Response, int]:
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
        row = query_one("SELECT id, email FROM users WHERE email = ?", (email,))
        if not row:
            return jsonify({"error": "user creation failed"}), 500
        token = create_token({"sub": row["id"], "email": row["email"]})
        return jsonify({"token": token, "user": {"id": row["id"], "email": row["email"]}}), 201

    @app.post("/auth/login")
    def login() -> tuple[Response, int]:
        data = request.get_json(silent=True) or {}
        email = data.get("email")
        password = data.get("password")
        if not email or not password:
            return jsonify({"error": "email and password required"}), 400

        row = query_one("SELECT id, email, password_hash, is_active FROM users WHERE email = ?", (email,))
        if not row or not row["is_active"]:
            return jsonify({"error": "invalid credentials"}), 401
        if not verify_password(str(password), row["password_hash"]):
            return jsonify({"error": "invalid credentials"}), 401

        token = create_token({"sub": row["id"], "email": row["email"]})
        return jsonify({"token": token, "user": {"id": row["id"], "email": row["email"]}}), 200
