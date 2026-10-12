"""Tests for Module F's incremental vault watcher (kathrena.rag_index.watcher)."""

from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from kathrena.rag_index import watcher as watcher_module
from kathrena.rag_index.opt_out import OptOutChecker
from kathrena.rag_index.watcher import VaultWatcher, _Handler


def _event(path, is_directory=False):
    return SimpleNamespace(src_path=str(path), is_directory=is_directory)


class _Recorder:
    """Fake `on_change`/`on_delete` callback that just records what it was called with."""

    def __init__(self) -> None:
        self.calls: list = []

    def __call__(self, path) -> None:
        self.calls.append(path)


def test_created_markdown_file_triggers_on_change(rag_config):
    rag_config.vault_root.mkdir(parents=True)
    note_path = rag_config.vault_root / "note.md"
    note_path.write_text("Hello vault", encoding="utf-8")
    on_change, on_delete = _Recorder(), _Recorder()
    handler = _Handler(rag_config, OptOutChecker(rag_config.vault_root), on_change, on_delete)

    handler.on_created(_event(note_path))

    assert on_change.calls == [note_path]
    assert on_delete.calls == []


def test_non_markdown_file_is_ignored(rag_config):
    rag_config.vault_root.mkdir(parents=True)
    audio_path = rag_config.vault_root / "clip.wav"
    audio_path.write_bytes(b"")
    on_change, on_delete = _Recorder(), _Recorder()
    handler = _Handler(rag_config, OptOutChecker(rag_config.vault_root), on_change, on_delete)

    handler.on_created(_event(audio_path))

    assert on_change.calls == []


def test_deleted_markdown_file_triggers_on_delete(rag_config):
    rag_config.vault_root.mkdir(parents=True)
    on_change, on_delete = _Recorder(), _Recorder()
    handler = _Handler(rag_config, OptOutChecker(rag_config.vault_root), on_change, on_delete)

    handler.on_deleted(_event(rag_config.vault_root / "note.md"))

    assert on_delete.calls == [rag_config.vault_root / "note.md"]


@pytest.fixture
def quiet_config(rag_config):
    """A rag_config with a very short quiet period so debounce tests run fast."""
    return rag_config.__class__(
        vault_root=rag_config.vault_root,
        persist_directory=rag_config.persist_directory,
        checkpoint_path=rag_config.checkpoint_path,
        watch_quiet_period_seconds=0.05,
    )


def test_reindex_is_debounced_until_quiet(quiet_config, fake_store, monkeypatch):
    quiet_config.vault_root.mkdir(parents=True)
    note_path = quiet_config.vault_root / "note.md"
    note_path.write_text("v1", encoding="utf-8")

    calls = []
    monkeypatch.setattr(
        watcher_module, "index_one", lambda config, store, path: calls.append(path)
    )

    watcher = VaultWatcher(quiet_config, fake_store)
    # Simulate a burst of rapid edits: each one should reset the quiet-period clock.
    watcher._schedule_reindex(note_path)
    time.sleep(0.02)
    watcher._schedule_reindex(note_path)
    time.sleep(0.02)
    watcher._schedule_reindex(note_path)

    assert calls == []  # still within the quiet period after the last edit

    time.sleep(0.1)

    assert calls == [note_path]  # exactly one reindex, after things went quiet


def test_delete_cancels_a_pending_reindex(quiet_config, fake_store, monkeypatch):
    quiet_config.vault_root.mkdir(parents=True)
    note_path = quiet_config.vault_root / "note.md"
    note_path.write_text("v1", encoding="utf-8")
    fake_store.docs["note.md"] = ["v1"]

    calls = []
    monkeypatch.setattr(
        watcher_module, "index_one", lambda config, store, path: calls.append(path)
    )

    watcher = VaultWatcher(quiet_config, fake_store)
    watcher._schedule_reindex(note_path)
    watcher._cancel_and_delete(note_path)

    time.sleep(0.1)

    assert calls == []  # the pending reindex never fired
    assert "note.md" not in fake_store.docs

