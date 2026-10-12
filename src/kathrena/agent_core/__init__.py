"""Module G: Kathrena Agent Core.

Design spec: Architecture/Modules/G - Kathrena Agent Core.md

Kathrena's conversational LangGraph agent - retrieves from `kathrena.rag_index`
(Module F), reachable via `kathrena.chat_interface` (Module K) or push-to-talk
(`kathrena.agent_core.push_to_talk`).

Public API: `run_turn` runs one chat turn and returns a `TurnResult` (the
reply text plus any `ChangeProposal`s staged during that turn).
"""

from __future__ import annotations

from kathrena.agent_core.config import AgentCoreConfig
from kathrena.agent_core.graph import TurnResult, run_turn

__all__ = ["AgentCoreConfig", "TurnResult", "run_turn"]

