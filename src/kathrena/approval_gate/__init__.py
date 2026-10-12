"""Module H: Change Proposal and Approval Gate.

Design spec: Architecture/Modules/H - Change Proposal and Approval Gate.md

The safety gate: every proposed vault write pauses via LangGraph `interrupt()`
and only commits after explicit approval through `kathrena.chat_interface`
(Module K), resumed with `Command(resume=...)`.

Public API: `propose_change` stages a `ChangeProposal` and pauses for review;
`get_pending_review` looks up a paused proposal without resolving it;
`resolve_change` resumes it with a `Resolution` (approve/reject/edit).
"""

from __future__ import annotations

from kathrena.approval_gate.chainlit_actions import proposal_actions
from kathrena.approval_gate.config import ApprovalGateConfig
from kathrena.approval_gate.gate import get_pending_review, propose_change, resolve_change
from kathrena.approval_gate.models import (
    ChangeProposal,
    Decision,
    Outcome,
    PendingReview,
    Resolution,
)

__all__ = [
    "ApprovalGateConfig",
    "ChangeProposal",
    "Decision",
    "Outcome",
    "PendingReview",
    "Resolution",
    "get_pending_review",
    "propose_change",
    "proposal_actions",
    "resolve_change",
]

