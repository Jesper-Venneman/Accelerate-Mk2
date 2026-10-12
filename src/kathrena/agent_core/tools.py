"""Tools Kathrena's agent can call: vault search, memory recall, deadlines, web search, and
proposing vault edits.

Design spec: Architecture/Modules/G - Kathrena Agent Core.md

Each `build_*_tool` closes over the dependency it needs (a `VectorStore`, a `MemoryProvider`, an
`ApprovalGateConfig`, ...) so the returned function's signature is exactly what the LLM should
see - no config object or internal state leaks into the tool-calling schema.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from kathrena.agent_core.text_match import find_span
from kathrena.agent_core.web_search import WebSearch
from kathrena.approval_gate import ApprovalGateConfig, ChangeProposal, PendingReview, propose_change
from kathrena.memory import MemoryProvider
from kathrena.project_management import ProjectManagementConfig, list_upcoming_deadlines
from kathrena.rag_index.vector_store import VectorStore
from kathrena.settings import get_store

# Named presets for `set_llm_mode`.
_LLM_MODES: dict[str, dict[str, str]] = {
    "local": {
        "pipeline.llm_profile": "local",
        "agent_core.tool_profile": "local",
        "agent_core.reply_profile": "local",
        "memory.llm_profile": "local",
    },
    "cloud": {
        "pipeline.llm_profile": "cloud",
        "agent_core.tool_profile": "cloud",
        "agent_core.reply_profile": "cloud",
        "memory.llm_profile": "cloud",
    },
    "standard": {
        "pipeline.llm_profile": "local",
        "agent_core.tool_profile": "local",
        "agent_core.reply_profile": "cloud",
        "memory.llm_profile": "local",
    },
}

# Allow-list for change_setting - deliberately excludes secrets/endpoints/paths (api_key,
# base_url, vault_root, ...).
_CHANGEABLE_SETTINGS: dict[str, tuple[str, str]] = {
    "pipeline.llm_profile": ("pipeline", "llm_profile"),
    "agent_core.tool_profile": ("agent_core", "tool_profile"),
    "agent_core.reply_profile": ("agent_core", "reply_profile"),
    "memory.llm_profile": ("memory", "llm_profile"),
}


def build_search_vault_tool(vector_store: VectorStore, top_k: int):
    """Build a `search_vault(query)` tool bound to `vector_store`."""

    def search_vault(query: str) -> str:
        """Search the vault for notes relevant to the query and return the best excerpts."""
        results = vector_store.search(query, k=top_k)
        if not results:
            return "No relevant notes found."
        return "\n\n".join(f"[{result.source_path}]\n{result.content}" for result in results)

    return search_vault


def build_read_vault_file_tool(vault_root: Path, max_chars: int = 20000):
    """Build a `read_vault_file(path, near_text)` tool bound to `vault_root`.

    Deliberately doesn't check the `rag-index: false` opt-out (Decisions Log Round 24) - that flag
    only controls what search_vault can surface, not whether a file directly referenced by path
    (e.g. from another indexed note, or from a prior search_vault result) can still be read.
    """

    def read_vault_file(path: str, near_text: str | None = None) -> str:
        """Read a vault note by its path (as shown in search_vault's [path] prefix).

        Pass `near_text` - the exact excerpt search_vault surfaced - to get just a window of
        `max_chars` characters centered on that excerpt within the full file, instead of the
        whole thing; omit it (or if the excerpt can't be found) to fall back to the full file,
        truncated past `max_chars`.
        """
        resolved_root = vault_root.resolve()
        target = (resolved_root / path).resolve()
        try:
            target.relative_to(resolved_root)
        except ValueError:
            return f"Path is outside the vault: {path}"
        if not target.is_file():
            return f"File not found: {path}"
        text = target.read_text(encoding="utf-8")

        if near_text:
            span = find_span(text, near_text)
            if span is not None:
                start, end = span
                pad = max_chars // 2
                window_start = max(0, start - pad)
                window_end = min(len(text), end + pad)
                prefix = "..." if window_start > 0 else ""
                suffix = "..." if window_end < len(text) else ""
                return f"{prefix}{text[window_start:window_end]}{suffix}"

        if len(text) > max_chars:
            omitted = len(text) - max_chars
            return f"{text[:max_chars]}\n\n... (truncated, {omitted} more characters)"
        return text

    return read_vault_file


def build_search_memory_tool(memory_provider: MemoryProvider):
    """Build a `search_memory(query)` tool bound to `memory_provider`."""

    def search_memory(query: str) -> str:
        """Search Kathrena's own memories (facts, preferences, past chats) about the user."""
        memories = memory_provider.recall(query)
        if not memories:
            return "No relevant memories found."
        return "\n\n".join(memories)

    return search_memory


def build_current_datetime_tool(clock=datetime.now):
    """Build a `get_current_datetime()` tool. `clock` is injectable for tests, real system clock
    otherwise - Kathrena has no other sense of "now" (the LLM itself has no clock access)."""

    def get_current_datetime() -> str:
        """Get the current local date and time - use this for anything date/time-related."""
        return clock().strftime("%A, %B %d, %Y, %H:%M")

    return get_current_datetime


def build_list_deadlines_tool(pm_config: ProjectManagementConfig, clock=date.today):
    """Build a `list_deadlines(within_days)` tool bound to `pm_config`.

    An on-demand skill (Decisions Log Round 20), not a background sub-agent - Kathrena checks
    when asked, she doesn't surface deadlines unprompted.
    """

    def list_deadlines(within_days: int = pm_config.default_within_days) -> str:
        """List vault notes with a due date within `within_days` days, soonest first.

        Always includes anything already overdue. Pass a smaller `within_days` for a narrower
        question (e.g. "what's due this week?") or a larger one to look further ahead.
        """
        today = clock()
        deadlines = list_upcoming_deadlines(pm_config, within_days=within_days, today=today)
        if not deadlines:
            return "No deadlines found."
        lines = []
        for deadline in deadlines:
            days_left = (deadline.due_date - today).days
            if days_left < 0:
                when = f"OVERDUE by {-days_left} day(s)"
            elif days_left == 0:
                when = "due today"
            else:
                when = f"in {days_left} day(s)"
            lines.append(
                f"- {deadline.title} ({deadline.target_path}): "
                f"{deadline.due_date.isoformat()} - {when}"
            )
        return "\n".join(lines)

    return list_deadlines


def build_web_search_tool(web_search: WebSearch, max_results: int):
    """Build a `search_web(query)` tool bound to `web_search`."""

    def search_web(query: str) -> str:
        """Search the public internet for up-to-date info not found in the vault or memory."""
        hits = web_search.search(query, max_results=max_results)
        if not hits:
            return "No web results found."
        return "\n\n".join(f"[{hit.title}]({hit.url})\n{hit.snippet}" for hit in hits)

    return search_web


def build_propose_vault_change_tool(approval_config: ApprovalGateConfig):
    """Build a `propose_vault_change(...)` tool bound to `approval_config`."""

    def propose_vault_change(target_path: str, new_content: str, description: str) -> PendingReview:
        """Propose writing new_content to target_path in the vault.

        This only stages the change for the user's review - it never writes anything by itself.
        Use this whenever you want to create or edit a vault note.
        """
        proposal = ChangeProposal(
            target_path=target_path,
            new_content=new_content,
            description=description,
            proposer="G",
        )
        return propose_change(approval_config, proposal)

    return propose_vault_change


def build_set_llm_mode_tool():
    """Build a `set_llm_mode(mode)` tool - a fixed macro over several settings at once."""

    def set_llm_mode(mode: str) -> str:
        """Switch every LLM-using role to a named mode in one call.

        This only stops Kathrena's own new requests to the local LLM server - it does not unload
        that server's model from VRAM or stop it, and doesn't affect vault/memory search or voice
        transcription/synthesis, which stay local regardless of mode.
        """
        mapping = _LLM_MODES.get(mode)
        if mapping is None:
            return f"Unknown mode {mode!r} - choose one of {sorted(_LLM_MODES)!r}."
        store = get_store()
        mismatches = []
        for setting_name, value in mapping.items():
            section, key = setting_name.split(".", 1)
            store.set_value(section, key, value)
            if store.value(section, key, value) != value:
                mismatches.append(setting_name)
        if mismatches:
            return (
                f"Tried to switch to {mode!r} mode, but {', '.join(mismatches)} didn't take - "
                "check data/settings.yaml."
            )
        applied = ", ".join(f"{name}={value}" for name, value in mapping.items())
        return f"Switched to {mode!r} mode ({applied})."

    return set_llm_mode


def build_change_setting_tool():
    """Build a `change_setting(name, value)` tool - a generic, allow-listed settings writer."""

    def change_setting(name: str, value: str) -> str:
        """Change a single setting to a new value."""
        target = _CHANGEABLE_SETTINGS.get(name)
        if target is None:
            return f"{name!r} isn't a changeable setting - allowed: {sorted(_CHANGEABLE_SETTINGS)!r}."
        section, key = target
        store = get_store()
        store.set_value(section, key, value)
        stored = store.value(section, key, value)
        if stored != value:
            return f"Tried to set {name} to {value!r}, but it's still {stored!r} - check data/settings.yaml."
        return f"Set {name} to {value!r}."

    return change_setting
