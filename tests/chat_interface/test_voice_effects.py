"""Tests for kathrena.chat_interface.voice_effects and .audio."""

from __future__ import annotations

import numpy as np
import pytest

from kathrena.chat_interface.audio import AudioClip, to_wav_bytes
from kathrena.chat_interface.config import VoiceOutputConfig
from kathrena.chat_interface.voice_effects import NullVoiceEffects, PedalboardVoiceEffects


def _sine_clip(seconds: float = 0.5, sample_rate: int = 24000, freq: float = 220.0) -> AudioClip:
    t = np.linspace(0, seconds, int(seconds * sample_rate), endpoint=False, dtype=np.float32)
    samples = np.sin(2 * np.pi * freq * t).astype(np.float32)
    return AudioClip(samples=samples, sample_rate=sample_rate)


def test_null_voice_effects_returns_the_clip_unchanged():
    clip = _sine_clip()

    result = NullVoiceEffects().apply(clip)

    assert result is clip


def test_pedalboard_voice_effects_returns_processed_audio_of_similar_length():
    clip = _sine_clip()
    effects = PedalboardVoiceEffects(VoiceOutputConfig())

    result = effects.apply(clip)

    assert result.sample_rate == clip.sample_rate
    # PitchShift/Chorus may buffer a handful of samples internally - allow a little slack.
    assert abs(len(result.samples) - len(clip.samples)) < clip.sample_rate * 0.1
    assert not np.array_equal(result.samples, clip.samples)


def test_to_wav_bytes_round_trips_through_soundfile():
    import io

    import soundfile as sf

    clip = _sine_clip(seconds=0.1)

    wav_bytes = to_wav_bytes(clip)

    read_back, sample_rate = sf.read(io.BytesIO(wav_bytes), dtype="float32")
    assert sample_rate == clip.sample_rate
    assert read_back.shape[0] == pytest.approx(len(clip.samples), abs=2)
