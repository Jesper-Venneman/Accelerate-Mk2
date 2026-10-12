"""Shared pytest fixtures for Module F's test suite."""

from __future__ import annotations

import pytest

from kathrena.rag_index.config import RagIndexConfig
from kathrena.rag_index.vector_store import SearchResult, VectorStore


@pytest.fixture
def rag_config(tmp_path) -> RagIndexConfig:
    """A RagIndexConfig rooted in a fresh temp directory, isolated per test."""
    return RagIndexConfig(
        vault_root=tmp_path / "vault",
        persist_directory=tmp_path / "chroma",
        checkpoint_path=tmp_path / "checkpoints.sqlite",
    )


class FakeVectorStore:
    """In-memory `VectorStore` for tests - no Chroma/embeddings needed."""

    def __init__(self) -> None:
        self.docs: dict[str, list[str]] = {}

    def upsert(self, doc_id: str, chunks: list[str], metadata: dict[str, str]) -> None:
        self.docs[doc_id] = list(chunks)

    def delete(self, doc_id: str) -> None:
        self.docs.pop(doc_id, None)

    def search(self, query: str, k: int) -> list[SearchResult]:
        # No real relevance ranking - good enough for tests that don't exercise search directly.
        results = [
            SearchResult(content=chunk, source_path=doc_id)
            for doc_id, chunks in self.docs.items()
            for chunk in chunks
        ]
        return results[:k]


@pytest.fixture
def fake_store() -> VectorStore:
    return FakeVectorStore()
