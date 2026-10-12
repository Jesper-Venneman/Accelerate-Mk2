"""Tests for Module F's file discovery (kathrena.rag_index.discovery)."""

from __future__ import annotations

from kathrena.rag_index.discovery import discover_files


def test_discover_files_finds_markdown_files(rag_config):
    rag_config.vault_root.mkdir(parents=True)
    (rag_config.vault_root / "note.md").write_text("Hello", encoding="utf-8")
    (rag_config.vault_root / "audio.wav").write_bytes(b"")

    found = discover_files(rag_config)

    assert found == [rag_config.vault_root / "note.md"]


def test_discover_files_skips_excluded_dirs(rag_config):
    excluded = rag_config.vault_root / ".obsidian"
    excluded.mkdir(parents=True)
    (excluded / "config.md").write_text("Should be skipped", encoding="utf-8")
    (rag_config.vault_root / "note.md").write_text("Hello", encoding="utf-8")

    found = discover_files(rag_config)

    assert found == [rag_config.vault_root / "note.md"]


def test_discover_files_skips_opted_out_project(rag_config):
    project_dir = rag_config.vault_root / "01 - Projects" / "Private"
    project_dir.mkdir(parents=True)
    (project_dir / "Private.md").write_text(
        "---\nsynonyms:\n  - Private\nrag-index: false\n---\n", encoding="utf-8"
    )
    (project_dir / "notes.md").write_text("Secret notes", encoding="utf-8")
    (rag_config.vault_root / "public.md").write_text("Public note", encoding="utf-8")

    found = discover_files(rag_config)

    assert found == [rag_config.vault_root / "public.md"]
