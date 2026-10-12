"""Shared audio-clip type for Module K's voice pipeline (Kokoro -> voice effects -> playback).

Design spec: Architecture/Modules/K - Chat Interface.md
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AudioClip:
    """Mono float32 PCM audio - the type every stage of Module K's voice-output pipeline passes."""

    samples: np.ndarray
    sample_rate: int


def to_wav_bytes(clip: AudioClip) -> bytes:
    """Encode `clip` as an in-memory WAV file, for `cl.Audio(content=...)`."""
    import soundfile as sf  # Imported lazily so importing this module doesn't require it.

    buffer = io.BytesIO()
    sf.write(buffer, clip.samples, clip.sample_rate, format="WAV")
    return buffer.getvalue()
