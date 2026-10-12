"""Shared pytest fixtures for Module I's test suite."""

from __future__ import annotations

import pytest

from kathrena.project_management.config import ProjectManagementConfig


@pytest.fixture
def pm_config(tmp_path) -> ProjectManagementConfig:
    """A ProjectManagementConfig rooted in a fresh temp vault, isolated per test."""
    return ProjectManagementConfig(vault_root=tmp_path / "vault")
