"""Kathrena's voice persona: a separate, swappable DSP stage between raw TTS output and playback.

Design spec: Architecture/Modules/K - Chat Interface.md (Voice persona)
Approach: Architecture/Decisions Log.md, Round 16 - DSP effects (pitch/formant shift, EQ, a touch
of robotic texture), not trained voice cloning/conversion.

Deliberately independent of the TTS engine (kathrena.chat_interface.tts): takes an `AudioClip` in,
returns an `AudioClip` out, so Kokoro (or a future swap) never needs to know this stage exists.
"""

from __future__ import annotations

from typing import Protocol

from kathrena.chat_interface.audio import AudioClip
from kathrena.chat_interface.config import VoiceOutputConfig


class VoiceEffects(Protocol):
    """Swappable interface so the voice-persona effects can change without touching callers."""

    def apply(self, clip: AudioClip) -> AudioClip: ...


class PedalboardVoiceEffects:
    """Default `VoiceEffects`: pitch shift + a highpass/distortion/chorus touch via `pedalboard`."""

    def __init__(self, config: VoiceOutputConfig) -> None:
        # Imported lazily so importing this module doesn't require pedalboard unless used.
        from pedalboard import Chorus, Distortion, HighpassFilter, Pedalboard, PitchShift

        self._board = Pedalboard(
            [
                PitchShift(semitones=config.pitch_shift_semitones),
                HighpassFilter(cutoff_frequency_hz=config.highpass_cutoff_hz),
                Distortion(drive_db=config.distortion_drive_db),
                Chorus(rate_hz=config.chorus_rate_hz, depth=config.chorus_depth),
            ]
        )

    def apply(self, clip: AudioClip) -> AudioClip:
        processed = self._board(clip.samples, clip.sample_rate)
        return AudioClip(samples=processed, sample_rate=clip.sample_rate)


class NullVoiceEffects:
    """A no-op `VoiceEffects` - Kokoro's raw voice, unmodified. Useful for testing or disabling."""

    def apply(self, clip: AudioClip) -> AudioClip:
        return clip
