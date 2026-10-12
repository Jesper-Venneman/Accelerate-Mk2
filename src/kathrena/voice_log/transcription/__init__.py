"""Module B: Transcription.

Design spec: Architecture/Modules/B - Transcription Module.md

Converts raw audio into text for `kathrena.voice_log.project_router` (Module C),
using openai-whisper behind a swappable interface.
"""

from kathrena.voice_log.transcription.whisper_transcriber import (
    Transcriber,
    TranscriptionResult,
    WhisperTranscriber,
)

__all__ = ["Transcriber", "TranscriptionResult", "WhisperTranscriber"]
