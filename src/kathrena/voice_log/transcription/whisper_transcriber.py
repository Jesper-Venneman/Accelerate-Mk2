"""Speech-to-text transcription behind a swappable interface.

Design spec: Architecture/Modules/B - Transcription Module.md
Engine choice (openai-whisper): Architecture/Decisions Log.md, Round 15.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from kathrena.config import PipelineConfig


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str | None = None


class Transcriber(Protocol):
    """Swappable speech-to-text interface so the engine can change without touching callers."""

    def transcribe(self, audio_path: Path) -> TranscriptionResult: ...


class WhisperTranscriber:
    """Default `Transcriber`, backed by the original openai-whisper package.

    Requires `ffmpeg` on PATH. Swapped in from faster-whisper (Decisions Log Round 15) after its
    CTranslate2 GPU backend repeatedly failed to find its CUDA libraries on this machine, even
    after installing the `nvidia-cublas-cu12`/`nvidia-cudnn-cu12` packages it needs - this is the
    same package Mk1 used successfully.
    """

    def __init__(self, config: PipelineConfig) -> None:
        import whisper  # Imported lazily so importing this module doesn't require it unless used.

        self._model = whisper.load_model(config.whisper_model_size, device=config.whisper_device)
        # openai-whisper's decoder registers stateful KV-cache hooks on the model during a call -
        # concurrent transcribe() calls on the same instance corrupt each other's cache and crash
        # with tensor shape mismatches. Serializes any callers sharing this instance across
        # threads (e.g. kathrena.agent_core.push_to_talk, whose transcriptions run on their own
        # background threads); a no-op cost when called from a single thread, as the voice-log
        # pipeline does.
        self._lock = threading.Lock()

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        with self._lock:
            result = self._model.transcribe(str(audio_path))
        return TranscriptionResult(text=result["text"].strip(), language=result.get("language"))

