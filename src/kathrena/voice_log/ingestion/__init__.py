"""Module A: Ingestion and Sync Layer.

Design spec: Architecture/Modules/A - Ingestion and Sync Layer.md

Watches a synced drop folder for new voice-log audio and hands new files off to
`kathrena.voice_log.transcription` (Module B). Source-agnostic by design - phone,
desktop, or a future hardware recorder all just need to drop a .wav into the folder.
"""

from kathrena.voice_log.ingestion.watcher import (
    NewVoiceLogHandler,
    VoiceLogWatcher,
    is_voice_log,
    parse_recorded_at,
)

__all__ = ["NewVoiceLogHandler", "VoiceLogWatcher", "is_voice_log", "parse_recorded_at"]
