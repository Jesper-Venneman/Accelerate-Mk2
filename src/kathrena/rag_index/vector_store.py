"""Swappable vector store interface, backed by Chroma by default.

Design spec: Architecture/Modules/F - RAG Indexing Module.md
Tech choice: Architecture/Decisions Log.md, Round 5 (Chroma + BAAI/bge-small-en-v1.5).
Fallback candidates if this doesn't work out: Architecture/Modules/F - RAG Indexing Module.md
(LanceDB/Qdrant, nomic-embed-text/all-MiniLM-L6-v2).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from kathrena.rag_index.config import RagIndexConfig


@dataclass(frozen=True)
class SearchResult:
    """One retrieved chunk - used by `kathrena.agent_core` (Module G) to ground its answers."""

    content: str
    source_path: str


class VectorStore(Protocol):
    """Swappable interface so the vector store/embedding model can change without touching callers.

    Callers only depend on this Protocol - see `Considered and rejected` in the design spec for why.
    """

    def upsert(self, doc_id: str, chunks: list[str], metadata: dict[str, str]) -> None: ...
    def delete(self, doc_id: str) -> None: ...
    def search(self, query: str, k: int) -> list[SearchResult]: ...


class ChromaVectorStore:
    """Default `VectorStore`: a Chroma collection reached over HTTP via a shared server process."""

    def __init__(self, config: RagIndexConfig) -> None:
        # Imported lazily so importing this module doesn't require chromadb/sentence-transformers
        # unless a ChromaVectorStore is actually constructed.
        import time

        import chromadb
        from langchain_chroma import Chroma
        from langchain_huggingface import HuggingFaceEmbeddings

        embeddings = HuggingFaceEmbeddings(model_name=config.embedding_model_name)

        # The server may still be starting up when this races against it (start.ps1 launches the
        # server and its clients together) - retry briefly instead of failing on the first attempt.
        client = None
        last_error: Exception | None = None
        for _attempt in range(config.chroma_connect_retries):
            try:
                candidate = chromadb.HttpClient(host=config.chroma_host, port=config.chroma_port)
                candidate.heartbeat()
                client = candidate
                break
            except Exception as exc:
                last_error = exc
                time.sleep(config.chroma_connect_retry_delay_seconds)
        if client is None:
            raise ConnectionError(
                f"Could not reach the Chroma server at {config.chroma_host}:{config.chroma_port} "
                f"after {config.chroma_connect_retries} attempt(s) - is `chroma run` (see "
                "start.ps1) actually running?"
            ) from last_error

        self._store = Chroma(
            client=client,
            collection_name=config.collection_name,
            embedding_function=embeddings,
        )

    def upsert(self, doc_id: str, chunks: list[str], metadata: dict[str, str]) -> None:
        # Delete-then-add rather than a true update, since a file's chunk count can change
        # between re-indexes and stale trailing chunks would otherwise be left behind.
        self.delete(doc_id)
        if not chunks:
            return
        ids = [f"{doc_id}::{i}" for i in range(len(chunks))]
        metadatas = [{**metadata, "doc_id": doc_id, "chunk_index": i} for i in range(len(chunks))]
        self._store.add_texts(texts=chunks, ids=ids, metadatas=metadatas)

    def delete(self, doc_id: str) -> None:
        self._store.delete(where={"doc_id": doc_id})

    def search(self, query: str, k: int) -> list[SearchResult]:
        docs = self._store.similarity_search(query, k=k)
        return [
            SearchResult(content=doc.page_content, source_path=doc.metadata.get("path", ""))
            for doc in docs
        ]
