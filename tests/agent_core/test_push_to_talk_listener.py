"""Tests for kathrena.agent_core.push_to_talk.listener - the hold-to-record state machine.

No real keyboard hook, microphone, or Whisper model needed - a fake recorder/transcriber stand in
for both, and the private press/release handlers are exercised directly rather than through a
real pynput hotkey.
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from kathrena.agent_core.push_to_talk.config import PushToTalkConfig
from kathrena.agent_core.push_to_talk.listener import PushToTalkListener
from kathrena.voice_log.transcription import TranscriptionResult


class FakeRecorder:
    def __init__(self, samples: np.ndarray) -> None:
        self._samples = samples
        self.started = 0
        self.stopped = 0

    def start(self) -> None:
        self.started += 1

    def stop(self) -> np.ndarray:
        self.stopped += 1
        return self._samples


class FakeTranscriber:
    def __init__(self, text: str) -> None:
        self._text = text
        self.calls = 0

    def transcribe(self, audio_path) -> TranscriptionResult:
        self.calls += 1
        return TranscriptionResult(text=self._text)


@pytest.fixture
def ptt_config() -> PushToTalkConfig:
    # min_utterance_seconds=0.0 so these fixture-sized fake samples aren't filtered out by the
    # duration check - that behavior gets its own dedicated tests below.
    return PushToTalkConfig(max_utterance_seconds=5.0, min_utterance_seconds=0.0)


def test_release_emits_the_transcribed_question(ptt_config):
    recorder = FakeRecorder(np.zeros(10, dtype=np.float32))
    transcriber = FakeTranscriber("what's the status of foo")
    listener = PushToTalkListener(ptt_config, transcriber, recorder=recorder)
    emitted = []
    listener._emit = emitted.append

    listener._start_recording()
    listener._stop_recording_and_transcribe()
    time.sleep(0.05)  # transcription happens on its own thread

    assert recorder.started == 1
    assert recorder.stopped == 1
    assert emitted == ["what's the status of foo"]


def test_empty_transcript_is_not_emitted(ptt_config):
    recorder = FakeRecorder(np.zeros(10, dtype=np.float32))
    transcriber = FakeTranscriber("")
    listener = PushToTalkListener(ptt_config, transcriber, recorder=recorder)
    emitted = []
    listener._emit = emitted.append

    listener._start_recording()
    listener._stop_recording_and_transcribe()
    time.sleep(0.05)

    assert emitted == []


def test_whitespace_only_transcript_is_not_emitted(ptt_config):
    recorder = FakeRecorder(np.zeros(10, dtype=np.float32))
    transcriber = FakeTranscriber("   ")
    listener = PushToTalkListener(ptt_config, transcriber, recorder=recorder)
    emitted = []
    listener._emit = emitted.append

    listener._start_recording()
    listener._stop_recording_and_transcribe()
    time.sleep(0.05)

    assert emitted == []


def test_repeated_press_events_while_recording_are_ignored(ptt_config):
    """Holding a key generates OS key-repeat press events on some platforms - only the first
    should start a new recording."""
    recorder = FakeRecorder(np.zeros(10, dtype=np.float32))
    transcriber = FakeTranscriber("hi")
    listener = PushToTalkListener(ptt_config, transcriber, recorder=recorder)
    listener._emit = lambda text: None  # avoid the leftover max-duration timer hitting real _emit

    listener._start_recording()
    listener._start_recording()
    listener._start_recording()

    assert recorder.started == 1

    listener.stop()  # cancel the pending max-duration timer so it doesn't fire after the test


def test_release_without_a_press_does_nothing(ptt_config):
    recorder = FakeRecorder(np.zeros(10, dtype=np.float32))
    transcriber = FakeTranscriber("hi")
    listener = PushToTalkListener(ptt_config, transcriber, recorder=recorder)
    emitted = []
    listener._emit = emitted.append

    listener._stop_recording_and_transcribe()
    time.sleep(0.05)

    assert recorder.stopped == 0
    assert emitted == []


def test_max_duration_safety_cutoff_stops_a_stuck_recording():
    """A missed key-release event (e.g. a driver glitch) shouldn't record forever."""
    config = PushToTalkConfig(max_utterance_seconds=0.05, min_utterance_seconds=0.0)
    recorder = FakeRecorder(np.zeros(10, dtype=np.float32))
    transcriber = FakeTranscriber("cut off")
    listener = PushToTalkListener(config, transcriber, recorder=recorder)
    emitted = []
    listener._emit = emitted.append

    listener._start_recording()
    time.sleep(0.15)

    assert recorder.stopped == 1
    assert emitted == ["cut off"]


def test_recording_shorter_than_the_minimum_is_discarded_without_calling_whisper():
    """Key bounce can fire a full press/release pair almost instantly - too short to be real
    speech, and short enough to crash openai-whisper's decoder (the actual bug this guards)."""
    config = PushToTalkConfig(max_utterance_seconds=5.0, min_utterance_seconds=0.3)
    recorder = FakeRecorder(np.zeros(10, dtype=np.float32))  # far below 0.3s * 16000 Hz
    transcriber = FakeTranscriber("should never be transcribed")
    listener = PushToTalkListener(config, transcriber, recorder=recorder)
    emitted = []
    listener._emit = emitted.append

    listener._start_recording()
    listener._stop_recording_and_transcribe()
    time.sleep(0.05)

    assert transcriber.calls == 0
    assert emitted == []


def test_recording_at_or_above_the_minimum_is_still_transcribed():
    config = PushToTalkConfig(max_utterance_seconds=5.0, min_utterance_seconds=0.3)
    recorder = FakeRecorder(np.zeros(int(0.3 * config.sample_rate), dtype=np.float32))
    transcriber = FakeTranscriber("long enough")
    listener = PushToTalkListener(config, transcriber, recorder=recorder)
    emitted = []
    listener._emit = emitted.append

    listener._start_recording()
    listener._stop_recording_and_transcribe()
    time.sleep(0.05)

    assert emitted == ["long enough"]


def test_a_transcription_failure_is_discarded_instead_of_crashing_the_thread():
    """Regression test: openai-whisper can raise on malformed/edge-case audio - that shouldn't
    take down the background thread with an unhandled exception."""
    ptt_config = PushToTalkConfig(max_utterance_seconds=5.0, min_utterance_seconds=0.0)
    recorder = FakeRecorder(np.zeros(10, dtype=np.float32))

    class RaisingTranscriber:
        def transcribe(self, audio_path):
            raise RuntimeError("simulated whisper decoder failure")

    listener = PushToTalkListener(ptt_config, RaisingTranscriber(), recorder=recorder)
    emitted = []
    listener._emit = emitted.append

    listener._start_recording()
    listener._stop_recording_and_transcribe()
    time.sleep(0.05)

    assert emitted == []  # no crash, and nothing sent
