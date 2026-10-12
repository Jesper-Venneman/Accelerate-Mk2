"""Push-to-talk listener: hold a key to record a question, release to send it.

Design spec: Architecture/Modules/G - Kathrena Agent Core.md
Approach: Architecture/Decisions Log.md, Round 18 - replaces the wake-word listener (Round 17),
which turned out unstable and wasteful in practice (continuous Whisper scanning, false triggers).

A global `pynput` keyboard hook watches one configured key - system-wide, regardless of which
window has focus, and without suppressing the key's normal behavior elsewhere (`suppress=False`,
pynput's default: the listener only observes, it never swallows the keypress). Holding it starts
a streaming recording (`microphone.StreamingRecorder`); releasing it stops the recording and hands
the raw samples to a plain background thread for transcription via `kathrena.voice_log`'s
`transcription` module (B) - deliberately NOT transcribed on pynput's own callback thread, since
pynput's docs warn that blocking calls there risk freezing keyboard/mouse input system-wide.

If there's actually something to send - not just an accidental tap - the text is handed back via
a thread-safe call into an `asyncio.Queue`.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
import threading
from pathlib import Path

import numpy as np
import soundfile as sf

from kathrena.agent_core.push_to_talk.config import PushToTalkConfig
from kathrena.agent_core.push_to_talk.microphone import (
    Recorder,
    StreamingRecorder,
    describe_default_input_device,
)
from kathrena.voice_log.transcription import Transcriber

logger = logging.getLogger(__name__)


class PushToTalkListener:
    """Hold `config.hotkey_name` to talk. `utterances` is an `asyncio.Queue[str]` to `await` from.

    Call `start(loop)` before anything is produced, and `stop()` when the owning Chainlit session
    ends (see `kathrena.chat_interface.app`).
    """

    def __init__(
        self,
        config: PushToTalkConfig,
        transcriber: Transcriber,
        recorder: Recorder | None = None,
    ) -> None:
        self._config = config
        self._transcriber = transcriber
        self._recorder = recorder if recorder is not None else StreamingRecorder(config.sample_rate)
        self.utterances: asyncio.Queue[str] = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()
        self._is_recording = False
        self._max_duration_timer: threading.Timer | None = None
        self._keyboard_listener: object | None = None  # pynput.keyboard.Listener

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Begin listening for the hotkey. `loop` is where `utterances` gets fed."""
        # Imported lazily so importing this module doesn't require pynput unless a listener is
        # actually started.
        from pynput import keyboard

        self._loop = loop
        target_key = getattr(keyboard.Key, self._config.hotkey_name)
        logger.info(
            "Push-to-talk listener starting - hold %s to talk. Input device: %s",
            self._config.hotkey_name,
            describe_default_input_device(),
        )

        def on_press(key: object) -> None:
            if key == target_key:
                self._start_recording()

        def on_release(key: object) -> None:
            if key == target_key:
                self._stop_recording_and_transcribe()

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()
        self._keyboard_listener = listener

    def stop(self) -> None:
        if self._keyboard_listener is not None:
            self._keyboard_listener.stop() # pyright: ignore[reportAttributeAccessIssue]
            self._keyboard_listener = None
        with self._lock:
            if self._is_recording:
                self._is_recording = False
                self._cancel_max_duration_timer()
                self._recorder.stop()

    def _start_recording(self) -> None:
        with self._lock:
            if self._is_recording:
                return  # holding a key generates repeated OS key-repeat press events
            self._is_recording = True
            self._recorder.start()
            timer = threading.Timer(
                self._config.max_utterance_seconds, self._stop_recording_and_transcribe
            )
            timer.daemon = True
            timer.start()
            self._max_duration_timer = timer

    def _stop_recording_and_transcribe(self) -> None:
        with self._lock:
            if not self._is_recording:
                return
            self._is_recording = False
            self._cancel_max_duration_timer()
            samples = self._recorder.stop()

        # Whisper can take a second or more - never run it on pynput's own callback thread.
        threading.Thread(target=self._transcribe_and_emit, args=(samples,), daemon=True).start()

    def _cancel_max_duration_timer(self) -> None:
        if self._max_duration_timer is not None:
            self._max_duration_timer.cancel()
            self._max_duration_timer = None

    def _transcribe_and_emit(self, samples: np.ndarray) -> None:
        min_samples = self._config.min_utterance_seconds * self._config.sample_rate
        if samples.size < min_samples:
            return  # too short to be real speech - most likely key bounce, not an actual press
        try:
            text = self._transcribe(samples).strip()
        except Exception:
            logger.exception("Transcribing a push-to-talk recording failed - discarding it")
            return
        if text:  # an empty transcript means silence - an accidental tap, not a real question
            self._emit(text)

    def _transcribe(self, samples: np.ndarray) -> str:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "utterance.wav"
            sf.write(path, samples, self._config.sample_rate)
            return self._transcriber.transcribe(path).text

    def _emit(self, text: str) -> None:
        assert self._loop is not None, "start() must be called before an utterance can be emitted"
        self._loop.call_soon_threadsafe(self.utterances.put_nowait, text)
