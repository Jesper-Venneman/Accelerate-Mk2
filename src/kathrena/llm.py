"""Centralized LLM client construction: one place that turns a named profile into a chat model.

Design spec: Architecture/Architecture Overview.md#Runtime architecture
Decision: Architecture/Decisions Log.md, Round 27.

Every LLM-using module (`voice_log.refinement`, `agent_core`, `memory`) used to duplicate the
same `init_chat_model(...)` call, each hardcoding `model_provider="openai"` - meaning a cloud
Anthropic profile could never actually have worked (Claude needs `model_provider="anthropic"`).
Centralizing here fixes that and gives each role (Module E/G/J) an independent, named profile
switch (`local` vs. `cloud`, or any other name added to `data/settings.yaml`'s `llm_profiles`
section), resolved once via `resolve_profile`/`build_chat_model` rather than three copies of the
same logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kathrena.settings.store import get_store

# Seeded into `llm_profiles` the first time any profile is resolved, so both show up ready to
# edit rather than only whichever one happened to be requested first.
_DEFAULT_PROFILES: dict[str, dict[str, str | int | None]] = {
    "local": {
        "provider": "openai",
        "model": "local-model",
        "base_url": "http://127.0.0.1:5000/v1",
        "api_key": "not-needed",
        "max_tokens": None,
    },
    "cloud": {
        "provider": "openai",
        "model": None,
        "base_url": None,
        "api_key": None,
        "max_tokens": 8192,
    },
}


@dataclass(frozen=True)
class LLMProfile:
    """One named LLM connection - a local TextGen endpoint, a cloud provider, etc."""

    provider: str
    model: str | None
    base_url: str | None = None
    api_key: str | None = None
    max_tokens: int | None = None


class LLMProfileError(RuntimeError):
    """Raised when a named profile doesn't exist, or exists but hasn't been filled in yet."""


def seed_default_profiles() -> None:
    """Seed both the `local` and `cloud` starter profiles into `llm_profiles`, without resolving
    or validating either. Called both by `resolve_profile` and by
    `kathrena.settings.bootstrap.ensure_configured`, so the endpoints are visible in the file to
    edit even on the very first run - before the app ever gets far enough to resolve one itself.
    """
    store = get_store()
    existing = store.raw_section("llm_profiles")
    for profile_name, defaults in _DEFAULT_PROFILES.items():
        if profile_name not in existing:
            store.value("llm_profiles", profile_name, defaults)
            continue
        current = dict(existing[profile_name])
        missing = {key: value for key, value in defaults.items() if key not in current}
        if missing:
            current.update(missing)
            store.set_value("llm_profiles", profile_name, current)


def resolve_profile(name: str) -> LLMProfile:
    """Look up a named profile from `data/settings.yaml`'s `llm_profiles` section."""
    seed_default_profiles()
    profiles = get_store().raw_section("llm_profiles")
    if name not in profiles:
        raise LLMProfileError(
            f"No {name!r} profile in data/settings.yaml's llm_profiles section "
            f"(have: {sorted(profiles)!r})."
        )
    data = profiles[name]
    profile = LLMProfile(
        provider=data["provider"],
        model=data.get("model"),
        base_url=data.get("base_url"),
        api_key=data.get("api_key"),
        max_tokens=data.get("max_tokens"),
    )
    missing = [field for field in ("model", "base_url") if getattr(profile, field) is None]
    if missing:
        raise LLMProfileError(
            f"data/settings.yaml's llm_profiles.{name}.{'/'.join(missing)} still unset - fill "
            "it in, then retry."
        )
    return profile


def build_chat_model(profile: LLMProfile) -> Any:
    """Construct a LangChain chat model for `profile` - the one place `init_chat_model` is called.
    """
    # Imported lazily so importing this module doesn't require langchain-openai/-anthropic unless
    # a chat model is actually constructed.
    from langchain.chat_models import init_chat_model

    kwargs: dict[str, Any] = {"model": profile.model, "model_provider": profile.provider}
    if profile.base_url is not None:
        kwargs["base_url"] = profile.base_url
    if profile.api_key is not None:
        kwargs["api_key"] = profile.api_key
    if profile.max_tokens is not None:
        kwargs["max_tokens"] = profile.max_tokens
    return init_chat_model(**kwargs)
