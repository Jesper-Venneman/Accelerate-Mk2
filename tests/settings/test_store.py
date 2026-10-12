"""Tests for kathrena.settings.store - the central settings file."""

from __future__ import annotations

from pathlib import Path

from kathrena.settings.store import SettingsStore, setting_bool, setting_int, setting_path


def test_value_seeds_and_persists_the_default_on_first_read(tmp_path):
    path = tmp_path / "settings.yaml"
    store = SettingsStore(path)

    result = store.value("agent_core", "rag_top_k", 4)

    assert result == 4
    assert path.is_file()
    assert "rag_top_k" in path.read_text(encoding="utf-8")


def test_value_returns_the_persisted_value_once_seeded(tmp_path):
    store = SettingsStore(tmp_path / "settings.yaml")
    store.value("agent_core", "rag_top_k", 4)

    result = store.value("agent_core", "rag_top_k", 999)  # different default, should be ignored

    assert result == 4


def test_set_value_overrides_a_previously_seeded_value(tmp_path):
    store = SettingsStore(tmp_path / "settings.yaml")
    store.value("agent_core", "rag_top_k", 4)

    store.set_value("agent_core", "rag_top_k", 8)

    assert store.value("agent_core", "rag_top_k", 4) == 8


def test_a_second_store_instance_sees_changes_persisted_by_the_first(tmp_path):
    path = tmp_path / "settings.yaml"
    first = SettingsStore(path)
    first.set_value("agent_core", "rag_top_k", 8)

    second = SettingsStore(path)

    assert second.value("agent_core", "rag_top_k", 4) == 8


def test_new_field_is_seeded_independently_of_existing_ones_in_the_same_section(tmp_path):
    path = tmp_path / "settings.yaml"
    store = SettingsStore(path)
    store.value("agent_core", "rag_top_k", 4)

    # Simulates a module adding a new field after the file already has some values in that section.
    result = store.value("agent_core", "agent_name", "Kathrena")

    assert result == "Kathrena"
    assert store.value("agent_core", "rag_top_k", 999) == 4


def test_setting_bool_seeds_a_bool_default(tmp_path):
    store = SettingsStore(tmp_path / "settings.yaml")

    result = store.value("chat_interface", "always_speak", False)

    assert result is False


def test_module_level_helpers_read_through_the_currently_patched_global_store(tmp_path, monkeypatch):
    from kathrena.settings import store as settings_store

    monkeypatch.setattr(settings_store, "settings", SettingsStore(tmp_path / "settings.yaml"))

    assert setting_int("agent_core", "rag_top_k", 4) == 4
    assert setting_bool("chat_interface", "voice_output_enabled", True) is True
    assert setting_path("agent_core", "vault_root", ".") == Path(".").expanduser()
