"""Xfail stubs for SKRG-02 — install plugin service tests.

Wave 0 TDD stubs. Each test is marked xfail(strict=False) so pytest exits 0
while the install-plugin service is pending implementation.
Stubs drive the green implementation in Phase 19 Plan 02.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


@pytest.mark.xfail(strict=False, reason="SKRG-02: not yet implemented")
async def test_install_creates_workspace_plugin_record() -> None:
    """SKRG-02: install_plugin creates a WorkspacePlugin row with correct metadata."""
    pytest.fail("not implemented")


@pytest.mark.xfail(strict=False, reason="SKRG-02: not yet implemented")
async def test_install_auto_wires_skill_content_immediately() -> None:
    """SKRG-02: install_plugin triggers skill materializer to write SKILL.md immediately."""
    pytest.fail("not implemented")


@pytest.mark.xfail(strict=False, reason="SKRG-02: not yet implemented")
async def test_update_plugin_overwrites_content_with_upstream() -> None:
    """SKRG-02: update_plugin replaces local content with upstream version."""
    pytest.fail("not implemented")
