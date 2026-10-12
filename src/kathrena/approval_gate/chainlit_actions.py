"""Chainlit UI actions for resolving a staged `ChangeProposal`.

Design spec: Architecture/Modules/H - Change Proposal and Approval Gate.md

Lives alongside the rest of Module H so the Approve/Edit/Reject affordance travels with the
gate it operates on; `kathrena.chat_interface` (Module K) wires the resulting actions to
`resolve_change` via its `resolve_proposal` action callback.
"""

from __future__ import annotations

import chainlit as cl

from kathrena.approval_gate.models import Decision


def proposal_actions(thread_id: str) -> list[cl.Action]:
    return [
        cl.Action(
            name="resolve_proposal",
            label="✅ Approve",
            payload={"thread_id": thread_id, "decision": Decision.APPROVE.value},
        ),
        cl.Action(
            name="resolve_proposal",
            label="✏️ Edit",
            payload={"thread_id": thread_id, "decision": Decision.EDIT.value},
        ),
        cl.Action(
            name="resolve_proposal",
            label="❌ Reject",
            payload={"thread_id": thread_id, "decision": Decision.REJECT.value},
        ),
    ]
