"""Tests for kathrena.voice_log.transcription.whisper_transcriber - specifically its thread-safety.

Design spec: Architecture/Modules/B - Transcription Module.md

Regression test for a real bug: openai-whisper's decoder registers stateful KV-cache hooks during
a transcribe() call, so two concurrent calls on the same WhisperTranscriber instance (e.g. from
kathrena.agent_core.push_to_talk's background transcription threads) corrupt each other's state
and crash with a tensor shape mismatch. A fake whisper module stands in for the real (heavy)
package, so this stays a fast unit test.
"""

from __future__ import annotations

import sys
import threading
import time
import types

import pytest


class _FakeWhisperModel:
    """Records whether any two transcribe() calls were ever active at the same time."""

    def __init__(self) -> None:
        self.max_concurrent = 0
        self._active = 0
        self._state_lock = threading.Lock()

    def transcribe(self, audio_path: str) -> dict:
        with self._state_lock:
            self._active += 1
            self.max_concurrent = max(self.max_concurrent, self._active)
        time.sleep(0.05)  # long enough for a second, unguarded call to overlap
        with self._state_lock:
            self._active -= 1
        return {"text": "hello", "language": "en"}


@pytest.fixture
def fake_whisper_model(monkeypatch):
    """Substitutes sys.modules["whisper"] so `import whisper` picks this up - no real load."""
    model = _FakeWhisperModel()
    fake_module = types.SimpleNamespace(load_model=lambda *a, **k: model)
    monkeypatch.setitem(sys.modules, "whisper", fake_module)
    return model


def test_concurrent_transcribe_calls_are_serialized(fake_whisper_model, config, tmp_path):
    from kathrena.voice_log.transcription.whisper_transcriber import WhisperTranscriber

    transcriber = WhisperTranscriber(config)
    audio_path = tmp_path / "a.wav"
    audio_path.write_bytes(b"")

    threads = [
        threading.Thread(target=transcriber.transcribe, args=(audio_path,)) for _ in range(4)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert fake_whisper_model.max_concurrent == 1
