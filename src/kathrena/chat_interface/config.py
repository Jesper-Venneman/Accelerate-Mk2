"""Configuration for Module K's voice output (text-to-speech + voice-persona effects).

Design spec: Architecture/Modules/K - Chat Interface.md (Voice output, Voice persona)
Engine/approach choices: Architecture/Decisions Log.md, Round 16.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kathrena.settings import setting_bool, setting_float, setting_str


@dataclass(frozen=True)
class VoiceOutputConfig:
    """Kokoro synthesis settings plus the DSP voice-persona effects layered on top of it."""

    enabled: bool = field(
        default_factory=lambda: setting_bool("chat_interface", "voice_output_enabled", True)
    )

    always_speak: bool = field(
        default_factory=lambda: setting_bool("chat_interface", "always_speak", False)
    )

    # Kokoro-82M (Decisions Log Round 16). lang_code must match the chosen voice's language.
    kokoro_lang_code: str = field(
        default_factory=lambda: setting_str("chat_interface", "kokoro_lang_code", "a")
    )
    kokoro_voice: str = field(
        default_factory=lambda: setting_str("chat_interface", "kokoro_voice", "af_heart")
    )

    # Voice-persona DSP chain (K - Chat Interface.md's "Voice persona" section) - starting points
    # meant to be tuned by ear, not precisely validated values.
    pitch_shift_semitones: float = field(
        default_factory=lambda: setting_float("chat_interface", "pitch_shift_semitones", -2.0)
    )
    highpass_cutoff_hz: float = field(
        default_factory=lambda: setting_float("chat_interface", "highpass_cutoff_hz", 150.0)
    )
    distortion_drive_db: float = field(
        default_factory=lambda: setting_float("chat_interface", "distortion_drive_db", 6.0)
    )
    chorus_rate_hz: float = field(
        default_factory=lambda: setting_float("chat_interface", "chorus_rate_hz", 1.5)
    )
    chorus_depth: float = field(
        default_factory=lambda: setting_float("chat_interface", "chorus_depth", 0.25)
    )
