"""Configuration for Module I's I3 skill (on-demand deadline lookup).

Design spec: Architecture/Modules/I - Project Management Modules.md
Decision: Architecture/Decisions Log.md, Round 20 (skill, not a background sub-agent).

Independent from every other module's config - only agrees on the shared "common" settings
section's `vault_root`, same as `kathrena.rag_index.config.RagIndexConfig`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from kathrena.settings import setting_int, setting_path, setting_str


@dataclass(frozen=True)
class ProjectManagementConfig:
    """Vault location and defaults for `kathrena.project_management`'s `list_deadlines` skill."""

    vault_root: Path = field(default_factory=lambda: setting_path("common", "vault_root", "."))

    # How many days ahead counts as "close" when the LLM asks for deadlines without saying a
    # window itself - can still be overridden per call (see build_list_deadlines_tool).
    default_within_days: int = field(
        default_factory=lambda: setting_int("project_management", "default_within_days", 30)
    )

    # Frontmatter key holding a note's due date, e.g. `due: 2026-09-15`.
    due_frontmatter_key: str = field(
        default_factory=lambda: setting_str("project_management", "due_frontmatter_key", "due")
    )

    include_glob: str = "**/*.md"
    exclude_dir_names: tuple[str, ...] = (".obsidian", ".git", ".venv", ".trash")
