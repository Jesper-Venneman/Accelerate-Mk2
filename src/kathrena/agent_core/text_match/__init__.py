"""Fuzzy substring matching: part of Module G (Kathrena Agent Core).

Design spec: Architecture/Modules/G - Kathrena Agent Core.md
Decision: Architecture/Decisions Log.md, Round 24.

Backs `kathrena.agent_core.tools`'s `read_vault_file` tool - lets its `near_text` argument match a
vault note's raw text even when punctuation/whitespace differ slightly, the same relationship
`kathrena.agent_core.web_search` has to its own tool.
"""

from __future__ import annotations

from kathrena.agent_core.text_match.matching import find_span

__all__ = ["find_span"]
