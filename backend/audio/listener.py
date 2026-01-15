"""
backend/audio/listener.py

Microphone listener. Uses PyAudio if available.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from backend.config import settings


logger = logging.getLogger("baby_monitor.audio")


def start_listening(callback: Callable[[bytes], None]) -> None:
    """
    Capture microphone audio and feed chunks to callback.

    This runs a blocking loop. Call from a background thread.
    """
    try:
        import pyaudio  # type: ignore
    except Exception as exc:
        raise RuntimeError("PyAudio is required for microphone capture") from exc

    chunk_frames = int(settings.audio_sample_rate * settings.audio_chunk_seconds)
    if chunk_frames <= 0:
        raise ValueError("AUDIO_CHUNK_SECONDS must be > 0")

    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=settings.audio_channels,
        rate=settings.audio_sample_rate,
        input=True,
        frames_per_buffer=chunk_frames,
    )

    logger.info("Audio listener started: %s Hz, %s ch", settings.audio_sample_rate, settings.audio_channels)
    try:
        while True:
            try:
                data = stream.read(chunk_frames, exception_on_overflow=False)
            except Exception as exc:
                logger.warning("Audio read failed: %s", exc)
                time.sleep(0.05)
                continue
            if not data:
                time.sleep(0.01)
                continue
            try:
                callback(data)
            except Exception as exc:
                logger.error("Audio callback failed: %s", exc)
                time.sleep(0.05)
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()
