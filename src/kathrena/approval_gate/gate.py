"""LangGraph plumbing for Module H: pause a proposed vault write, resume it on review.

Design spec: Architecture/Modules/H - Change Proposal and Approval Gate.md

Two-node graph per proposal:
1. `stage_and_await` validates and reads the current file (if any), builds a diff for review,
   then calls `interrupt()` - pausing the graph and persisting it via the `SqliteSaver`
   checkpointer, so the proposal survives a restart and can be resolved whenever the user gets
   to it, hours or days later.
2. `apply_decision` runs only after a resume: writes the approved (or reviewer-edited) content,
   or nothing at all if rejected.

Design constraint from the spec: everything before `interrupt()` re-runs on every resume attempt,
so `stage_and_await` must stay side-effect-free (it only validates a path and reads from disk) -
the actual write happens in `apply_decision`, which only runs once, after a decision exists.
"""

from __future__ import annotations

import difflib
import logging
import uuid
from pathlib import Path
from typing import TypedDict

from kathrena.approval_gate.config import ApprovalGateConfig
from kathrena.approval_gate.models import (
    ChangeProposal,
    Decision,
    Outcome,
    PendingReview,
    Resolution,
)
from kathrena.approval_gate.vault_writer import resolve_target_path, write_approved_content

logger = logging.getLogger(__name__)


class _ProposalState(TypedDict):
    target_path: str
    new_content: str
    description: str
    proposer: str
    decision: str | None
    edited_content: str | None
    written_path: str | None


def _unified_diff(old_content: str, new_content: str, target_path: str) -> str:
    """Human-readable diff for review - recomputed fresh each time, never persisted as state."""
    return "".join(
        difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{target_path}",
            tofile=f"b/{target_path}",
        )
    )


def build_approval_graph(config: ApprovalGateConfig):
    """Build the (uncompiled) two-node graph. Compile with a checkpointer to pause/resume."""
    # Imported lazily so importing this module doesn't require langgraph unless used.
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import interrupt

    def stage_and_await(state: _ProposalState) -> _ProposalState:
        # Raises UnsafeTargetPathError up front for an out-of-bounds path, before ever pausing.
        target = resolve_target_path(config.vault_root, state["target_path"])
        old_content = target.read_text(encoding="utf-8") if target.exists() else ""
        diff = _unified_diff(old_content, state["new_content"], state["target_path"])
        resume_value = interrupt(
            {
                "type": "change_proposal",
                "target_path": state["target_path"],
                "description": state["description"],
                "proposer": state["proposer"],
                "diff": diff,
            }
        )
        return {
            **state,
            "decision": resume_value["decision"],
            "edited_content": resume_value.get("edited_content"),
        }

    def apply_decision(state: _ProposalState) -> _ProposalState:
        decision = Decision(state["decision"])
        if decision is Decision.REJECT:
            logger.info("Proposal for %s rejected, nothing written", state["target_path"])
            return {**state, "written_path": None}
        content = state["edited_content"] if decision is Decision.EDIT else state["new_content"]
        written = write_approved_content(config.vault_root, state["target_path"], content)
        logger.info(
            "Proposal for %s %s -> wrote %s", state["target_path"], decision.value, written
        )
        return {**state, "written_path": str(written)}

    graph = StateGraph(_ProposalState)
    graph.add_node("stage_and_await", stage_and_await)
    graph.add_node("apply_decision", apply_decision)
    graph.add_edge(START, "stage_and_await")
    graph.add_edge("stage_and_await", "apply_decision")
    graph.add_edge("apply_decision", END)
    return graph


def _sqlite_checkpointer(config: ApprovalGateConfig):
    # Imported lazily so importing this module doesn't require langgraph-checkpoint-sqlite
    # unless used.
    from langgraph.checkpoint.sqlite import SqliteSaver

    config.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver.from_conn_string(str(config.checkpoint_path))


def _run_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _to_pending_review(thread_id: str, interrupt_value: dict) -> PendingReview:
    return PendingReview(
        thread_id=thread_id,
        target_path=interrupt_value["target_path"],
        description=interrupt_value["description"],
        proposer=interrupt_value["proposer"],
        diff=interrupt_value["diff"],
    )


def propose_change(
    config: ApprovalGateConfig, proposal: ChangeProposal, thread_id: str | None = None
) -> PendingReview:
    """Stage `proposal` and pause for review. Returns the diff/description to show a reviewer.

    Each call opens its own connection to the checkpoint DB and closes it before returning - no
    in-process state is kept, so the returned `thread_id` can be resolved from a totally separate
    process (or after a restart) via `resolve_change`.
    """
    thread_id = thread_id or str(uuid.uuid4())
    with _sqlite_checkpointer(config) as checkpointer:
        graph = build_approval_graph(config).compile(checkpointer=checkpointer)
        # version="v2" for a typed GraphOutput(value=..., interrupts=...) instead of the legacy
        # `result["__interrupt__"]` dict-key access (deprecated in this langgraph version).
        result = graph.invoke(
            {
                "target_path": proposal.target_path,
                "new_content": proposal.new_content,
                "description": proposal.description,
                "proposer": proposal.proposer,
                "decision": None,
                "edited_content": None,
                "written_path": None,
            },
            config=_run_config(thread_id),
            version="v2",
        )
    if not result.interrupts:
        raise RuntimeError(f"Proposal for {proposal.target_path!r} did not pause for review")
    return _to_pending_review(thread_id, result.interrupts[0].value)


def get_pending_review(config: ApprovalGateConfig, thread_id: str) -> PendingReview | None:
    """Look up a paused proposal for `thread_id` without resolving it - e.g. after a restart."""
    with _sqlite_checkpointer(config) as checkpointer:
        graph = build_approval_graph(config).compile(checkpointer=checkpointer)
        snapshot = graph.get_state(_run_config(thread_id))
    if not snapshot.interrupts:
        return None
    return _to_pending_review(thread_id, snapshot.interrupts[0].value)


def resolve_change(config: ApprovalGateConfig, thread_id: str, resolution: Resolution) -> Outcome:
    """Resume the paused proposal for `thread_id` with the reviewer's decision."""
    from langgraph.types import Command

    resume_value: dict[str, str] = {"decision": resolution.decision.value}
    if resolution.decision is Decision.EDIT:
        resume_value["edited_content"] = resolution.edited_content

    with _sqlite_checkpointer(config) as checkpointer:
        graph = build_approval_graph(config).compile(checkpointer=checkpointer)
        run_config = _run_config(thread_id)
        if not graph.get_state(run_config).interrupts:
            raise ValueError(f"No pending proposal for thread_id {thread_id!r}")
        result = graph.invoke(Command(resume=resume_value), config=run_config, version="v2")

    final_state = result.value
    written_path = final_state["written_path"]
    return Outcome(
        decision=Decision(final_state["decision"]),
        written_path=Path(written_path) if written_path else None,
    )
