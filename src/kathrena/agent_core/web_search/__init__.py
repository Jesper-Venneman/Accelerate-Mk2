"""Web search: part of Module G (Kathrena Agent Core).

Design spec: Architecture/Modules/G - Kathrena Agent Core.md (Web search)
Decision: Architecture/Decisions Log.md, Round 21.

Gives Kathrena's `search_web` tool a real internet backend, kept behind the `WebSearch` Protocol
so the underlying provider (DuckDuckGo today) can be swapped without touching
`kathrena.agent_core.tools`/`kathrena.agent_core.graph`.
"""

from __future__ import annotations

from kathrena.agent_core.web_search.config import WebSearchConfig
from kathrena.agent_core.web_search.search import DuckDuckGoWebSearch, SearchHit, WebSearch

__all__ = ["DuckDuckGoWebSearch", "SearchHit", "WebSearch", "WebSearchConfig"]
