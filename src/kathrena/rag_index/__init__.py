"""Module F: RAG Indexing.

Design spec: Architecture/Modules/F - RAG Indexing Module.md

Keeps a searchable Chroma vector index of the vault up to date for
`kathrena.agent_core` (Module G) and `kathrena.project_management` (Module I),
orchestrated as a resumable LangGraph run.
"""

from kathrena.rag_index.chunker import split_document
from kathrena.rag_index.config import RagIndexConfig
from kathrena.rag_index.discovery import discover_files
from kathrena.rag_index.indexer import index_one, run_full_index
from kathrena.rag_index.opt_out import OptOutChecker
from kathrena.rag_index.vector_store import ChromaVectorStore, VectorStore
from kathrena.rag_index.watcher import VaultWatcher

__all__ = [
    "ChromaVectorStore",
    "OptOutChecker",
    "RagIndexConfig",
    "VaultWatcher",
    "VectorStore",
    "discover_files",
    "index_one",
    "run_full_index",
    "split_document",
]
