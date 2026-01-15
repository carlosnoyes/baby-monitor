"""
backend/notifications/push.py

Firebase Cloud Messaging (legacy HTTP) push sender.
"""

from __future__ import annotations

import json
import logging
from urllib import request

from backend.config import settings


logger = logging.getLogger("baby_monitor.notifications")

_FCM_LEGACY_ENDPOINT = "https://fcm.googleapis.com/fcm/send"


def send_push(token: str, title: str, body: str) -> None:
    if not settings.fcm_server_key:
        raise RuntimeError("FCM_SERVER_KEY not configured")

    if not token:
        logger.warning("Skipping push: device token is empty")
        return

    payload = {
        "to": token,
        "notification": {"title": title, "body": body},
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        _FCM_LEGACY_ENDPOINT,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"key={settings.fcm_server_key}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=10) as resp:
            if resp.status >= 400:
                logger.error("FCM error: %s %s", resp.status, resp.read().decode("utf-8", "ignore"))
    except Exception as exc:
        logger.error("FCM push failed: %s", exc)
