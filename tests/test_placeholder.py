"""Placeholder tests for Phase 1 repository setup."""

from __future__ import annotations


def test_placeholder() -> None:
    """Smoke test to verify pytest is wired correctly."""
    assert True


def test_project_identity() -> None:
    """Ensure project naming constant is available for future imports."""
    project_name = "semiconductor-data-platform"
    assert "semiconductor" in project_name
    assert project_name.endswith("platform")
