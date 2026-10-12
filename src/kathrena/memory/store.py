"""Kathrena's persistent memory database - the one place this module touches storage.

Design spec: Architecture/Modules/J - Memory Module.md
Backing store choice: Architecture/Decisions Log.md, Round 19 - LangGraph's own `SqliteStore`
(bundled with `langgraph-checkpoint-sqlite`, already a dependency) rather than standing up a
separate Chroma collection with a custom adapter: it already provides a persistent, file-based
`BaseStore` with built-in vector search (via `sqlite-vec`), so no extra glue code is needed.
"""

from __future__ import annotations

from kathrena.memory.config import MemoryConfig


def open_memory_store(config: MemoryConfig):
    """Open (creating if needed) Kathrena's memory database. Returns a `SqliteStore`.

    Kept open for the whole process's lifetime rather than scoped to a `with` block - `SqliteStore`
    serializes its own access internally (a `threading.Lock` per connection), so it's safe to share
    across the threads that touch it (Chainlit's event loop via `search_memory`, and LangMem's own
    background reflection thread via `remember`).
    """
    # Imported lazily so importing this module doesn't require sentence-transformers/langgraph's
    # sqlite store extras unless a store is actually opened.
    import sqlite3

    from langchain_huggingface import HuggingFaceEmbeddings
    from langgraph.store.sqlite import SqliteStore

    config.store_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(config.store_path), check_same_thread=False, isolation_level=None)
    embeddings = HuggingFaceEmbeddings(model_name=config.embedding_model_name)
    store = SqliteStore(
        conn,
        index={"dims": config.embedding_dims, "embed": embeddings, "fields": ["content"]},
    )
    store.setup()
    return store
