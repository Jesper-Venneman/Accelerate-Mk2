"""Tests for kathrena.memory.provider - LangMemProvider's hot-swap-by-rebuild behavior, including
the explicit `shutdown(wait=False)` on the old `ReflectionExecutor` (Decisions Log Round 28,
verified against LangMem's actual installed source), and the persisted per-thread marker
(Decisions Log Round 30) that caps what remember() re-submits on a long-running thread."""

from __future__ import annotations

import concurrent.futures

from kathrena.memory.config import MemoryConfig
from kathrena.memory.provider import LangMemProvider


class _FakeStore:
    """Minimal stand-in for langgraph's BaseStore - just enough get/put for marker bookkeeping."""

    def __init__(self) -> None:
        self._items: dict[tuple, dict] = {}

    def get(self, namespace, key):
        value = self._items.get((namespace, key))
        return None if value is None else _FakeItem(value)

    def put(self, namespace, key, value, index=None):
        self._items[(namespace, key)] = value


class _FakeItem:
    def __init__(self, value: dict) -> None:
        self.value = value


class _FakeExecutor:
    """Stands in for langmem.ReflectionExecutor - records submissions and shutdown calls."""

    def __init__(self, manager, store=None) -> None:
        self.manager = manager
        self.store = store
        self.submitted: list[dict] = []
        self.submitted_configs: list[dict] = []
        self.shutdown_calls: list[bool] = []

    def submit(self, payload, /, config=None, *, after_seconds=0):
        self.submitted.append(payload)
        self.submitted_configs.append(config)
        future: concurrent.futures.Future = concurrent.futures.Future()
        future.set_result(None)  # immediately "completes", same as real usage's done-callback
        return future

    def shutdown(self, wait=True, *, cancel_futures=False):
        self.shutdown_calls.append(wait)


def _fake_create_memory_store_manager(chat_model, *, namespace, store):
    return {"chat_model": chat_model, "namespace": namespace, "store": store}


def _patch_langmem_and_llm(monkeypatch, instances: list[_FakeExecutor]) -> None:
    import langmem

    import kathrena.llm as kathrena_llm

    def fake_executor_factory(manager, store=None):
        executor = _FakeExecutor(manager, store)
        instances.append(executor)
        return executor

    monkeypatch.setattr(langmem, "ReflectionExecutor", fake_executor_factory)
    monkeypatch.setattr(langmem, "create_memory_store_manager", _fake_create_memory_store_manager)
    monkeypatch.setattr(kathrena_llm, "resolve_profile", lambda name: name)
    monkeypatch.setattr(
        kathrena_llm, "build_chat_model", lambda profile, log_label=None: f"model-for-{profile}"
    )


def test_rebuilds_only_once_while_the_profile_stays_the_same(tmp_path, monkeypatch):
    instances: list[_FakeExecutor] = []
    _patch_langmem_and_llm(monkeypatch, instances)

    config = MemoryConfig(store_path=tmp_path / "memory.sqlite")
    provider = LangMemProvider(config, store=_FakeStore())

    provider.remember([], "thread-1")
    provider.remember([], "thread-1")

    assert len(instances) == 1
    assert instances[0].shutdown_calls == []


def test_remember_attaches_a_logging_callback_via_submit_config_not_the_model(tmp_path, monkeypatch):
    """The model handed to create_memory_store_manager must stay a plain BaseChatModel - LangMem
    does its own isinstance(model, BaseChatModel) check internally, which a build_chat_model
    .with_config(...) binding would fail (the real startup crash this guards against)."""
    from kathrena.llm_logging import LoggingCallbackHandler

    instances: list[_FakeExecutor] = []
    _patch_langmem_and_llm(monkeypatch, instances)

    config = MemoryConfig(store_path=tmp_path / "memory.sqlite")
    provider = LangMemProvider(config, store=_FakeStore())

    provider.remember([], "thread-1")

    submitted_config = instances[0].submitted_configs[-1]
    assert isinstance(submitted_config["callbacks"][0], LoggingCallbackHandler)
    # the chat model itself was never wrapped - build_chat_model got no log_label (see
    # _patch_langmem_and_llm's fake, which would otherwise return a different value for one)
    assert instances[0].manager["chat_model"] == "model-for-local"


def test_rebuilds_and_shuts_down_the_old_executor_when_the_profile_changes(tmp_path, monkeypatch):
    from kathrena.settings import get_store

    instances: list[_FakeExecutor] = []
    _patch_langmem_and_llm(monkeypatch, instances)

    config = MemoryConfig(store_path=tmp_path / "memory.sqlite")
    provider = LangMemProvider(config, store=_FakeStore())
    provider.remember([], "thread-1")
    first_executor = instances[0]

    get_store().set_value("memory", "llm_profile", "cloud")
    provider.remember([], "thread-1")

    assert len(instances) == 2
    assert first_executor.shutdown_calls == [False]  # non-blocking, per Decisions Log Round 28
    assert instances[1].shutdown_calls == []


def test_remember_sends_full_history_the_first_time(tmp_path, monkeypatch):
    instances: list[_FakeExecutor] = []
    _patch_langmem_and_llm(monkeypatch, instances)

    config = MemoryConfig(store_path=tmp_path / "memory.sqlite", marker_overlap_messages=1)
    provider = LangMemProvider(config, store=_FakeStore())

    provider.remember(["m0", "m1", "m2"], "thread-1")

    assert instances[0].submitted[-1]["messages"] == ["m0", "m1", "m2"]


def test_remember_only_resends_the_unsent_tail_plus_overlap_after_the_marker_advances(
    tmp_path, monkeypatch
):
    instances: list[_FakeExecutor] = []
    _patch_langmem_and_llm(monkeypatch, instances)

    config = MemoryConfig(store_path=tmp_path / "memory.sqlite", marker_overlap_messages=1)
    provider = LangMemProvider(config, store=_FakeStore())

    provider.remember(["m0", "m1", "m2"], "thread-1")  # completes immediately, marker -> 3
    provider.remember(["m0", "m1", "m2", "m3", "m4"], "thread-1")

    # marker=3, overlap=1 -> resend from index 2, not the whole history again
    assert instances[0].submitted[-1]["messages"] == ["m2", "m3", "m4"]


def test_marker_does_not_advance_when_the_submission_is_cancelled(tmp_path, monkeypatch):
    """The exact gap flagged in Architecture/Investigations/Memory Context Management.md -
    advancing the marker at submit time (rather than from a completion callback) would have
    silently skipped this range once a later call superseded it."""
    instances: list[_FakeExecutor] = []
    _patch_langmem_and_llm(monkeypatch, instances)

    config = MemoryConfig(store_path=tmp_path / "memory.sqlite")
    provider = LangMemProvider(config, store=_FakeStore())

    def cancelled_submit(payload, /, config=None, *, after_seconds=0):
        future: concurrent.futures.Future = concurrent.futures.Future()
        future.cancel()
        return future

    provider._executor.submit = cancelled_submit
    provider.remember(["m0", "m1"], "thread-1")

    assert provider._read_marker("thread-1") == 0
