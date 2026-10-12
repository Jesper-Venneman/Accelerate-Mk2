"""Configuration for Module H (change proposal and approval gate).

Design spec: Architecture/Modules/H - Change Proposal and Approval Gate.md

Independent from `kathrena.rag_index.config.RagIndexConfig` and `kathrena.config.PipelineConfig`
- all three only agree on the shared "common" settings section, nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from kathrena.settings import setting_path


@dataclass(frozen=True)
class ApprovalGateConfig:
    """Vault location and the checkpoint DB that persists paused proposals across restarts."""

    vault_root: Path = field(default_factory=lambda: setting_path("common", "vault_root", "."))

    # Local runtime data (Architecture/Architecture Overview.md#Runtime architecture) - already
    # covered by .gitignore. Separate DB file from Module F's, since they checkpoint unrelated
    # LangGraph runs.
    checkpoint_path: Path = field(
        default_factory=lambda: setting_path(
            "approval_gate", "checkpoint_path", "./data/approval_gate_checkpoints.sqlite"
        )
    )
