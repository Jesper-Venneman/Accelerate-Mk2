"""Scans the vault for notes with a due date - Module I's I3 skill.

Design spec: Architecture/Modules/I - Project Management Modules.md
Decision: Architecture/Decisions Log.md, Round 20.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from kathrena.project_management.config import ProjectManagementConfig

# Duplicated from kathrena.rag_index.opt_out's _read_frontmatter rather than shared - small
# per-module helpers are kept independent throughout this codebase so modules stay decoupled.
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


def _parse_due_date(value: object) -> date | None:
    """Coerce a frontmatter due-date value to a `date`, or None if missing/unparseable.

    PyYAML auto-parses unquoted `due: 2026-09-15` into a `date` already; this also handles a
    quoted string (`due: "2026-09-15"`) or an accidental `datetime` (`due: 2026-09-15 09:00`).
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


@dataclass(frozen=True)
class Deadline:
    """One vault note's due date, as surfaced to Kathrena's `list_deadlines` tool."""

    target_path: str  # vault-relative, e.g. "01 - Projects/Foo/Foo.md"
    title: str  # the note's filename stem, e.g. "Foo"
    due_date: date


def list_upcoming_deadlines(
    config: ProjectManagementConfig,
    *,
    within_days: int | None = None,
    today: date | None = None,
) -> list[Deadline]:
    """Every vault note with a parseable due date, soonest first.

    `within_days=None` returns everything with a due date, regardless of how far off..
    """
    today = today or date.today()
    deadlines = []
    for path in sorted(config.vault_root.glob(config.include_glob)):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(config.vault_root).parts
        if any(part in config.exclude_dir_names for part in relative_parts):
            continue
        due_date = _parse_due_date(_read_frontmatter(path).get(config.due_frontmatter_key))
        if due_date is None:
            continue
        if within_days is not None and due_date > today + timedelta(days=within_days):
            continue
        deadlines.append(
            Deadline(
                target_path=str(path.relative_to(config.vault_root)).replace("\\", "/"),
                title=path.stem,
                due_date=due_date,
            )
        )
    return sorted(deadlines, key=lambda deadline: deadline.due_date)
