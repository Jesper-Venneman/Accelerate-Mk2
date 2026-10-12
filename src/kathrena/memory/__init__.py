"""Module J: Memory Module.

Design spec: Architecture/Modules/J - Memory Module.md

Kathrena's persistent, evolving memory - separate from the vault - built on
LangMem and a LangGraph `SqliteStore` (Decisions Log Round 19), sitting behind
a swappable memory-provider interface so LangMem can be replaced later
without a redesign.

Public API: `open_memory_store` opens the persistent database; `MemoryProvider`
is the swappable interface; `LangMemProvider` is the default implementation.
"""

from __future__ import annotations

from kathrena.memory.config import MemoryConfig
from kathrena.memory.provider import LangMemProvider, MemoryProvider
from kathrena.memory.store import open_memory_store

__all__ = ["LangMemProvider", "MemoryConfig", "MemoryProvider", "open_memory_store"]

