"""Shared configuration for the Kathrena/Accelerate Mk2 pipeline.

Design spec: Architecture/Architecture Overview.md#Runtime architecture

Centralizes the vault paths and model settings every module needs, so no path or
hostname gets hardcoded more than once. Every value has a sensible default so the
pipeline runs against a fresh vault checkout without configuration, but each can
be overridden in `data/settings.yaml` (Decisions Log Round 25).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from kathrena.settings import setting_path, setting_str


@dataclass(frozen=True)
class PipelineConfig:
    """Filesystem layout and model settings for the voice-log pipeline (Modules A-E)."""

    # Shared with every other vault-reading module via the "common" settings section, not
    # "pipeline" - set once, every module picks it up.
    vault_root: Path = field(default_factory=lambda: setting_path("common", "vault_root", "."))
    project_dirs: tuple[str, ...] = ("01 - Projects", "02 - Side-Projects")
    unprocessed_dir_name: str = "91 - Resources/81 - logs/Unprocessed logs"
    processed_dir_name: str = "91 - Resources/81 - logs/Processed logs"
    unsorted_logs_dir_name: str = "02 - Side-Projects/Logs/Unsorted Logs"
    vocal_journal_dir_name: str = "02 - Side-Projects/Logs/Vocal Journal"
    edit_to_log_phrase: str = "edit to log"

    whisper_model_size: str = field(
        default_factory=lambda: setting_str("pipeline", "whisper_model_size", "medium")
    )
    whisper_device: str = field(
        default_factory=lambda: setting_str("pipeline", "whisper_device", "cuda")
    )

    # Which named data/settings.yaml llm_profiles entry this role's chat model is built from
    # (kathrena.llm.resolve_profile/build_chat_model) - independent from every other role, so
    # Module E can stay on "local" while e.g. Module G switches to "cloud" (Decisions Log Round 27).
    llm_profile: str = field(default_factory=lambda: setting_str("pipeline", "llm_profile", "local"))

    def resolve(self, relative: str) -> Path:
        """Resolve a vault-relative path against `vault_root`."""
        return self.vault_root / relative

    @property
    def unprocessed_dir(self) -> Path:
        return self.resolve(self.unprocessed_dir_name)

    @property
    def processed_dir(self) -> Path:
        return self.resolve(self.processed_dir_name)

    @property
    def unsorted_logs_dir(self) -> Path:
        return self.resolve(self.unsorted_logs_dir_name)

    @property
    def vocal_journal_dir(self) -> Path:
        return self.resolve(self.vocal_journal_dir_name)
