"""Central settings store: the single source of truth every module's config.py reads through.

Design spec: Architecture/Architecture Overview.md#Runtime architecture
Decision: Architecture/Decisions Log.md, Round 25.
"""

from __future__ import annotations

from kathrena.settings.bootstrap import SettingsNotConfiguredError, ensure_configured
from kathrena.settings.store import (
    SettingsStore,
    get_store,
    setting_bool,
    setting_float,
    setting_int,
    setting_path,
    setting_str,
)

__all__ = [
    "SettingsNotConfiguredError",
    "SettingsStore",
    "ensure_configured",
    "get_store",
    "setting_bool",
    "setting_float",
    "setting_int",
    "setting_path",
    "setting_str",
]
