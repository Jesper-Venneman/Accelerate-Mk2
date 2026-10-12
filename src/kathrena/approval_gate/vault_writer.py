"""Applies an approved ChangeProposal's content to disk.

Design spec: Architecture/Modules/H - Change Proposal and Approval Gate.md

Isolated from the LangGraph plumbing in `gate.py` so the one genuinely dangerous operation in
this module - writing into the vault - is a single small function, directly unit-testable
without spinning up a graph.
"""

from __future__ import annotations

from pathlib import Path


class UnsafeTargetPathError(ValueError):
    """Raised when a proposal's target_path would resolve outside the vault root."""


def resolve_target_path(vault_root: Path, target_path: str) -> Path:
    """Resolve `target_path` against `vault_root`, rejecting anything that escapes it.

    Proposals come from Kathrena/sub-agents (Modules G/I), not typed by hand, so `target_path` is
    treated as untrusted input - guards against a proposal (buggy or malicious) writing outside
    the vault via `..` segments or an absolute/other-drive path.
    """
    vault_root = vault_root.resolve()
    candidate = (vault_root / target_path).resolve()
    if candidate != vault_root and vault_root not in candidate.parents:
        raise UnsafeTargetPathError(f"{target_path!r} resolves outside the vault root")
    return candidate


def write_approved_content(vault_root: Path, target_path: str, content: str) -> Path:
    """Write `content` to `target_path` inside `vault_root`, creating parent folders as needed."""
    resolved = resolve_target_path(vault_root, target_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return resolved
