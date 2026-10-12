"""Tests for kathrena.settings.bootstrap - the startup configuration gate."""

from __future__ import annotations

import pytest

from kathrena.settings.bootstrap import (
    VAULT_ROOT_PLACEHOLDER,
    SettingsNotConfiguredError,
    ensure_configured,
)
from kathrena.settings.store import get_store


def test_ensure_configured_raises_a_creation_message_when_the_file_did_not_exist_yet():
    with pytest.raises(SettingsNotConfiguredError, match="Created"):
        ensure_configured()


def test_ensure_configured_raises_an_edit_message_once_the_file_already_exists():
    with pytest.raises(SettingsNotConfiguredError):
        ensure_configured()  # first call: file doesn't exist yet, gets created

    with pytest.raises(SettingsNotConfiguredError, match="still unset"):
        ensure_configured()  # second call: file exists now, still unconfigured


def test_ensure_configured_seeds_the_placeholder_on_first_run():
    with pytest.raises(SettingsNotConfiguredError):
        ensure_configured()

    store = get_store()
    assert store.value("common", "vault_root", "unused") == VAULT_ROOT_PLACEHOLDER


def test_ensure_configured_seeds_llm_profiles_on_first_run():
    with pytest.raises(SettingsNotConfiguredError):
        ensure_configured()

    profiles = get_store().raw_section("llm_profiles")
    assert set(profiles) == {"local", "cloud"}


def test_ensure_configured_passes_once_vault_root_is_set(tmp_path):
    store = get_store()
    store.set_value("common", "vault_root", str(tmp_path))

    ensure_configured()  # should not raise


def test_ensure_configured_does_not_overwrite_an_already_configured_vault_root(tmp_path):
    store = get_store()
    store.set_value("common", "vault_root", str(tmp_path))

    ensure_configured()

    assert store.value("common", "vault_root", "unused") == str(tmp_path)
