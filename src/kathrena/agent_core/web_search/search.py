"""Internet search for Module G, kept behind a swappable Protocol.

Design spec: Architecture/Modules/G - Kathrena Agent Core.md (Web search)
Decision: Architecture/Decisions Log.md, Round 21.

Mirrors the same swappable-provider pattern already used for `kathrena.rag_index.VectorStore`
and `kathrena.memory.MemoryProvider`: `kathrena.agent_core.tools` only ever depends on the
`WebSearch` Protocol, so the backend (DuckDuckGo now, something else later - e.g. Tavily, if
DuckDuckGo's result quality or rate limits become a problem) can change without touching the
tool-calling loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SearchHit:
    """Represents a single web search result."""
    title: str
    url: str
    snippet: str


class WebSearch(Protocol):
    def search(self, query: str, max_results: int) -> list[SearchHit]: ...


class DuckDuckGoWebSearch:
    def search(self, query: str, max_results: int) -> list[SearchHit]:
        # Imported lazily so importing this module doesn't require `ddgs` unless search actually
        # runs, same convention as the rest of this codebase's optional/heavy dependencies.
        from ddgs import DDGS

        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            return [
                SearchHit(title=r["title"], url=r["href"], snippet=r["body"]) for r in results
            ]
