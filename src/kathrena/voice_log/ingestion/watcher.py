"""Filesystem watcher for new voice-log recordings.

Design spec: Architecture/Modules/A - Ingestion and Sync Layer.md
"""

from __future__ import annotations

import re
import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from kathrena.config import PipelineConfig

_VOICE_LOG_FILENAME = re.compile(r"^VoiceLog_.*\.wav$", re.IGNORECASE)

# Two filename conventions have been observed from different recording sources; try both
# before falling back to the file's modification time. The filename format is set by whatever
# recorded the audio, not by this module, so this stays permissive rather than assuming one
# canonical layout.
_TIMESTAMP_PATTERNS = (
    "VoiceLog_%d-%m-%Y--%H-%M-%S.wav",
    "VoiceLog_%Y-%m-%d_%H-%M-%S.wav",
)

NewVoiceLogHandler = Callable[[Path], None]


def is_voice_log(path: Path) -> bool:
    """Whether `path` looks like a voice log recording this pipeline should process."""
    return path.is_file() and bool(_VOICE_LOG_FILENAME.match(path.name))


def parse_recorded_at(path: Path) -> datetime:
    """Best-effort parse of when a voice log was recorded, from its filename."""
    for pattern in _TIMESTAMP_PATTERNS:
        try:
            return datetime.strptime(path.name, pattern)
        except ValueError:
            continue
    return datetime.fromtimestamp(path.stat().st_mtime)


class VoiceLogWatcher:
    """Watches `config.unprocessed_dir` for new voice logs and hands each to `on_new_log`.

    Deliberately takes a plain callback rather than importing Modules B-E directly, so this
    module has no knowledge of what happens downstream - swap the callback and the rest of the
    pipeline changes with it.
    """

    def __init__(self, config: PipelineConfig, on_new_log: NewVoiceLogHandler) -> None:
        self._config = config
        self._on_new_log = on_new_log
        self._observer = Observer()

    def process_existing(self) -> None:
        """Process any voice logs already sitting in the drop folder before watching started."""
        for path in sorted(self._config.unprocessed_dir.glob("*.wav")):
            if is_voice_log(path):
                self._on_new_log(path)

    def start(self) -> None:
        """Begin watching for new voice logs. Runs on a background thread until `stop()`."""
        handler = _Handler(self._on_new_log)
        self._observer.schedule(handler, str(self._config.unprocessed_dir), recursive=False)
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()

    def mark_processed(self, path: Path) -> None:
        """Move a fully-processed voice log out of the drop folder."""
        self._config.processed_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(self._config.processed_dir / path.name))


class _Handler(FileSystemEventHandler):
    def __init__(self, on_new_log: NewVoiceLogHandler) -> None:
        self._on_new_log = on_new_log

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if is_voice_log(path):
            self._on_new_log(path)
