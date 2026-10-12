"""Text-to-speech synthesis for Module K, behind a swappable interface.

Design spec: Architecture/Modules/K - Chat Interface.md (Voice output)
Engine choice (Kokoro-82M): Architecture/Decisions Log.md, Round 16.
"""

from __future__ import annotations

import warnings
from typing import Protocol

import numpy as np

from kathrena.chat_interface.audio import AudioClip
from kathrena.chat_interface.config import VoiceOutputConfig

_KOKORO_SAMPLE_RATE = 24000


class TextToSpeech(Protocol):
    """Swappable interface so the TTS engine can change without touching callers."""

    def synthesize(self, text: str) -> AudioClip: ...


class KokoroTextToSpeech:
    """Default `TextToSpeech`: Kokoro-82M, running locally via `KPipeline`."""

    def __init__(self, config: VoiceOutputConfig) -> None:
        # Imported lazily so importing this module doesn't require kokoro/torch unless used.
        from kokoro import KPipeline

        # repo_id silences Kokoro's own "defaulting repo_id" nag; the warnings filter silences
        # deprecation/dropout noise from Kokoro's own internal torch usage, not our code.
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            warnings.filterwarnings("ignore", category=FutureWarning)
            self._pipeline = KPipeline(
                lang_code=config.kokoro_lang_code, repo_id="hexgrad/Kokoro-82M"
            )
        self._voice = config.kokoro_voice

    def synthesize(self, text: str) -> AudioClip:
        chunks = [audio for _, _, audio in self._pipeline(text, voice=self._voice)]
        if not chunks:
            return AudioClip(samples=np.zeros(0, dtype=np.float32), sample_rate=_KOKORO_SAMPLE_RATE)
        samples = np.concatenate([np.asarray(chunk, dtype=np.float32) for chunk in chunks])
        return AudioClip(samples=samples, sample_rate=_KOKORO_SAMPLE_RATE)
