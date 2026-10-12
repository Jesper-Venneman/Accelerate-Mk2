"""Streaming microphone capture for push-to-talk - the one place this module touches hardware.

Design spec: Architecture/Modules/G - Kathrena Agent Core.md

Unlike a fixed-duration recording, push-to-talk doesn't know how long the question will be ahead
of time - `StreamingRecorder` accumulates audio for as long as the hotkey is held, via
sounddevice's callback-based `InputStream` rather than a blocking `sd.rec()` call.
"""

from __future__ import annotations

import logging
import threading
from typing import Protocol

import numpy as np

logger = logging.getLogger(__name__)


class Recorder(Protocol):
    """Swappable interface so tests can inject a fake recorder - no real sound card needed."""

    def start(self) -> None: ...
    def stop(self) -> np.ndarray: ...


class StreamingRecorder:
    """Default `Recorder`: mono float32 audio from the default input device, via `sounddevice`."""

    def __init__(self, sample_rate: int) -> None:
        self._sample_rate = sample_rate
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream = None

    def start(self) -> None:
        # Imported lazily so importing this module doesn't need a sound card.
        import sounddevice as sd

        with self._lock:
            self._frames = []
        self._stream = sd.InputStream(
            samplerate=self._sample_rate, channels=1, dtype="float32", callback=self._on_audio
        )
        self._stream.start()

    def _on_audio(self, indata: np.ndarray, frames: int, time_info: object, status: object) -> None:
        if status:
            logger.warning("Microphone input stream reported a status: %s", status)
        with self._lock:
            self._frames.append(indata[:, 0].copy())

    def stop(self) -> np.ndarray:
        """Stop recording and return everything captured since `start()`, sanitized."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            frames, self._frames = self._frames, []
        samples = np.concatenate(frames) if frames else np.zeros(0, dtype=np.float32)
        return sanitize(samples, self._sample_rate)


def sanitize(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    """Guard against garbage audio from a misbehaving device/driver or a stream glitch.

    Valid PCM audio is always within [-1, 1] - anything outside that (or NaN/Inf) is corrupted,
    not just loud. Treated as silence rather than raised, since a bad chunk shouldn't crash the
    listener.
    """
    cleaned = np.clip(np.nan_to_num(samples, nan=0.0, posinf=0.0, neginf=0.0), -1.0, 1.0)
    if not np.array_equal(cleaned, samples):
        logger.warning(
            "Microphone returned %d invalid/out-of-range sample(s) - check the selected input "
            "device and requested sample rate (%d Hz). Treating them as silence.",
            int(np.count_nonzero(cleaned != samples)),
            sample_rate,
        )
    return cleaned


def describe_default_input_device() -> str:
    """Best-effort description of the default input device, for startup diagnostics."""
    import sounddevice as sd

    try:
        device = sd.query_devices(kind="input")
        return f"{device['name']!r} (default samplerate {device['default_samplerate']:.0f} Hz)"
    except Exception as exc:  # purely diagnostic - must never block the listener from starting
        return f"<could not query default input device: {exc}>"
