"""Xfail stubs for SKRG-01 and SKRG-04 — workspace plugins router tests.

Wave 0 TDD stubs. Each test is marked xfail(strict=False) so pytest exits 0
while the workspace-plugins router is pending implementation.
Stubs drive the green implementation in Phase 19 Plans 02-03.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


@pytest.mark.xfail(strict=False, reason="SKRG-01: not yet implemented")
async def test_browse_repo_returns_skill_list() -> None:
    """SKRG-01: GET /workspaces/{id}/plugins/browse returns list of available skills from repo."""
    pytest.fail("not implemented")


@pytest.mark.xfail(strict=False, reason="SKRG-01: not yet implemented")
async def test_browse_repo_raises_on_github_unreachable() -> None:
    """SKRG-01: GET /workspaces/{id}/plugins/browse returns error when GitHub is unreachable."""
    pytest.fail("not implemented")


@pytest.mark.xfail(strict=False, reason="SKRG-04: not yet implemented")
async def test_update_check_returns_has_update_true_when_sha_differs() -> None:
    """SKRG-04: GET /workspaces/{id}/plugins/{pluginId}/check-update returns has_update=true when SHA differs."""
    pytest.fail("not implemented")


@pytest.mark.xfail(strict=False, reason="SKRG-04: not yet implemented")
async def test_update_check_caches_result_five_minutes() -> None:
    """SKRG-04: update check result is cached for 5 minutes to avoid excessive GitHub API calls."""
    pytest.fail("not implemented")
