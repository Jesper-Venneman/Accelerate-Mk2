"""Tests for kathrena.llm - centralized LLM client construction."""

from __future__ import annotations

import pytest

from kathrena.llm import LLMProfile, LLMProfileError, build_chat_model, resolve_profile
from kathrena.settings.store import get_store


def test_resolve_profile_seeds_both_starter_profiles_on_first_call():
    with pytest.raises(LLMProfileError):
        resolve_profile("cloud")  # cloud's model is unset by default

    profiles = get_store().raw_section("llm_profiles")
    assert set(profiles) == {"local", "cloud"}
    assert profiles["local"]["max_tokens"] is None
    assert profiles["cloud"]["max_tokens"] == 8192  # cloud defaults to a cap, local doesn't


def test_resolve_profile_returns_the_local_starter_profile_by_default():
    profile = resolve_profile("local")

    assert profile == LLMProfile(
        provider="openai",
        model="local-model",
        base_url="http://127.0.0.1:5000/v1",
        api_key="not-needed",
    )


def test_resolve_profile_raises_for_an_unknown_profile_name():
    with pytest.raises(LLMProfileError, match="foo"):
        resolve_profile("foo")


def test_resolve_profile_raises_while_cloud_model_is_still_unset():
    with pytest.raises(LLMProfileError, match="model"):
        resolve_profile("cloud")


def test_resolve_profile_raises_while_base_url_is_still_unset_even_if_model_is_set():
    store = get_store()
    store.set_value(
        "llm_profiles",
        "cloud",
        {"provider": "openai", "model": "gpt-4o-mini", "base_url": None, "api_key": "sk-test"},
    )

    with pytest.raises(LLMProfileError, match="base_url"):
        resolve_profile("cloud")


def test_resolve_profile_reflects_a_manually_overridden_local_profile():
    store = get_store()
    store.set_value(
        "llm_profiles",
        "local",
        {
            "provider": "openai",
            "model": "custom-local-model",
            "base_url": "http://127.0.0.1:9000/v1",
            "api_key": "custom-key",
        },
    )

    profile = resolve_profile("local")

    assert profile == LLMProfile(
        provider="openai",
        model="custom-local-model",
        base_url="http://127.0.0.1:9000/v1",
        api_key="custom-key",
    )


def test_seed_default_profiles_backfills_max_tokens_into_an_already_seeded_profile():
    """A profile saved before `max_tokens` existed (Decisions Log Round 31) must still pick up
    the new default on next read - SettingsStore's per-key auto-seed doesn't reach inside an
    already-seeded profile's nested dict on its own."""
    store = get_store()
    store.set_value(
        "llm_profiles",
        "cloud",
        {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "base_url": "https://api.example.com/v1",
            "api_key": "sk-test",
        },
    )

    profile = resolve_profile("cloud")

    assert profile.max_tokens == 8192
    assert profile.model == "gpt-4o-mini"  # untouched by the backfill


def test_resolve_profile_reads_a_custom_max_tokens(monkeypatch):
    store = get_store()
    store.set_value(
        "llm_profiles",
        "local",
        {
            "provider": "openai",
            "model": "local-model",
            "base_url": "http://127.0.0.1:5000/v1",
            "api_key": "not-needed",
            "max_tokens": 512,
        },
    )

    assert resolve_profile("local").max_tokens == 512


def test_build_chat_model_always_passes_provider_and_model(monkeypatch):
    captured = {}

    def fake_init_chat_model(**kwargs):
        captured.update(kwargs)
        return "fake-model"

    monkeypatch.setattr("langchain.chat_models.init_chat_model", fake_init_chat_model)

    result = build_chat_model(LLMProfile(provider="openai", model="local-model"))

    assert result == "fake-model"
    assert captured == {"model": "local-model", "model_provider": "openai"}


def test_build_chat_model_only_passes_base_url_and_api_key_when_set(monkeypatch):
    captured = {}

    def fake_init_chat_model(**kwargs):
        captured.update(kwargs)
        return "fake-model"

    monkeypatch.setattr("langchain.chat_models.init_chat_model", fake_init_chat_model)

    build_chat_model(
        LLMProfile(provider="openai", model="local-model", base_url="http://x", api_key="key")
    )

    assert captured == {
        "model": "local-model",
        "model_provider": "openai",
        "base_url": "http://x",
        "api_key": "key",
    }


def test_build_chat_model_passes_max_tokens_when_set(monkeypatch):
    captured = {}

    def fake_init_chat_model(**kwargs):
        captured.update(kwargs)
        return "fake-model"

    monkeypatch.setattr("langchain.chat_models.init_chat_model", fake_init_chat_model)

    build_chat_model(LLMProfile(provider="openai", model="local-model", max_tokens=8192))

    assert captured == {"model": "local-model", "model_provider": "openai", "max_tokens": 8192}
