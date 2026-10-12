"""Shared pytest fixtures for Module G's test suite."""

from __future__ import annotations

import pytest

from kathrena.agent_core.config import AgentCoreConfig
from kathrena.agent_core.web_search import SearchHit
from kathrena.approval_gate.config import ApprovalGateConfig
from kathrena.project_management.config import ProjectManagementConfig
from kathrena.rag_index.vector_store import SearchResult


@pytest.fixture
def agent_config(tmp_path) -> AgentCoreConfig:
    """An AgentCoreConfig rooted in a fresh temp directory, isolated per test."""
    return AgentCoreConfig(
        checkpoint_path=tmp_path / "agent_checkpoints.sqlite",
        vault_root=tmp_path / "vault",
    )


@pytest.fixture
def approval_config(tmp_path) -> ApprovalGateConfig:
    """An ApprovalGateConfig rooted in a temp dir - same pattern as tests/approval_gate."""
    return ApprovalGateConfig(
        vault_root=tmp_path / "vault",
        checkpoint_path=tmp_path / "approval_checkpoints.sqlite",
    )


@pytest.fixture
def pm_config(tmp_path) -> ProjectManagementConfig:
    """A ProjectManagementConfig rooted in a fresh temp vault - same pattern as
    tests/project_management."""
    return ProjectManagementConfig(vault_root=tmp_path / "vault")


class FakeVectorStore:
    """Read-only fake `VectorStore` - agent_core only ever searches, never writes."""

    def __init__(self, results: list[SearchResult] | None = None) -> None:
        self._results = results or []
        self.queries: list[str] = []

    def upsert(self, doc_id: str, chunks: list[str], metadata: dict[str, str]) -> None:
        raise NotImplementedError("kathrena.agent_core only reads from the vector store")

    def delete(self, doc_id: str) -> None:
        raise NotImplementedError("kathrena.agent_core only reads from the vector store")

    def search(self, query: str, k: int) -> list[SearchResult]:
        self.queries.append(query)
        return self._results[:k]


class ScriptedChatModel:
    """Fake chat model that returns pre-scripted AIMessages in sequence - no real LLM call."""

    def __init__(self, responses: list) -> None:
        self._responses = list(responses)
        self.invocations: list[list] = []

    def bind_tools(self, tools) -> ScriptedChatModel:
        return self

    def invoke(self, messages, config=None) -> object:
        self.invocations.append(list(messages))
        return self._responses.pop(0)


class FakeMemoryProvider:
    """Fake `MemoryProvider` - records what it was asked to remember, returns scripted recalls."""

    def __init__(self, recall_results: list[str] | None = None) -> None:
        self._recall_results = recall_results or []
        self.queries: list[str] = []
        self.remembered: list[tuple[list, str]] = []

    def recall(self, query: str) -> list[str]:
        self.queries.append(query)
        return self._recall_results

    def remember(self, messages: list, thread_id: str) -> None:
        self.remembered.append((messages, thread_id))


class FakeWebSearch:
    """Fake `WebSearch` - returns scripted hits, records what it was asked."""

    def __init__(self, hits: list[SearchHit] | None = None) -> None:
        self._hits = hits or []
        self.queries: list[str] = []

    def search(self, query: str, max_results: int) -> list[SearchHit]:
        self.queries.append(query)
        return self._hits[:max_results]


@pytest.fixture
def fake_vector_store():
    """Factory fixture: `fake_vector_store(results=[...])` -> a fresh `FakeVectorStore`."""
    return FakeVectorStore


@pytest.fixture
def scripted_chat_model():
    """Factory fixture: `scripted_chat_model(responses=[...])` -> a fresh `ScriptedChatModel`."""
    return ScriptedChatModel


@pytest.fixture
def fake_memory_provider():
    """Factory fixture: `fake_memory_provider(recall_results=[...])` -> a `FakeMemoryProvider`."""
    return FakeMemoryProvider


@pytest.fixture
def fake_web_search():
    """Factory fixture: `fake_web_search(hits=[...])` -> a fresh `FakeWebSearch`."""
    return FakeWebSearch
