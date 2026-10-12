"""Composition root for a full vault index: discover -> chunk -> embed -> upsert.

Design spec: Architecture/Modules/F - RAG Indexing Module.md

Orchestrated as a LangGraph graph rather than a plain loop, so a large or interrupted re-index
can resume from its last checkpoint instead of restarting - the same durable-execution pattern
used by `kathrena.approval_gate` (Module H). One node discovers pending files, another indexes
one file at a time; the checkpointer persists `pending`/`indexed_count` after every step.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TypedDict

from kathrena.rag_index.chunker import split_document
from kathrena.rag_index.config import RagIndexConfig
from kathrena.rag_index.discovery import discover_files
from kathrena.rag_index.vector_store import VectorStore

logger = logging.getLogger(__name__)


class IndexState(TypedDict):
    pending: list[str]
    indexed_count: int


def index_one(config: RagIndexConfig, store: VectorStore, path: Path) -> None:
    """Chunk, embed, and upsert a single file. Used by both the full-index graph and the watcher."""
    text = path.read_text(encoding="utf-8")
    chunks = split_document(text, config)
    relative = path.relative_to(config.vault_root)
    store.upsert(doc_id=str(relative), chunks=chunks, metadata={"path": str(relative)})
    logger.info("Indexed %s (%d chunk(s))", relative, len(chunks))


def build_indexing_graph(config: RagIndexConfig, store: VectorStore):
    """Build the (uncompiled) indexing graph. Compile with a checkpointer to make it resumable."""
    # Imported lazily so importing this module doesn't require langgraph unless used.
    from langgraph.graph import END, START, StateGraph

    def discover(state: IndexState) -> IndexState:
        if state["pending"]:
            return state  # a partial run's already in progress - don't re-discover
        files = discover_files(config)
        return {"pending": [str(p) for p in files], "indexed_count": 0}

    def index_next(state: IndexState) -> IndexState:
        pending = list(state["pending"])
        path = Path(pending.pop(0))
        index_one(config, store, path)
        return {"pending": pending, "indexed_count": state["indexed_count"] + 1}

    def route(state: IndexState) -> str:
        return "index_next" if state["pending"] else END

    graph = StateGraph(IndexState)
    graph.add_node("discover", discover)
    graph.add_node("index_next", index_next)
    graph.add_edge(START, "discover")
    graph.add_conditional_edges("discover", route)
    graph.add_conditional_edges("index_next", route)
    return graph


def run_full_index(
    config: RagIndexConfig, store: VectorStore, thread_id: str = "full-index"
) -> int:
    """Run a full vault index, resuming a previous incomplete run for `thread_id` if one exists."""
    # Imported lazily so importing this module doesn't require langgraph-checkpoint-sqlite
    # unless used.
    from langgraph.checkpoint.sqlite import SqliteSaver

    config.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    with SqliteSaver.from_conn_string(str(config.checkpoint_path)) as checkpointer:
        graph = build_indexing_graph(config, store).compile(checkpointer=checkpointer)
        run_config = {"configurable": {"thread_id": thread_id}}
        resuming = bool(graph.get_state(run_config).values.get("pending"))
        initial = None if resuming else {"pending": [], "indexed_count": 0}
        result = graph.invoke(initial, config=run_config)
    return result["indexed_count"]
