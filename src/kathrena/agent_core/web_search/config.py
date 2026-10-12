"""Configuration for Module G's web search tool.

Design spec: Architecture/Modules/G - Kathrena Agent Core.md (Web search)
Decision: Architecture/Decisions Log.md, Round 21.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kathrena.settings import setting_bool


@dataclass(frozen=True)
class WebSearchConfig:
    """Whether Kathrena's `search_web` tool is available at all.

    How many results it asks for per call lives on `kathrena.agent_core.config.AgentCoreConfig`
    instead (`web_search_max_results`), alongside `rag_top_k` - both are "how many hits per tool
    call" knobs owned by Module G, not by the backend module providing the capability.
    """

    enabled: bool = field(default_factory=lambda: setting_bool("web_search", "enabled", True))
