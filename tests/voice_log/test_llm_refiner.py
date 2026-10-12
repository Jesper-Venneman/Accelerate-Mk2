"""Tests for kathrena.voice_log.refinement.llm_refiner - LangChainRefiner's hot-swap-by-rebuild
behavior (Decisions Log Round 28)."""

from __future__ import annotations

from kathrena.config import PipelineConfig
from kathrena.voice_log.refinement.llm_refiner import LangChainRefiner


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModel:
    def __init__(self, profile: str) -> None:
        self.profile = profile

    def invoke(self, prompt: str) -> _FakeResponse:
        return _FakeResponse(f"refined by {self.profile}")


def _patch_llm(monkeypatch, build_calls: list[str]) -> None:
    import kathrena.llm as kathrena_llm

    monkeypatch.setattr(kathrena_llm, "resolve_profile", lambda name: name)

    def fake_build_chat_model(profile):
        build_calls.append(profile)
        return _FakeModel(profile)

    monkeypatch.setattr(kathrena_llm, "build_chat_model", fake_build_chat_model)


def test_rebuilds_only_once_while_the_profile_stays_the_same(tmp_path, monkeypatch):
    build_calls: list[str] = []
    _patch_llm(monkeypatch, build_calls)

    refiner = LangChainRefiner(PipelineConfig(vault_root=tmp_path))
    refiner.refine("hello")
    refiner.refine("hello again")

    assert build_calls == ["local"]


def test_rebuilds_when_the_profile_changes(tmp_path, monkeypatch):
    from kathrena.settings import get_store

    build_calls: list[str] = []
    _patch_llm(monkeypatch, build_calls)

    refiner = LangChainRefiner(PipelineConfig(vault_root=tmp_path))
    refiner.refine("hello")

    get_store().set_value("pipeline", "llm_profile", "cloud")
    result = refiner.refine("hello again")

    assert build_calls == ["local", "cloud"]
    assert result == "refined by cloud"
