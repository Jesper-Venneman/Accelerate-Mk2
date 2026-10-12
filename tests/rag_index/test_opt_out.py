"""Tests for Module F's per-project RAG opt-out check (kathrena.rag_index.opt_out)."""

from __future__ import annotations

from kathrena.rag_index.opt_out import OptOutChecker


def _write_project_note(vault_root, project_name: str, rag_index: bool) -> None:
    project_dir = vault_root / "01 - Projects" / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / f"{project_name}.md").write_text(
        f"---\nsynonyms:\n  - {project_name}\nrag-index: {str(rag_index).lower()}\n---\nNotes.\n",
        encoding="utf-8",
    )


def test_file_not_opted_out_by_default(rag_config):
    _write_project_note(rag_config.vault_root, "Accelerate", rag_index=True)
    checker = OptOutChecker(rag_config.vault_root)

    log_path = rag_config.vault_root / "01 - Projects" / "Accelerate" / "Ω - logs" / "log.md"

    assert not checker.is_opted_out(log_path)


def test_file_opted_out_via_project_frontmatter(rag_config):
    _write_project_note(rag_config.vault_root, "Blender", rag_index=False)
    checker = OptOutChecker(rag_config.vault_root)

    note_path = rag_config.vault_root / "01 - Projects" / "Blender" / "Blender.md"

    assert checker.is_opted_out(note_path)


def test_nested_file_inherits_opt_out(rag_config):
    _write_project_note(rag_config.vault_root, "Blender", rag_index=False)
    checker = OptOutChecker(rag_config.vault_root)

    nested = rag_config.vault_root / "01 - Projects" / "Blender" / "Ω - logs" / "log.md"

    assert checker.is_opted_out(nested)


def test_file_outside_any_project_is_not_opted_out(rag_config):
    checker = OptOutChecker(rag_config.vault_root)
    (rag_config.vault_root / "11 - Information").mkdir(parents=True)
    note_path = rag_config.vault_root / "11 - Information" / "Reference.md"

    assert not checker.is_opted_out(note_path)
