"""Unit tests for UpdateIssueService KG populate enqueue."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.application.services.issue.update_issue_service import (
    UpdateIssuePayload,
    UpdateIssueService,
)

pytestmark = pytest.mark.asyncio

_ISSUE_ID = uuid4()
_ACTOR_ID = uuid4()
_PROJECT_ID = uuid4()
_WORKSPACE_ID = uuid4()


def _make_session() -> AsyncMock:
    return AsyncMock()


def _make_issue() -> MagicMock:
    issue = MagicMock()
    issue.id = _ISSUE_ID
    issue.name = "Original name"
    issue.description = "Original description"
    issue.workspace_id = _WORKSPACE_ID
    issue.project_id = _PROJECT_ID
    issue.labels = []
    return issue


def _make_repos(issue: MagicMock | None = None) -> tuple[AsyncMock, AsyncMock, AsyncMock]:
    if issue is None:
        issue = _make_issue()
    issue_repo = AsyncMock()
    issue_repo.get_by_id_with_relations = AsyncMock(return_value=issue)
    issue_repo.update = AsyncMock(return_value=issue)

    activity_repo = AsyncMock()
    activity_repo.create = AsyncMock(side_effect=lambda a: a)

    label_repo = AsyncMock()
    return issue_repo, activity_repo, label_repo


class TestKgPopulateEnqueue:
    async def test_enqueues_on_name_change(self) -> None:
        queue = AsyncMock()
        queue.enqueue = AsyncMock()
        issue_repo, activity_repo, label_repo = _make_repos()

        service = UpdateIssueService(
            session=_make_session(),
            issue_repository=issue_repo,
            activity_repository=activity_repo,
            label_repository=label_repo,
            queue=queue,
        )
        await service.execute(
            UpdateIssuePayload(issue_id=_ISSUE_ID, actor_id=_ACTOR_ID, name="New name")
        )

        queue.enqueue.assert_called_once()
        payload = queue.enqueue.call_args[0][1]
        assert payload["task_type"] == "kg_populate"
        assert payload["entity_type"] == "issue"
        assert payload["entity_id"] == str(_ISSUE_ID)

    async def test_enqueues_on_description_change(self) -> None:
        queue = AsyncMock()
        queue.enqueue = AsyncMock()
        issue_repo, activity_repo, label_repo = _make_repos()

        service = UpdateIssueService(
            session=_make_session(),
            issue_repository=issue_repo,
            activity_repository=activity_repo,
            label_repository=label_repo,
            queue=queue,
        )
        await service.execute(
            UpdateIssuePayload(
                issue_id=_ISSUE_ID, actor_id=_ACTOR_ID, description="New description"
            )
        )

        queue.enqueue.assert_called_once()

    async def test_no_enqueue_on_priority_only_change(self) -> None:
        from pilot_space.infrastructure.database.models import IssuePriority

        queue = AsyncMock()
        queue.enqueue = AsyncMock()
        issue = _make_issue()
        issue.priority = IssuePriority.LOW
        issue_repo, activity_repo, label_repo = _make_repos(issue)

        service = UpdateIssueService(
            session=_make_session(),
            issue_repository=issue_repo,
            activity_repository=activity_repo,
            label_repository=label_repo,
            queue=queue,
        )
        await service.execute(
            UpdateIssuePayload(issue_id=_ISSUE_ID, actor_id=_ACTOR_ID, priority=IssuePriority.HIGH)
        )

        queue.enqueue.assert_not_called()

    async def test_no_enqueue_when_queue_is_none(self) -> None:
        issue_repo, activity_repo, label_repo = _make_repos()

        service = UpdateIssueService(
            session=_make_session(),
            issue_repository=issue_repo,
            activity_repository=activity_repo,
            label_repository=label_repo,
            queue=None,
        )
        result = await service.execute(
            UpdateIssuePayload(issue_id=_ISSUE_ID, actor_id=_ACTOR_ID, name="New name")
        )

        assert "name" in result.changed_fields

    async def test_enqueue_failure_does_not_break_update(self) -> None:
        queue = AsyncMock()
        queue.enqueue = AsyncMock(side_effect=RuntimeError("queue down"))
        issue_repo, activity_repo, label_repo = _make_repos()

        service = UpdateIssueService(
            session=_make_session(),
            issue_repository=issue_repo,
            activity_repository=activity_repo,
            label_repository=label_repo,
            queue=queue,
        )
        result = await service.execute(
            UpdateIssuePayload(issue_id=_ISSUE_ID, actor_id=_ACTOR_ID, name="New name")
        )

        assert "name" in result.changed_fields
