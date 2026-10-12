"""Data types for a proposed vault change and the reviewer's decision on it.

Design spec: Architecture/Modules/H - Change Proposal and Approval Gate.md
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


@dataclass(frozen=True)
class ChangeProposal:
    """A single proposed vault write, staged before it ever touches disk.

    `target_path` is vault-relative (e.g. "Projects/Foo/Foo.md") - resolved and bounds-checked
    against the vault root before any write happens (see `vault_writer.resolve_target_path`).
    """

    target_path: str
    new_content: str
    description: str
    proposer: str  # e.g. "G" or "I4" - which module/sub-agent raised this, for audit/logging


class Decision(StrEnum):
    """A reviewer's resolution for a paused `ChangeProposal`."""

    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"  # approve, but with reviewer-edited content


@dataclass(frozen=True)
class Resolution:
    """The reviewer's answer, passed back in via `Command(resume=...)`."""

    decision: Decision
    edited_content: str | None = None  # required, and only used, when decision is EDIT

    def __post_init__(self) -> None:
        if self.decision is Decision.EDIT and not self.edited_content:
            raise ValueError("Decision.EDIT requires a non-empty edited_content")


@dataclass(frozen=True)
class PendingReview:
    """A paused proposal's reviewable details - what a reviewer (human or Module K) sees."""

    thread_id: str
    target_path: str
    description: str
    proposer: str
    diff: str


@dataclass(frozen=True)
class Outcome:
    """What actually happened after a proposal was resolved."""

    decision: Decision
    written_path: Path | None  # set only when the decision resulted in a disk write
