"""Cleans up and summarizes a raw transcript via the hybrid LLM backend.

Design spec: Architecture/Modules/E - Refinement and Summarization Module.md
LLM backend choice: Architecture/Decisions Log.md, Round 10.
"""

from __future__ import annotations

from typing import Any, Protocol

from kathrena.config import PipelineConfig

_REFINE_PROMPT = (
    "Rewrite and summarize the following voice log transcript to be cleaner and more formal, "
    "while preserving its original meaning and every notable detail. Be purely informative and "
    "do not refer to the speaker in the third person. End with a short bullet list of the most "
    "important points.\n\nTranscript:\n{transcript}"
)


class Refiner(Protocol):
    """Swappable interface so the LLM backend can change without touching callers (Module D)."""

    def refine(self, transcript: str) -> str: ...


class LangChainRefiner:
    """Default `Refiner`: a hybrid LLM behind `kathrena.llm.build_chat_model`.

    Local by default via oobabooga TextGen's OpenAI-compatible endpoint; set `PipelineConfig`'s
    `llm_profile` to a different `data/settings.yaml` llm_profiles entry to use a cloud provider
    instead - same interface either way (Decisions Log Round 27).

    Hot-swappable without a restart (Decisions Log Round 28): rebuilds its chat model only when
    `pipeline.llm_profile` has actually changed since last checked, re-read fresh on every
    `refine()` call rather than trusting the frozen `config` snapshot.
    """

    def __init__(self, config: PipelineConfig) -> None:
        self._config = config
        self._profile_name: str | None = None
        self._model: Any = None
        self._rebuild_if_needed()

    def _rebuild_if_needed(self) -> None:
        from kathrena.llm import build_chat_model, resolve_profile
        from kathrena.settings import setting_str

        current_profile = setting_str("pipeline", "llm_profile", "local")
        if current_profile == self._profile_name:
            return
        self._model = build_chat_model(resolve_profile(current_profile))
        self._profile_name = current_profile

    def refine(self, transcript: str) -> str:
        self._rebuild_if_needed()
        response = self._model.invoke(_REFINE_PROMPT.format(transcript=transcript))
        return response.text.strip()
