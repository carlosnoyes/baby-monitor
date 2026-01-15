"""
backend/audio/detector.py

Simple audio detector (volume threshold). Replace with ML later.
"""

from __future__ import annotations

from array import array
from typing import Iterable

from backend.config import settings


def _rms_from_int16(samples: Iterable[int]) -> float:
    total = 0.0
    count = 0
    for s in samples:
        total += float(s) * float(s)
        count += 1
    if count == 0:
        return 0.0
    mean_square = total / count
    return mean_square ** 0.5


def is_crying(audio_chunk: bytes | Iterable[int]) -> bool:
    """
    Return True if the audio chunk likely contains crying.

    Expects 16-bit PCM mono audio for bytes input.
    """
    if isinstance(audio_chunk, (bytes, bytearray, memoryview)):
        if len(audio_chunk) < 2:
            return False
        samples = array("h")
        samples.frombytes(bytes(audio_chunk))
        rms = _rms_from_int16(samples)
        normalized = rms / 32768.0
    else:
        rms = _rms_from_int16(audio_chunk)
        normalized = rms / 32768.0

    return normalized >= settings.audio_volume_threshold
