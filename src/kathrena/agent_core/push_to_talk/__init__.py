"""Push-to-talk voice input: part of Module G (Kathrena Agent Core).

Design spec: Architecture/Modules/G - Kathrena Agent Core.md
Approach: Architecture/Decisions Log.md, Round 18.

Replaces the wake-word listener (Round 17), which turned out unstable and resource-heavy in
practice (constant Whisper scanning, false triggers). `PushToTalkListener` holds a global hotkey
to record a question and releases it to send - no continuous transcription, no phrase matching.
"""

from __future__ import annotations

from kathrena.agent_core.push_to_talk.config import PushToTalkConfig
from kathrena.agent_core.push_to_talk.listener import PushToTalkListener

__all__ = ["PushToTalkConfig", "PushToTalkListener"]
