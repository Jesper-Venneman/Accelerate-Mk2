"""Manual, interactive test harness for Module H - `python -m kathrena.approval_gate <command>`.

Design spec: Architecture/Modules/H - Change Proposal and Approval Gate.md

Deliberately never touches `common.vault_root` (the real vault) - always operates on a small
throwaway sandbox vault under `./data/approval_gate_sandbox`, so you can safely try the
propose/review/resolve flow - including across two separate process runs, which is the actual
thing worth proving here: that a paused proposal really survives via the SqliteSaver checkpointer,
not just in-memory - without any risk to real notes.

Usage:
    python -m kathrena.approval_gate propose <note-name> "<new content>"
    python -m kathrena.approval_gate pending <thread-id>
    python -m kathrena.approval_gate resolve <thread-id> approve|reject|edit ["<edited content>"]

Run `propose` again for the same `<note-name>` after approving once to see a real edit diff
(against the content you just approved) rather than a "new file" diff.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from kathrena.approval_gate.config import ApprovalGateConfig
from kathrena.approval_gate.gate import get_pending_review, propose_change, resolve_change
from kathrena.approval_gate.models import ChangeProposal, Decision, Resolution

_SANDBOX_ROOT = Path("./data/approval_gate_sandbox")


def _sandbox_config() -> ApprovalGateConfig:
    """A config rooted in the throwaway sandbox vault, never the real one - see module docstring."""
    return ApprovalGateConfig(
        vault_root=_SANDBOX_ROOT / "vault",
        checkpoint_path=_SANDBOX_ROOT / "checkpoints.sqlite",
    )


def _print_diff(target_path: str, proposer: str, diff: str) -> None:
    print(f"--- diff for {target_path} (proposed by {proposer}) ---")
    print(diff or "(new file, no prior content)")


def _cmd_propose(args: argparse.Namespace, config: ApprovalGateConfig) -> None:
    config.vault_root.mkdir(parents=True, exist_ok=True)
    proposal = ChangeProposal(
        target_path=f"{args.note_name}.md",
        new_content=args.content,
        description=args.description,
        proposer="manual-demo",
    )
    review = propose_change(config, proposal)
    print(f"Proposal paused for review. thread_id = {review.thread_id}")
    _print_diff(review.target_path, review.proposer, review.diff)


def _cmd_pending(args: argparse.Namespace, config: ApprovalGateConfig) -> None:
    review = get_pending_review(config, args.thread_id)
    if review is None:
        print(f"No pending proposal for thread_id {args.thread_id!r}")
        return
    _print_diff(review.target_path, review.proposer, review.diff)


def _cmd_resolve(args: argparse.Namespace, config: ApprovalGateConfig) -> None:
    decision = Decision(args.decision)
    resolution = Resolution(
        decision=decision, edited_content=args.content if decision is Decision.EDIT else None
    )
    outcome = resolve_change(config, args.thread_id, resolution)
    if outcome.written_path is None:
        print(f"Not written (decision: {outcome.decision.value})")
        return
    print(f"Applied ({outcome.decision.value}) -> {outcome.written_path}")
    print("--- resulting file content ---")
    print(outcome.written_path.read_text(encoding="utf-8"))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    propose = subparsers.add_parser("propose", help="Stage a demo proposal and pause for review")
    propose.add_argument("note_name", help="Sandbox note name, without the .md extension")
    propose.add_argument("content", help="Proposed new file content")
    propose.add_argument("--description", default="Manual demo proposal")

    pending = subparsers.add_parser("pending", help="Show a paused proposal's diff again")
    pending.add_argument("thread_id")

    resolve = subparsers.add_parser("resolve", help="Resolve a paused proposal")
    resolve.add_argument("thread_id")
    resolve.add_argument("decision", choices=[d.value for d in Decision])
    resolve.add_argument("content", nargs="?", default=None, help="Required when decision is edit")

    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _build_parser().parse_args()
    config = _sandbox_config()
    handlers = {"propose": _cmd_propose, "pending": _cmd_pending, "resolve": _cmd_resolve}
    handlers[args.command](args, config)


if __name__ == "__main__":
    main()
