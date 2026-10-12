"""Tests for kathrena.approval_gate.vault_writer - the module's one dangerous operation."""

from __future__ import annotations

import pytest

from kathrena.approval_gate.vault_writer import UnsafeTargetPathError, write_approved_content


def test_writes_a_new_file_creating_parent_folders(tmp_path):
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    written = write_approved_content(vault_root, "Projects/Foo/Foo.md", "hello")

    assert written == vault_root / "Projects" / "Foo" / "Foo.md"
    assert written.read_text(encoding="utf-8") == "hello"


def test_overwrites_an_existing_file(tmp_path):
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "note.md").write_text("old", encoding="utf-8")

    write_approved_content(vault_root, "note.md", "new")

    assert (vault_root / "note.md").read_text(encoding="utf-8") == "new"


@pytest.mark.parametrize(
    "target_path",
    ["../outside.md", "sub/../../outside.md", "/etc/passwd", "nested/../../../outside.md"],
)
def test_rejects_paths_that_escape_the_vault_root(tmp_path, target_path):
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    with pytest.raises(UnsafeTargetPathError):
        write_approved_content(vault_root, target_path, "malicious")
