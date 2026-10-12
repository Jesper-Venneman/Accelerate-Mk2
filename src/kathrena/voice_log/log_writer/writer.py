"""Writes the final log entry in the format matching its routed log type.

Design spec: Architecture/Modules/D - Log Writer Module.md

Note: Mk1 also created an `Archive/` subfolder and a sorting-spec frontmatter file the first
time a project logged - that behavior isn't part of the current Architecture spec, so it's
deliberately not carried over here. Flag if you want it back.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from kathrena.config import PipelineConfig
from kathrena.voice_log.project_router import LogType, RouteResult

_EDIT_TO_LOG_PREFIX = re.compile(r"^edit to log(, )?", re.IGNORECASE)
_PROJECT_LOGS_SUBDIR = "Ω - logs"


@dataclass(frozen=True)
class LogEntry:
    """Everything needed to write one voice log, regardless of its type."""

    audio_path: Path
    transcript: str
    recorded_at: datetime
    route: RouteResult
    summary: str | None = None
    """None for Vocal Journal entries - Module E's refinement is skipped for those."""


def write_log(config: PipelineConfig, entry: LogEntry) -> Path:
    """Write `entry` to disk in the format matching its routed log type.

    Returns the path written to.
    """
    if entry.route.log_type is LogType.VOCAL_JOURNAL:
        return _write_vocal_journal(config, entry)
    if entry.route.log_type is LogType.UNSORTED:
        return _write_project_or_unsorted(
            config, entry, config.unsorted_logs_dir, project_name=None
        )
    log_dir = entry.route.destination / _PROJECT_LOGS_SUBDIR
    return _write_project_or_unsorted(
        config, entry, log_dir, project_name=entry.route.destination.name
    )


def _audio_embed(config: PipelineConfig, audio_path: Path) -> str:
    return f"![[{config.processed_dir_name}/{audio_path.name}]]"


def _write_project_or_unsorted(
    config: PipelineConfig, entry: LogEntry, log_dir: Path, project_name: str | None
) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    label = project_name or "None"
    filename = f"ProjectLog_{label}_{entry.recorded_at:%Y-%m-%d--%H-%M-%S}.md"
    path = log_dir / filename
    body = (
        f"{_audio_embed(config, entry.audio_path)}\n\n"
        "---\n\n"
        f"{entry.transcript}\n\n"
        "---\n\n"
        f"{entry.summary or ''}\n\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


def _write_vocal_journal(config: PipelineConfig, entry: LogEntry) -> Path:
    config.vocal_journal_dir.mkdir(parents=True, exist_ok=True)
    filename = f"VocalJournal_{entry.recorded_at:%Y-%m-%d}.md"
    path = config.vocal_journal_dir / filename
    stripped_transcript = _EDIT_TO_LOG_PREFIX.sub("", entry.transcript).strip()
    block = f"{_audio_embed(config, entry.audio_path)}\n{stripped_transcript}\n\n---\n\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(block)
    return path
