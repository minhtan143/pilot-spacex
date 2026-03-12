"""Unit tests for CreateCycleService KG populate enqueue."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.application.services.cycle.create_cycle_service import (
    CreateCyclePayload,
    CreateCycleService,
)

pytestmark = pytest.mark.asyncio

_WORKSPACE_ID = uuid4()
_PROJECT_ID = uuid4()


def _make_session() -> AsyncMock:
    return AsyncMock()


def _make_cycle_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_next_sequence = AsyncMock(return_value=1)
    repo.deactivate_project_cycles = AsyncMock()
    cycle = MagicMock()
    cycle.id = uuid4()
    cycle.name = "Sprint 1"
    repo.create = AsyncMock(return_value=cycle)
    repo.get_by_id_with_relations = AsyncMock(return_value=cycle)
    return repo


class TestKgPopulateEnqueue:
    async def test_enqueues_kg_populate_on_create(self) -> None:
        session = _make_session()
        repo = _make_cycle_repo()
        queue = AsyncMock()
        queue.enqueue = AsyncMock()

        service = CreateCycleService(session=session, cycle_repository=repo, queue=queue)
        await service.execute(
            CreateCyclePayload(
                workspace_id=_WORKSPACE_ID,
                project_id=_PROJECT_ID,
                name="Sprint 1",
            )
        )

        queue.enqueue.assert_called_once()
        enqueued_payload = queue.enqueue.call_args[0][1]
        assert enqueued_payload["task_type"] == "kg_populate"
        assert enqueued_payload["entity_type"] == "cycle"
        assert enqueued_payload["workspace_id"] == str(_WORKSPACE_ID)
        assert enqueued_payload["project_id"] == str(_PROJECT_ID)

    async def test_no_enqueue_when_queue_is_none(self) -> None:
        session = _make_session()
        repo = _make_cycle_repo()

        service = CreateCycleService(session=session, cycle_repository=repo, queue=None)
        result = await service.execute(
            CreateCyclePayload(
                workspace_id=_WORKSPACE_ID,
                project_id=_PROJECT_ID,
                name="Sprint 1",
            )
        )

        assert result.created is True

    async def test_enqueue_failure_does_not_break_create(self) -> None:
        session = _make_session()
        repo = _make_cycle_repo()
        queue = AsyncMock()
        queue.enqueue = AsyncMock(side_effect=RuntimeError("queue down"))

        service = CreateCycleService(session=session, cycle_repository=repo, queue=queue)
        result = await service.execute(
            CreateCyclePayload(
                workspace_id=_WORKSPACE_ID,
                project_id=_PROJECT_ID,
                name="Sprint 1",
            )
        )

        assert result.created is True
