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
    """Default `VectorStore`: an embedded Chroma collection."""

    def __init__(self, config: RagIndexConfig) -> None:
        # Imported lazily so importing this module doesn't require chromadb/sentence-transformers
        # unless a ChromaVectorStore is actually constructed.
        from langchain_chroma import Chroma
        from langchain_huggingface import HuggingFaceEmbeddings

        embeddings = HuggingFaceEmbeddings(model_name=config.embedding_model_name)
        self._store = Chroma(
            collection_name=config.collection_name,
            embedding_function=embeddings,
            persist_directory=str(config.persist_directory),
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
