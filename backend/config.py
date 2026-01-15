"""
backend/config.py

Central configuration for the Baby Monitor project.

Usage:
    from backend.config import settings

Design goals:
- Keep secrets OUT of git (use .env on the Pi).
- Provide safe defaults for local dev.
- One place to change key parameters (audio + server + notifications).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


def _load_dotenv(dotenv_path: Path) -> None:
    """
    Minimal .env loader (no external dependency).
    Reads KEY=VALUE lines and injects into os.environ if not already set.
    Supports comments (# ...) and blank lines.
    """
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Do not override values that were already set in the environment
        os.environ.setdefault(key, value)


def _env(key: str, default: str | None = None) -> str | None:
    v = os.environ.get(key)
    return v if v is not None else default


def _env_int(key: str, default: int) -> int:
    v = os.environ.get(key)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        raise ValueError(f"Environment variable {key} must be an integer, got: {v!r}")


def _env_float(key: str, default: float) -> float:
    v = os.environ.get(key)
    if v is None:
        return default
    try:
        return float(v)
    except ValueError:
        raise ValueError(f"Environment variable {key} must be a float, got: {v!r}")


def _env_bool(key: str, default: bool) -> bool:
    v = os.environ.get(key)
    if v is None:
        return default
    v_norm = v.strip().lower()
    if v_norm in ("1", "true", "yes", "y", "on"):
        return True
    if v_norm in ("0", "false", "no", "n", "off"):
        return False
    raise ValueError(f"Environment variable {key} must be boolean-like, got: {v!r}")


@dataclass(frozen=True)
class Settings:
    # --- App / server ---
    app_name: str = "baby-monitor"
    env: str = "dev"  # dev | prod
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # --- Security ---
    # In production, set a strong random value in .env
    jwt_secret: str = "dev-change-me"
    jwt_exp_minutes: int = 60 * 24 * 7  # 7 days

    # --- Database ---
    database_path: str = "data/baby_monitor.sqlite3"

    # --- Audio ---
    audio_sample_rate: int = 44100
    audio_channels: int = 1
    audio_chunk_seconds: float = 0.5

    # Volume threshold used by a simple detector (can improve later)
    # This is intentionally a tunable knob.
    audio_volume_threshold: float = 0.01

    # --- Notification behavior ---
    # Prevent spamming a user repeatedly while the baby is continuously crying.
    notify_cooldown_seconds: int = 60

    # --- Firebase Push Notifications ---
    # For FCM HTTP v1 you typically use a service account; for legacy you use a server key.
    # We'll support a simple server-key approach first.
    fcm_enabled: bool = False
    fcm_server_key: str | None = None

    # --- Misc ---
    # If true, the server can serve the static web folder.
    serve_web: bool = True
    web_dir: str = "web"


def load_settings() -> Settings:
    """
    Load settings from environment variables (and optional .env).
    Priority:
        OS environment > .env file > defaults
    """
    # Look for .env in repo root or backend/.env
    repo_root = Path(__file__).resolve().parents[1]
    dotenv_candidates = [
        repo_root / ".env",
        repo_root / "backend" / ".env",
    ]
    for p in dotenv_candidates:
        _load_dotenv(p)

    return Settings(
        # App/server
        app_name=_env("APP_NAME", "baby-monitor") or "baby-monitor",
        env=_env("ENV", "dev") or "dev",
        host=_env("HOST", "0.0.0.0") or "0.0.0.0",
        port=_env_int("PORT", 8000),
        log_level=_env("LOG_LEVEL", "INFO") or "INFO",

        # Security
        jwt_secret=_env("JWT_SECRET", "dev-change-me") or "dev-change-me",
        jwt_exp_minutes=_env_int("JWT_EXP_MINUTES", 60 * 24 * 7),

        # DB
        database_path=_env("DATABASE_PATH", "data/baby_monitor.sqlite3") or "data/baby_monitor.sqlite3",

        # Audio
        audio_sample_rate=_env_int("AUDIO_SAMPLE_RATE", 44100),
        audio_channels=_env_int("AUDIO_CHANNELS", 1),
        audio_chunk_seconds=_env_float("AUDIO_CHUNK_SECONDS", 0.5),
        audio_volume_threshold=_env_float("AUDIO_VOLUME_THRESHOLD", 0.01),

        # Notifications
        notify_cooldown_seconds=_env_int("NOTIFY_COOLDOWN_SECONDS", 60),

        # FCM
        fcm_enabled=_env_bool("FCM_ENABLED", False),
        fcm_server_key=_env("FCM_SERVER_KEY", None),

        # Web
        serve_web=_env_bool("SERVE_WEB", True),
        web_dir=_env("WEB_DIR", "web") or "web",
    )


# Singleton-style settings import
settings = load_settings()


def ensure_runtime_dirs() -> None:
    """
    Create runtime directories needed by the app (like data/).
    Safe to call multiple times.
    """
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
