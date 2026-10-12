"""Configuration for push-to-talk voice input (part of Module G).

Design spec: Architecture/Modules/G - Kathrena Agent Core.md
Approach: Architecture/Decisions Log.md, Round 18.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kathrena.settings import setting_float, setting_str


@dataclass(frozen=True)
class PushToTalkConfig:
    """Which key to hold to talk, and safety limits on the recording it captures."""

    # Any name from pynput.keyboard.Key (e.g. "scroll_lock", "pause", "f13") - pick a key your
    # keyboard has that nothing else relies on, so holding it never conflicts with normal use.
    hotkey_name: str = field(
        default_factory=lambda: setting_str("push_to_talk", "hotkey_name", "scroll_lock")
    )

    # Key bounce (electrical or driver-level, worse on some toggle keys like Scroll Lock) can
    # fire several rapid press/release pairs for a single physical press, each producing a
    # too-short recording that also happens to crash openai-whisper's decoder. Anything shorter
    # than this is discarded before it ever reaches Whisper - it's noise, not a real question.
    min_utterance_seconds: float = field(
        default_factory=lambda: setting_float("push_to_talk", "min_utterance_seconds", 0.3)
    )

    sample_rate: int = 16000  # Whisper expects 16000 Hz audio
    # A missed key-release event (a rare OS/driver glitch) shouldn't record forever.
    max_utterance_seconds: float = field(
        default_factory=lambda: setting_float("push_to_talk", "max_utterance_seconds", 120.0)
    )
