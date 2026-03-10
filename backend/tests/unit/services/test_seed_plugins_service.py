"""Xfail stubs for SKRG-05 — seed plugins service tests.

Wave 0 TDD stubs. Each test is marked xfail(strict=False) so pytest exits 0
while the seed-plugins service is pending implementation.
Stubs drive the green implementation in Phase 19 Plan 03.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


@pytest.mark.xfail(strict=False, reason="SKRG-05: not yet implemented")
async def test_seed_workspace_installs_default_plugins() -> None:
    """SKRG-05: seed_workspace_plugins installs the default plugin set for a new workspace."""
    pytest.fail("not implemented")


@pytest.mark.xfail(strict=False, reason="SKRG-05: not yet implemented")
async def test_seed_workspace_skips_when_github_token_missing() -> None:
    """SKRG-05: seed_workspace_plugins gracefully skips when GITHUB_TOKEN is not configured."""
    pytest.fail("not implemented")


@pytest.mark.xfail(strict=False, reason="SKRG-05: not yet implemented")
async def test_seed_failure_is_nonfatal() -> None:
    """SKRG-05: seed failure does not propagate — workspace creation succeeds regardless."""
    pytest.fail("not implemented")
