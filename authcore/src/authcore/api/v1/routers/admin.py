"""FastAPI router: /api/v1/admin/* — admin-only endpoints."""

from __future__ import annotations

import uuid

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from authcore.api.dependencies.auth import CurrentUser, require_admin
from authcore.api.v1.schemas.admin import (
    AuditLogResponse,
    ChangeRoleRequest,
    ChangeRoleResponse,
    ListAuditLogsResponse,
)
from authcore.application.services.admin.change_role_service import (
    ChangeRolePayload,
    ChangeRoleService,
)
from authcore.application.services.admin.list_audit_logs_service import (
    ListAuditLogsPayload,
    ListAuditLogsService,
)
from authcore.container.container import Container
from authcore.infrastructure.database.repositories.audit_log_repository import AuditLogRepository
from authcore.infrastructure.database.repositories.user_repository import UserRepository

router = APIRouter(prefix="/admin", tags=["admin"])


@router.put("/users/{user_id}/role", response_model=ChangeRoleResponse)
@inject
async def change_user_role(
    user_id: uuid.UUID,
    body: ChangeRoleRequest,
    current_user: CurrentUser = Depends(require_admin),
    session_factory: async_sessionmaker[AsyncSession] = Depends(  # type: ignore[type-arg]
        Provide[Container.infra.session_factory]  # type: ignore[misc]
    ),
) -> ChangeRoleResponse:
    async with session_factory() as session:
        async with session.begin():
            svc = ChangeRoleService(
                user_repo=UserRepository(session),
                audit_repo=AuditLogRepository(session),
            )
            result = await svc.execute(
                ChangeRolePayload(
                    admin_user_id=current_user.user_id,
                    target_user_id=user_id,
                    new_role=body.new_role,
                )
            )
    return ChangeRoleResponse(user_id=result.user_id, new_role=result.new_role)


@router.get("/users/{user_id}/audit-logs", response_model=ListAuditLogsResponse)
@inject
async def list_audit_logs(
    user_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_admin),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session_factory: async_sessionmaker[AsyncSession] = Depends(  # type: ignore[type-arg]
        Provide[Container.infra.session_factory]  # type: ignore[misc]
    ),
) -> ListAuditLogsResponse:
    async with session_factory() as session:
        async with session.begin():
            svc = ListAuditLogsService(
                user_repo=UserRepository(session),
                audit_repo=AuditLogRepository(session),
            )
            result = await svc.execute(
                ListAuditLogsPayload(
                    admin_user_id=current_user.user_id,
                    target_user_id=user_id,
                    limit=limit,
                    offset=offset,
                )
            )
    return ListAuditLogsResponse(
        logs=[
            AuditLogResponse(
                id=log.id,
                action=log.action,
                created_at=log.created_at,
                user_id=log.user_id,
                metadata=log.metadata,
                ip_address=log.ip_address,
            )
            for log in result.logs
        ],
        total_returned=result.total_returned,
    )
