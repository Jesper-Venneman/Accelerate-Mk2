"""Kathrena's long-term memory: background extraction + semantic recall.

Design spec: Architecture/Modules/J - Memory Module.md
Tooling choice (LangMem): Architecture/Decisions Log.md, Round 8.

`MemoryProvider` sits between `kathrena.agent_core` (Module G) and LangMem/the store - the
"swappable memory-provider interface" the design spec calls for, so LangMem could be replaced
later without touching G. Only two operations: `remember` (background extraction, triggered
after a turn) and `recall` (semantic search, used by G's `search_memory` tool).

Scope note: this first pass stores memories as plain unstructured text in a single namespace,
not the fuller Profile/Collection/Episodic split Round 9 originally sketched - see Round 19.
"""

from __future__ import annotations

from typing import Any, Protocol

from kathrena.memory.config import MemoryConfig

_MARKER_NAMESPACE = ("memory_markers",)


class MemoryProvider(Protocol):
    """Swappable interface so the memory backend can change without touching Module G."""

    def recall(self, query: str) -> list[str]: ...
    def remember(self, messages: list[Any], thread_id: str) -> None: ...


class LangMemProvider:
    """Default `MemoryProvider`: LangMem's background extractor over a LangGraph `BaseStore`.

    Hot-swappable without a restart (Decisions Log Round 28): rebuilds its chat model, `manager`,
    and `ReflectionExecutor` only when `memory.llm_profile` has actually changed since last
    checked, re-read fresh on every `remember()` call rather than trusting the frozen `config`
    snapshot. The *old* executor is explicitly `shutdown(wait=False)` rather than just dropped -
    verified against LangMem's own source that each executor owns a non-daemon background thread
    that otherwise runs forever, and that shutting one down flushes any already-pending
    extraction immediately (using the pre-switch model) rather than leaving it in limbo.
    """

    def __init__(self, config: MemoryConfig, store: Any) -> None:
        self._config = config
        self._store = store
        self._profile_name: str | None = None
        self._executor: Any = None
        self._rebuild_if_needed()

    def _rebuild_if_needed(self) -> None:
        # Imported lazily so importing this module doesn't require langmem/langchain-openai
        # unless a provider is actually constructed.
        from langmem import ReflectionExecutor, create_memory_store_manager

        from kathrena.llm import build_chat_model, resolve_profile
        from kathrena.settings import setting_str

        current_profile = setting_str("memory", "llm_profile", "local")
        if current_profile == self._profile_name:
            return
        # Deliberately no log_label here - create_memory_store_manager does its own
        # isinstance(model, BaseChatModel) check internally, which a build_chat_model-bound
        # RunnableBinding fails (Decisions Log Round 32 postmortem). remember() attaches the
        # logging callback per-submission instead, via the executor's own config.
        chat_model = build_chat_model(resolve_profile(current_profile))
        # Unstructured (schema-less) memories for now - see this module's docstring.
        manager = create_memory_store_manager(
            chat_model, namespace=self._config.namespace, store=self._store
        )
        old_executor = self._executor
        self._executor = ReflectionExecutor(manager, store=self._store)
        self._profile_name = current_profile
        if old_executor is not None:
            old_executor.shutdown(wait=False)

    def recall(self, query: str) -> list[str]:
        """Semantically search stored memories - used by Module G's `search_memory` tool."""
        results = self._store.search(
            self._config.namespace, query=query, limit=self._config.search_limit
        )
        return [str(item.value.get("content", item.value)) for item in results]

    def _read_marker(self, thread_id: str) -> int:
        item = self._store.get(_MARKER_NAMESPACE, thread_id)
        return item.value["sent_through"] if item is not None else 0

    def _write_marker(self, thread_id: str, sent_through: int) -> None:
        # index=False - bookkeeping, not semantically searchable content.
        self._store.put(_MARKER_NAMESPACE, thread_id, {"sent_through": sent_through}, index=False)

    def remember(self, messages: list[Any], thread_id: str) -> None:
        """Schedule (debounced) background extraction from the unsent tail of `messages`.

        Never blocks the caller. A persisted per-thread marker (Decisions Log Round 30) tracks
        how many messages have been *confirmed* handed to LangMem, so repeated calls for a
        long-running thread don't keep re-submitting its entire history - only
        `messages[marker - overlap:]` goes out each time.

        The marker only advances once a submission actually completes successfully.
        """
        from kathrena.llm_logging import LoggingCallbackHandler

        self._rebuild_if_needed()
        marker = self._read_marker(thread_id)
        to_send = messages[max(0, marker - self._config.marker_overlap_messages) :]
        future = self._executor.submit(
            {"messages": to_send},
            # callbacks here (not build_chat_model's log_label) - see _rebuild_if_needed for why.
            config={
                "configurable": {"thread_id": thread_id},
                "callbacks": [LoggingCallbackHandler("memory")],
            },
            after_seconds=int(self._config.reflection_delay_seconds),
        )
        sent_through = len(messages)  # captured now, only used if this submission actually runs

        def _advance_marker_if_it_actually_ran(f: Any) -> None:
            if not f.cancelled():
                self._write_marker(thread_id, sent_through)

        future.add_done_callback(_advance_marker_if_it_actually_ran)
