"""Tests for Module D (kathrena.voice_log.log_writer)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from kathrena.voice_log.log_writer import LogEntry, write_log
from kathrena.voice_log.project_router import LogType, RouteResult


def test_write_project_log(config):
    destination = config.resolve("01 - Projects") / "Accelerate"
    entry = LogEntry(
        audio_path=Path("VoiceLog_2026-01-02_03-04-05.wav"),
        transcript="Project Accelerate is going well.",
        recorded_at=datetime(2026, 1, 2, 3, 4, 5),
        route=RouteResult(LogType.PROJECT, destination),
        summary="- Progress is good.",
    )

    written_path = write_log(config, entry)

    expected = destination / "Ω - logs" / "ProjectLog_Accelerate_2026-01-02--03-04-05.md"
    assert written_path == expected
    content = written_path.read_text(encoding="utf-8")
    assert content.count("---") == 2
    assert "Project Accelerate is going well." in content
    assert "- Progress is good." in content
    expected_embed = "![[91 - Resources/81 - logs/Processed logs/VoiceLog_2026-01-02_03-04-05.wav]]"
    assert expected_embed in content


def test_write_unsorted_log(config):
    entry = LogEntry(
        audio_path=Path("VoiceLog_2026-01-02_03-04-05.wav"),
        transcript="No project mentioned here.",
        recorded_at=datetime(2026, 1, 2, 3, 4, 5),
        route=RouteResult(LogType.UNSORTED, config.unsorted_logs_dir),
        summary="- Nothing specific.",
    )

    written_path = write_log(config, entry)

    assert written_path == config.unsorted_logs_dir / "ProjectLog_None_2026-01-02--03-04-05.md"


def test_write_vocal_journal_strips_prefix_and_skips_summary(config):
    entry = LogEntry(
        audio_path=Path("VoiceLog_2026-01-02_03-04-05.wav"),
        transcript="Edit to log, remember to buy milk.",
        recorded_at=datetime(2026, 1, 2, 3, 4, 5),
        route=RouteResult(LogType.VOCAL_JOURNAL, config.vocal_journal_dir),
    )

    written_path = write_log(config, entry)

    assert written_path == config.vocal_journal_dir / "VocalJournal_2026-01-02.md"
    content = written_path.read_text(encoding="utf-8")
    assert "Edit to log" not in content
    assert "remember to buy milk." in content


def test_write_vocal_journal_appends_multiple_entries_same_day(config):
    first = LogEntry(
        audio_path=Path("a.wav"),
        transcript="Edit to log, first thought.",
        recorded_at=datetime(2026, 1, 2, 3, 0, 0),
        route=RouteResult(LogType.VOCAL_JOURNAL, config.vocal_journal_dir),
    )
    second = LogEntry(
        audio_path=Path("b.wav"),
        transcript="Edit to log, second thought.",
        recorded_at=datetime(2026, 1, 2, 9, 0, 0),
        route=RouteResult(LogType.VOCAL_JOURNAL, config.vocal_journal_dir),
    )

    write_log(config, first)
    written_path = write_log(config, second)

    content = written_path.read_text(encoding="utf-8")
    assert "first thought." in content
    assert "second thought." in content
    assert content.count("---") == 2
