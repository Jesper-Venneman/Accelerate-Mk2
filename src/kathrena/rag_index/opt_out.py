"""Per-project RAG opt-out check.

Design spec: Architecture/Modules/F - RAG Indexing Module.md
Decision: Architecture/Decisions Log.md, Round 6 (`rag-index: false` frontmatter flag).
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(.*?\n)---", re.DOTALL)


def _read_frontmatter(md_path: Path) -> dict:
    """Parse the YAML frontmatter block from the top of a `.md` file, if any."""
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError:
        return {}
    match = _FRONTMATTER_PATTERN.match(text)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


class OptOutChecker:
    """Whether a file falls under a project folder that opted out of RAG indexing.

    A project opts out via `rag-index: false` in its own `{Folder}/{Folder}.md` frontmatter -
    checked by walking every ancestor folder up to the vault root, not just the immediate parent,
    so files nested inside a project's subfolders inherit its opt-out too. Results are cached per
    folder since many files typically share the same project ancestor.
    """

    def __init__(self, vault_root: Path, frontmatter_key: str = "rag-index") -> None:
        self._vault_root = vault_root
        self._frontmatter_key = frontmatter_key
        self._cache: dict[Path, bool] = {}

    def is_opted_out(self, path: Path) -> bool:
        return any(self._folder_opted_out(folder) for folder in self._ancestors(path))

    def _ancestors(self, path: Path):
        folder = path.parent
        while True:
            yield folder
            if folder == self._vault_root or folder.parent == folder:
                return
            folder = folder.parent

    def _folder_opted_out(self, folder: Path) -> bool:
        if folder not in self._cache:
            note_path = folder / f"{folder.name}.md"
            self._cache[folder] = _read_frontmatter(note_path).get(self._frontmatter_key) is False
        return self._cache[folder]
