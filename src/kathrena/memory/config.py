"""Configuration for Module J (Kathrena's persistent memory).

Design spec: Architecture/Modules/J - Memory Module.md
Backing store choice: Architecture/Decisions Log.md, Round 19.

Independent from every other module's config - `llm_profile` names its own entry in
`data/settings.yaml`'s shared `llm_profiles` section (see `kathrena.llm`), chosen independently
from every other role's own profile (Decisions Log Round 27).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from kathrena.settings import setting_float, setting_int, setting_path, setting_str


@dataclass(frozen=True)
class MemoryConfig:
    """Storage location, embedding model, and LLM connection for Kathrena's memory."""

    # Local runtime data (Architecture/Architecture Overview.md#Runtime architecture) - already
    # covered by .gitignore. A separate file from kathrena.rag_index's Chroma dir and
    # kathrena.agent_core's checkpoint DB - personal memory never mixes with vault RAG or raw
    # chat history.
    store_path: Path = field(
        default_factory=lambda: setting_path("memory", "store_path", "./data/memory.sqlite")
    )

    # Same embedding model as kathrena.rag_index, but a fully separate
    # instance/database - personal memory is deliberately kept out of vault search results.
    # embedding_dims must match embedding_model_name's actual output size (384 for
    # bge-small-en-v1.5) - SqliteStore can't infer this from the model itself.
    embedding_model_name: str = field(
        default_factory=lambda: setting_str(
            "memory", "embedding_model_name", "BAAI/bge-small-en-v1.5"
        )
    )
    embedding_dims: int = field(
        default_factory=lambda: setting_int("memory", "embedding_dims", 384)
    )

    # Fixed, not templated - a single-user app has no need for LangMem's per-user namespace
    # placeholders (e.g. "{langgraph_user_id}").
    namespace: tuple[str, ...] = ("memories", "kathrena")

    # Which named data/settings.yaml llm_profiles entry background memory extraction is built
    # from (kathrena.llm.resolve_profile/build_chat_model) - independent from every other role's
    # own profile choice (Decisions Log Round 27).
    llm_profile: str = field(default_factory=lambda: setting_str("memory", "llm_profile", "local"))

    # How many memories the search_memory tool retrieves per call.
    search_limit: int = field(default_factory=lambda: setting_int("memory", "search_limit", 5))

    # LangMem's ReflectionExecutor debounce (Decisions Log Round 9's "wait for a conversation to
    # go idle" pattern, applied here instead of the retired wake-word listener) - each new turn
    # in the same thread reschedules this delay, so extraction only runs once things go quiet.
    reflection_delay_seconds: float = field(
        default_factory=lambda: setting_float("memory", "reflection_delay_seconds", 360.0)
    )

    # How many already-confirmed-sent messages remember() re-includes ahead of a thread's marker
    # for continuity/reinforcement (Decisions Log Round 30) - see
    # Architecture/Investigations/Memory Context Management.md.
    marker_overlap_messages: int = field(
        default_factory=lambda: setting_int("memory", "marker_overlap_messages", 2)
    )
