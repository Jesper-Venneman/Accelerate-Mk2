"""Shared pytest fixtures for the Kathrena test suite."""

from __future__ import annotations

import pytest

from kathrena.config import PipelineConfig
from kathrena.settings import store as settings_store


@pytest.fixture(autouse=True)
def _isolated_settings_store(tmp_path, monkeypatch):
    """Every test gets its own settings.yaml, isolated from the real project one and from every
    other test - config dataclasses' default_factory fields read through this store, so without
    this a bare `SomeConfig()` in any test would read/write the real `./data/settings.yaml`."""
    monkeypatch.setattr(settings_store, "settings", settings_store.SettingsStore(tmp_path / "settings.yaml"))


@pytest.fixture(autouse=True)
def _isolated_llm_log(tmp_path, monkeypatch):
    """`call_tools` and `LangMemProvider.remember` log to `LLMLoggingConfig()`'s polluting the
    real `data/logs/llm_calls.log`, this fixture redirects it to a temporary file."""
    import kathrena.llm_logging as llm_logging

    real_config = llm_logging.LLMLoggingConfig
    monkeypatch.setattr(
        llm_logging, "LLMLoggingConfig", lambda: real_config(path=tmp_path / "llm_calls.log")
    )


@pytest.fixture
def config(tmp_path) -> PipelineConfig:
    """A PipelineConfig rooted in a fresh temp directory, isolated per test."""
    return PipelineConfig(vault_root=tmp_path)
