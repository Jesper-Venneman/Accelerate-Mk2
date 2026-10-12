"""Discovers which vault files should be (re-)indexed.

Design spec: Architecture/Modules/F - RAG Indexing Module.md
"""

from __future__ import annotations

from pathlib import Path

from kathrena.rag_index.config import RagIndexConfig
from kathrena.rag_index.opt_out import OptOutChecker


def discover_files(config: RagIndexConfig) -> list[Path]:
    """List every markdown file in the vault that isn't excluded or opted out."""
    checker = OptOutChecker(config.vault_root, config.rag_index_frontmatter_key)
    files = []
    for path in sorted(config.vault_root.glob(config.include_glob)):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(config.vault_root).parts
        if any(part in config.exclude_dir_names for part in relative_parts):
            continue
        if checker.is_opted_out(path):
            continue
        files.append(path)
    return files
