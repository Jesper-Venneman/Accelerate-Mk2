"""Tests for Module F's resumable indexing graph (kathrena.rag_index.indexer)."""

from __future__ import annotations

import pytest

from kathrena.rag_index import indexer


def test_run_full_index_indexes_every_discovered_file(rag_config, fake_store):
    rag_config.vault_root.mkdir(parents=True)
    (rag_config.vault_root / "a.md").write_text("Note A", encoding="utf-8")
    (rag_config.vault_root / "b.md").write_text("Note B", encoding="utf-8")

    indexed_count = indexer.run_full_index(rag_config, fake_store)

    assert indexed_count == 2
    assert set(fake_store.docs) == {"a.md", "b.md"}


def test_run_full_index_resumes_after_a_crash(rag_config, fake_store, monkeypatch):
    rag_config.vault_root.mkdir(parents=True)
    (rag_config.vault_root / "a.md").write_text("Note A", encoding="utf-8")
    (rag_config.vault_root / "b.md").write_text("Note B", encoding="utf-8")

    real_index_one = indexer.index_one
    processed = []

    def flaky_index_one(config, store, path):
        processed.append(path.name)
        if path.name == "b.md":
            raise RuntimeError("simulated crash")
        real_index_one(config, store, path)

    monkeypatch.setattr(indexer, "index_one", flaky_index_one)
    with pytest.raises(RuntimeError, match="simulated crash"):
        indexer.run_full_index(rag_config, fake_store)

    # "a.md" was indexed before the crash; "b.md" wasn't reached yet.
    assert set(fake_store.docs) == {"a.md"}

    monkeypatch.setattr(indexer, "index_one", real_index_one)
    final_count = indexer.run_full_index(rag_config, fake_store)

    # Resumed from the checkpoint rather than restarting - "a.md" was not re-processed.
    assert processed == ["a.md", "b.md"]
    assert final_count == 2
    assert set(fake_store.docs) == {"a.md", "b.md"}
