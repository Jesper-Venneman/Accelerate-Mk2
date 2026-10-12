"""Tests for Module A's pure-logic helpers (kathrena.voice_log.ingestion)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from kathrena.voice_log.ingestion import is_voice_log, parse_recorded_at


def test_is_voice_log_accepts_expected_filenames(tmp_path):
    path = tmp_path / "VoiceLog_26-04-2025--20-59-46.wav"
    path.write_bytes(b"")

    assert is_voice_log(path)


def test_is_voice_log_rejects_other_files(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("hello", encoding="utf-8")

    assert not is_voice_log(path)


def test_parse_recorded_at_handles_original_format():
    path = Path("VoiceLog_26-04-2025--20-59-46.wav")

    assert parse_recorded_at(path) == datetime(2025, 4, 26, 20, 59, 46)


def test_parse_recorded_at_handles_iso_style_format():
    path = Path("VoiceLog_2025-04-27_16-26-04.wav")

    assert parse_recorded_at(path) == datetime(2025, 4, 27, 16, 26, 4)


def test_parse_recorded_at_falls_back_to_mtime(tmp_path):
    path = tmp_path / "VoiceLog_unparseable_name.wav"
    path.write_bytes(b"")

    parsed = parse_recorded_at(path)

    assert parsed == datetime.fromtimestamp(path.stat().st_mtime)
