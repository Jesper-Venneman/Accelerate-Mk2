"""Shared pytest fixtures for Module H's test suite."""

from __future__ import annotations

import pytest

from kathrena.approval_gate.config import ApprovalGateConfig


@pytest.fixture
def approval_config(tmp_path) -> ApprovalGateConfig:
    """An ApprovalGateConfig rooted in a fresh temp directory, isolated per test."""
    return ApprovalGateConfig(
        vault_root=tmp_path / "vault",
        checkpoint_path=tmp_path / "checkpoints.sqlite",
    )
