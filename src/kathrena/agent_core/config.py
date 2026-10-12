"""Configuration for Module G (Kathrena's conversational agent core).

Design spec: Architecture/Modules/G - Kathrena Agent Core.md

Independent from every other module's config (`kathrena.rag_index.config.RagIndexConfig`, 
`kathrena.config.PipelineConfig`) - they only agree on the shared "common" settings
section, not shared code. `tool_profile`/`reply_profile` each name an entry in
`data/settings.yaml`'s `llm_profiles` section (see `kathrena.llm`), independent from every
other role's own profile choice (Decisions Log Round 27/28).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from kathrena.settings import setting_int, setting_path, setting_str

# Personality/behaviour only - the tool-availability sentences (which describe actual registered
# tools) stay hardcoded in kathrena.agent_core.graph instead of here. This prompt is simple, 
# editing it in the settings.yaml is suggested.
_DEFAULT_SYSTEM_PROMPT = (
    "You are Kathrena, a warm and casual AI friend. Your goal is to help the user in any way you can."

    "Importantly: In your responses, in terms of formatting, do not use any bold or italic "
    "text, this will interfere with your voice module."
)


@dataclass(frozen=True)
class AgentCoreConfig:
    """Conversation checkpointing and LLM connection settings for Kathrena's agent graph."""

    agent_name: str = field(default_factory=lambda: setting_str("agent_core", "agent_name", "Kathrena"))

    # Local runtime data (Architecture/Architecture Overview.md#Runtime architecture) - already
    # covered by .gitignore. Lets a chat thread's history survive a process restart.
    checkpoint_path: Path = field(
        default_factory=lambda: setting_path(
            "agent_core", "checkpoint_path", "./data/agent_core_checkpoints.sqlite"
        )
    )

    # Which named data/settings.yaml llm_profiles entry decides which tool(s) to call - bound
    # with tools, loops through call_tools exactly as today (Decisions Log Round 28).
    tool_profile: str = field(
        default_factory=lambda: setting_str("agent_core", "tool_profile", "local")
    )

    # Which named llm_profiles entry writes the reply actually shown to the user. When this
    # differs from tool_profile, build_agent_graph adds a second call_reply_model node that runs
    # once the tool-calling loop stops requesting tools - when they're equal (the default), the
    # graph behaves exactly as if there were only one profile, at no extra cost.
    reply_profile: str = field(
        default_factory=lambda: setting_str("agent_core", "reply_profile", "local")
    )

    # Same "common" settings section as every other vault-reading module.
    vault_root: Path = field(default_factory=lambda: setting_path("common", "vault_root", "."))

    # How many vault chunks the search_vault tool retrieves per call.
    rag_top_k: int = field(default_factory=lambda: setting_int("agent_core", "rag_top_k", 4))

    # How many hits the search_web tool retrieves per call (Decisions Log Round 21) - whether the
    # tool is available at all is a separate flag, kathrena.agent_core.web_search.WebSearchConfig.
    web_search_max_results: int = field(
        default_factory=lambda: setting_int("agent_core", "web_search_max_results", 5)
    )

    # Safety cap for the read_vault_file tool - large notes are truncated rather than blowing the
    # context window in one call.
    read_file_max_chars: int = field(
        default_factory=lambda: setting_int("agent_core", "read_file_max_chars", 20000)
    )

    # Caps how many of the thread's messages call_model/call_reply_model actually send to the
    # LLM each turn - the checkpointed history itself (and what memory extraction reads) stays
    # full-length; only the live prompt is windowed. Matters now that a thread can survive a
    # restart (Decisions Log Round 29/30), not just one running session. See
    # Architecture/Investigations/Memory Context Management.md.
    history_window_messages: int = field(
        default_factory=lambda: setting_int("agent_core", "history_window_messages", 12)
    )

    # Personality/behaviour system prompt - editable without touching code (Decisions Log Round
    # 31). Tool-availability sentences are appended separately in kathrena.agent_core.graph.
    system_prompt: str = field(
        default_factory=lambda: setting_str("agent_core", "system_prompt", _DEFAULT_SYSTEM_PROMPT)
    )
