"""Unit tests for UpdateCycleService KG populate enqueue."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.application.services.cycle.update_cycle_service import (
    UpdateCyclePayload,
    UpdateCycleService,
)
from pilot_space.infrastructure.database.models import CycleStatus

pytestmark = pytest.mark.asyncio

_CYCLE_ID = uuid4()
_ACTOR_ID = uuid4()


def _make_session() -> AsyncMock:
    return AsyncMock()


def _make_cycle_repo(cycle: MagicMock | None = None) -> AsyncMock:
    repo = AsyncMock()
    if cycle is None:
        cycle = MagicMock()
        cycle.id = _CYCLE_ID
        cycle.name = "Sprint 1"
        cycle.description = "Original desc"
        cycle.status = CycleStatus.DRAFT
        cycle.start_date = None
        cycle.end_date = None
        cycle.owned_by_id = None
        cycle.project_id = uuid4()
        cycle.workspace_id = uuid4()
    repo.get_by_id_with_relations = AsyncMock(return_value=cycle)
    repo.update = AsyncMock()
    repo.deactivate_project_cycles = AsyncMock()
    return repo


class TestKgPopulateEnqueue:
    async def test_enqueues_on_name_change(self) -> None:
        queue = AsyncMock()
        queue.enqueue = AsyncMock()
        repo = _make_cycle_repo()

        service = UpdateCycleService(session=_make_session(), cycle_repository=repo, queue=queue)
        await service.execute(
            UpdateCyclePayload(cycle_id=_CYCLE_ID, actor_id=_ACTOR_ID, name="Sprint 2")
        )

        queue.enqueue.assert_called_once()
        assert queue.enqueue.call_args[0][1]["entity_type"] == "cycle"

    async def test_enqueues_on_description_change(self) -> None:
        queue = AsyncMock()
        queue.enqueue = AsyncMock()
        repo = _make_cycle_repo()

        service = UpdateCycleService(session=_make_session(), cycle_repository=repo, queue=queue)
        await service.execute(
            UpdateCyclePayload(cycle_id=_CYCLE_ID, actor_id=_ACTOR_ID, description="Updated desc")
        )

        queue.enqueue.assert_called_once()

    async def test_enqueues_on_status_change(self) -> None:
        queue = AsyncMock()
        queue.enqueue = AsyncMock()
        repo = _make_cycle_repo()

        service = UpdateCycleService(session=_make_session(), cycle_repository=repo, queue=queue)
        await service.execute(
            UpdateCyclePayload(cycle_id=_CYCLE_ID, actor_id=_ACTOR_ID, status=CycleStatus.PLANNED)
        )

        queue.enqueue.assert_called_once()

    async def test_no_enqueue_on_date_only_change(self) -> None:
        from datetime import date

        queue = AsyncMock()
        queue.enqueue = AsyncMock()
        repo = _make_cycle_repo()

        service = UpdateCycleService(session=_make_session(), cycle_repository=repo, queue=queue)
        await service.execute(
            UpdateCyclePayload(
                cycle_id=_CYCLE_ID,
                actor_id=_ACTOR_ID,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 14),
            )
        )

        queue.enqueue.assert_not_called()

    async def test_no_enqueue_when_queue_is_none(self) -> None:
        repo = _make_cycle_repo()

        service = UpdateCycleService(session=_make_session(), cycle_repository=repo, queue=None)
        result = await service.execute(
            UpdateCyclePayload(cycle_id=_CYCLE_ID, actor_id=_ACTOR_ID, name="Sprint 2")
        )

        assert "name" in result.updated_fields

    async def test_enqueue_failure_does_not_break_update(self) -> None:
        queue = AsyncMock()
        queue.enqueue = AsyncMock(side_effect=RuntimeError("queue down"))
        repo = _make_cycle_repo()

        service = UpdateCycleService(session=_make_session(), cycle_repository=repo, queue=queue)
        result = await service.execute(
            UpdateCyclePayload(cycle_id=_CYCLE_ID, actor_id=_ACTOR_ID, name="Sprint 2")
        )

        assert "name" in result.updated_fields
