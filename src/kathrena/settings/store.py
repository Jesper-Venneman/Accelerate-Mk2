"""Central, file-backed settings store: single source of truth for every module's configuration.

Design spec: Architecture/Architecture Overview.md#Runtime architecture
Decision: Architecture/Decisions Log.md, Round 25.

Every module's config.py reads its default values through this module's `setting_*` helpers
instead of its own `os.environ`/`_env_*` helpers - same call shape (name, default) -> value, just
a different source. A setting is seeded with its caller-supplied default (and persisted) the
first time it's ever read, so a module adding a new field shows up in the file on the next run
with no separate migration step. Persists to `./data/settings.yaml` (local runtime data, already
covered by the `/data/` entry in .gitignore).
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

_DEFAULT_PATH = Path("./data/settings.yaml")


class SettingsStore:
    """A flat `(section, key) -> value` store, backed by one YAML file.

    Re-reads the file on every access rather than caching in memory, so a hand-edit made to the
    file while the app is running (or a change from another part of the same process) is always
    picked up - this is a single-user desktop app with a handful of settings reads per turn, not
    a hot path worth optimizing away the simplicity of "the file is always the source of truth."
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _DEFAULT_PATH
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    def _read(self) -> dict[str, dict[str, Any]]:
        import yaml

        if self._path.is_file():
            return yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
        return {}

    def _write(self, raw: dict[str, dict[str, Any]]) -> None:
        import yaml

        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(yaml.safe_dump(raw, sort_keys=True), encoding="utf-8")

    def value(self, section: str, key: str, default: Any) -> Any:
        """Current value for `section.key` - seeds and persists `default` the first time this
        specific key is read, so new fields auto-populate the file without a migration step."""
        with self._lock:
            raw = self._read()
            section_values = raw.setdefault(section, {})
            if key not in section_values:
                section_values[key] = default
                self._write(raw)
            return section_values[key]

    def set_value(self, section: str, key: str, value: Any) -> None:
        """Persist a new value for `section.key` - used by the settings-changing tool."""
        with self._lock:
            raw = self._read()
            raw.setdefault(section, {})[key] = value
            self._write(raw)

    def raw_section(self, section: str) -> dict[str, Any]:
        """A read-only snapshot of everything currently stored under `section` - never seeds or
        persists anything, unlike `value()`."""
        with self._lock:
            return dict(self._read().get(section, {}))


# Module-level singleton every config.py's `setting_*` calls read through. Tests must never touch
# the real file - see tests/conftest.py's autouse `_isolated_settings_store` fixture, which
# monkeypatches this name to a fresh, temp-dir-backed store for the duration of each test.
settings = SettingsStore()


def get_store() -> SettingsStore:
    """The current global store - fetched fresh on every call (never cache the return value)
    so code always sees the store tests/callers have patched in, not a stale reference."""
    return settings


def setting_str(section: str, key: str, default: str) -> str:
    return str(settings.value(section, key, default))


def setting_int(section: str, key: str, default: int) -> int:
    return int(settings.value(section, key, default))


def setting_float(section: str, key: str, default: float) -> float:
    return float(settings.value(section, key, default))


def setting_bool(section: str, key: str, default: bool) -> bool:
    return bool(settings.value(section, key, default))


def setting_path(section: str, key: str, default: str) -> Path:
    return Path(settings.value(section, key, default)).expanduser()
