"""Tests for Module H's LangGraph-based propose/pause/resolve flow (kathrena.approval_gate.gate)."""

from __future__ import annotations

import pytest

from kathrena.approval_gate.gate import get_pending_review, propose_change, resolve_change
from kathrena.approval_gate.models import ChangeProposal, Decision, Resolution
from kathrena.approval_gate.vault_writer import UnsafeTargetPathError


def _proposal(target_path="note.md", new_content="new content", description="test change"):
    return ChangeProposal(
        target_path=target_path, new_content=new_content, description=description, proposer="test"
    )


def test_propose_pauses_and_surfaces_a_diff_for_a_new_file(approval_config):
    review = propose_change(approval_config, _proposal(new_content="new content"))

    assert review.target_path == "note.md"
    assert "+new content" in review.diff
    assert not (approval_config.vault_root / "note.md").exists()  # nothing written yet


def test_propose_diff_against_an_existing_file(approval_config):
    approval_config.vault_root.mkdir(parents=True)
    (approval_config.vault_root / "note.md").write_text("old content", encoding="utf-8")

    review = propose_change(approval_config, _proposal(new_content="new content"))

    assert "-old content" in review.diff
    assert "+new content" in review.diff


def test_propose_rejects_a_path_that_escapes_the_vault_root(approval_config):
    with pytest.raises(UnsafeTargetPathError):
        propose_change(approval_config, _proposal(target_path="../outside.md"))


def test_approve_writes_the_proposed_content(approval_config):
    review = propose_change(approval_config, _proposal(new_content="approved content"))

    outcome = resolve_change(approval_config, review.thread_id, Resolution(Decision.APPROVE))

    assert outcome.decision is Decision.APPROVE
    assert outcome.written_path == approval_config.vault_root / "note.md"
    assert outcome.written_path.read_text(encoding="utf-8") == "approved content"


def test_reject_writes_nothing(approval_config):
    review = propose_change(approval_config, _proposal())

    outcome = resolve_change(approval_config, review.thread_id, Resolution(Decision.REJECT))

    assert outcome.decision is Decision.REJECT
    assert outcome.written_path is None
    assert not (approval_config.vault_root / "note.md").exists()


def test_edit_writes_the_reviewer_edited_content_instead_of_the_proposal(approval_config):
    review = propose_change(approval_config, _proposal(new_content="original proposal"))

    outcome = resolve_change(
        approval_config,
        review.thread_id,
        Resolution(Decision.EDIT, edited_content="reviewer edited this"),
    )

    assert outcome.decision is Decision.EDIT
    assert outcome.written_path.read_text(encoding="utf-8") == "reviewer edited this"


def test_pending_review_is_visible_before_resolving_and_gone_after(approval_config):
    review = propose_change(approval_config, _proposal())

    # Each helper opens and closes its own checkpoint-DB connection, so this also proves a
    # paused proposal can be checked/resolved from a separate call (or process) - not just
    # relying on in-memory state from propose_change.
    assert get_pending_review(approval_config, review.thread_id) is not None

    resolve_change(approval_config, review.thread_id, Resolution(Decision.APPROVE))

    assert get_pending_review(approval_config, review.thread_id) is None


def test_resolve_raises_for_an_unknown_thread_id(approval_config):
    with pytest.raises(ValueError):
        resolve_change(approval_config, "no-such-thread", Resolution(Decision.APPROVE))


def test_resolve_raises_if_already_resolved(approval_config):
    review = propose_change(approval_config, _proposal())
    resolve_change(approval_config, review.thread_id, Resolution(Decision.APPROVE))

    with pytest.raises(ValueError):
        resolve_change(approval_config, review.thread_id, Resolution(Decision.APPROVE))


def test_edit_resolution_without_content_is_rejected_up_front():
    with pytest.raises(ValueError):
        Resolution(Decision.EDIT)
