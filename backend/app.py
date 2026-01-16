"""
backend/app.py

App entry point for the Baby Monitor backend.
"""

from __future__ import annotations

from threading import Thread
from datetime import datetime, timezone
import time
import logging
from typing import Callable, Any

from flask import Flask, send_from_directory

from backend.config import settings, ensure_runtime_dirs
from backend.database import execute
from pathlib import Path


logger = logging.getLogger("baby_monitor")


def _try_call(module_path: str, func_name: str, *args: Any) -> None:
    try:
        module = __import__(module_path, fromlist=[func_name])
        func = getattr(module, func_name)
    except Exception as exc:
        logger.warning("Skipping %s.%s: %s", module_path, func_name, exc)
        return
    try:
        func(*args)
    except Exception as exc:
        logger.error("Failed running %s.%s: %s", module_path, func_name, exc)


def _configure_logging() -> None:
    logging.basicConfig(level=settings.log_level.upper())


def register_routes(app: Flask) -> None:
    _try_call("backend.api.status", "register_routes", app)
    _try_call("backend.api.settings", "register_routes", app)
    _try_call("backend.api.users", "register_routes", app)
    _try_call("backend.api.devices", "register_routes", app)
    _try_call("backend.auth.routes", "register_routes", app)


def _build_audio_callback() -> Callable[[bytes], None]:
    def on_audio_chunk(audio_chunk: bytes) -> None:
        from backend.audio.detector import analyze_chunk
        from backend.audio.state import update
        from backend.notifications.dispatcher import evaluate_notifications

        try:
            crying, level = analyze_chunk(audio_chunk)
            state = update(crying, volume=level, threshold=settings.audio_volume_threshold)
            evaluate_notifications(state)
        except Exception as exc:
            logger.error("Audio processing failed: %s", exc)

    return on_audio_chunk


def start_audio_listener() -> None:
    try:
        from backend.audio.listener import start_listening
    except Exception as exc:
        logger.warning("Audio listener not started: %s", exc)
        return

    callback = _build_audio_callback()
    thread = Thread(target=start_listening, args=(callback,), daemon=True)
    thread.start()


def start_volume_logger() -> None:
    def volume_loop() -> None:
        from backend.audio.state import get_state

        while True:
            state = get_state()
            timestamp = datetime.now(timezone.utc).isoformat()
            execute(
                "INSERT INTO volume_samples (recorded_at, rms) VALUES (?, ?)",
                (timestamp, float(state.last_volume)),
            )
            time.sleep(1)

    thread = Thread(target=volume_loop, daemon=True)
    thread.start()


def create_app() -> Flask:
    _configure_logging()
    ensure_runtime_dirs()

    web_root = Path(__file__).resolve().parents[1] / settings.web_dir
    app = Flask(__name__, static_folder=str(web_root) if settings.serve_web else None)
    if settings.serve_web:
        @app.get("/")
        def index() -> object:
            return send_from_directory(str(web_root), "dashboard.html")

        @app.get("/<path:filename>")
        def static_files(filename: str) -> object:
            return send_from_directory(str(web_root), filename)

    _try_call("backend.database", "init_db")
    register_routes(app)
    start_audio_listener()
    start_volume_logger()

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host=settings.host, port=settings.port)
