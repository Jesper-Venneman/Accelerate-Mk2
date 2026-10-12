"""Routes a transcript to a project, the unsorted bucket, or the vocal journal.

Design spec: Architecture/Modules/C - Project Router Module.md
Log-type behavior: Architecture/Log Types/Project Log.md, Unsorted Log.md, Vocal Journal.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import yaml

from kathrena.config import PipelineConfig

_YAML_PATTERN = re.compile(r"\A---\s*\n(.*?\n)---", re.DOTALL)


class LogType(StrEnum):
    PROJECT = "project"
    UNSORTED = "unsorted"
    VOCAL_JOURNAL = "vocal_journal"


@dataclass(frozen=True)
class RouteResult:
    """Where a transcript should be routed, and what kind of log entry to write."""

    log_type: LogType
    destination: Path
    """The matched project's folder, or the unsorted-logs/vocal-journal folder."""


def _read_yaml_block(md_path: Path) -> dict:
    """Parse the YAML block from the top of a project's `.md` file."""
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError:
        return {}
    match = _YAML_PATTERN.match(text)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def build_synonym_map(config: PipelineConfig) -> dict[str, Path]:
    """Scan each configured project directory for `{Project}/{Project}.md` synonyms.

    Mirrors Mk1's `build_synonym_map()`, plus the "edit to log" -> Vocal Journal special case.
    """
    synonym_map: dict[str, Path] = {
        config.edit_to_log_phrase.lower(): config.vocal_journal_dir,
    }
    for project_dir_name in config.project_dirs:
        base_dir = config.resolve(project_dir_name)
        if not base_dir.is_dir():
            continue
        for project_folder in sorted(p for p in base_dir.iterdir() if p.is_dir()):
            md_file = project_folder / f"{project_folder.name}.md"
            if not md_file.is_file():
                continue
            synonyms = _read_yaml_block(md_file).get("synonyms") or []
            for synonym in synonyms:
                synonym_map[str(synonym).lower()] = project_folder
    return synonym_map


def route(transcript: str, synonym_map: dict[str, Path], config: PipelineConfig) -> RouteResult:
    """Find the earliest-mentioned synonym in `transcript` and route accordingly."""
    haystack = transcript.strip().lower()
    best_synonym: str | None = None
    best_index = -1
    for synonym in synonym_map:
        index = haystack.find(synonym)
        if index != -1 and (best_index == -1 or index < best_index):
            best_index = index
            best_synonym = synonym

    if best_synonym is None:
        return RouteResult(LogType.UNSORTED, config.unsorted_logs_dir)

    destination = synonym_map[best_synonym]
    if destination == config.vocal_journal_dir:
        return RouteResult(LogType.VOCAL_JOURNAL, destination)
    return RouteResult(LogType.PROJECT, destination)
