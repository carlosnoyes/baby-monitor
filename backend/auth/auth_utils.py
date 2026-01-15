"""
backend/auth/auth_utils.py

Password hashing and lightweight token helpers.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from flask import Request

from backend.config import settings


_HASH_ITERATIONS = 200_000


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256.
    Returns: salt$hash (both hex).
    """
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _HASH_ITERATIONS)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except Exception:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _HASH_ITERATIONS)
    return hmac.compare_digest(dk, expected)


def create_token(payload: dict[str, Any]) -> str:
    """
    Create a simple signed token with exp (seconds since epoch).
    """
    header = {"alg": "HS256", "typ": "JWT"}
    exp = int(time.time()) + (settings.jwt_exp_minutes * 60)
    body = {**payload, "exp": exp}

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    body_b64 = _b64url_encode(json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{header_b64}.{body_b64}".encode("ascii")
    signature = hmac.new(settings.jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)
    return f"{header_b64}.{body_b64}.{sig_b64}"


def verify_token(token: str) -> dict[str, Any] | None:
    try:
        header_b64, body_b64, sig_b64 = token.split(".", 2)
    except ValueError:
        return None

    signing_input = f"{header_b64}.{body_b64}".encode("ascii")
    expected_sig = hmac.new(settings.jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(_b64url_encode(expected_sig), sig_b64):
        return None

    try:
        body = json.loads(_b64url_decode(body_b64))
    except Exception:
        return None

    exp = body.get("exp")
    if not isinstance(exp, int):
        return None
    if exp < int(time.time()):
        return None

    return body


def get_auth_payload(request: Request) -> dict[str, Any] | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:].strip()
    if not token:
        return None
    return verify_token(token)
