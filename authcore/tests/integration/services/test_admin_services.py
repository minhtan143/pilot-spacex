"""Integration tests for admin services: ChangeRoleService, ListAuditLogsService."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from authcore.application.services.admin.change_role_service import (
    ChangeRolePayload,
    ChangeRoleService,
)
from authcore.application.services.admin.list_audit_logs_service import (
    ListAuditLogsPayload,
    ListAuditLogsService,
)
from authcore.domain.exceptions import AuthForbiddenError, InvalidRoleError, UserNotFoundError
from authcore.domain.models.user import UserEntity
from authcore.infrastructure.database.repositories.audit_log_repository import AuditLogRepository
from authcore.infrastructure.database.repositories.user_repository import UserRepository


async def _make_user(
    session: AsyncSession, email: str, role: str = "member"
) -> UserEntity:
    import bcrypt

    repo = UserRepository(session)
    entity = UserEntity(
        id=uuid.uuid4(),
        email=email,
        hashed_password=bcrypt.hashpw(b"Pass123!", bcrypt.gensalt(rounds=4)).decode(),
        role=role,
        is_verified=True,
        is_locked=False,
        failed_attempts=0,
        lockout_until=None,
        created_at=datetime.now(tz=UTC),
    )
    return await repo.save_entity(entity)


class TestChangeRoleService:
    async def test_admin_can_change_role(self, db_session: AsyncSession) -> None:
        admin = await _make_user(db_session, "admin@test.com", role="admin")
        target = await _make_user(db_session, "target@test.com", role="member")

        svc = ChangeRoleService(
            user_repo=UserRepository(db_session),
            audit_repo=AuditLogRepository(db_session),
        )
        result = await svc.execute(
            ChangeRolePayload(
                admin_user_id=admin.id,
                target_user_id=target.id,
                new_role="guest",
            )
        )
        assert result.new_role == "guest"

    async def test_non_admin_raises_forbidden(self, db_session: AsyncSession) -> None:
        member = await _make_user(db_session, "member@test.com", role="member")
        target = await _make_user(db_session, "target2@test.com", role="member")

        svc = ChangeRoleService(
            user_repo=UserRepository(db_session),
            audit_repo=AuditLogRepository(db_session),
        )
        with pytest.raises(AuthForbiddenError):
            await svc.execute(
                ChangeRolePayload(
                    admin_user_id=member.id,
                    target_user_id=target.id,
                    new_role="guest",
                )
            )

    async def test_invalid_role_raises(self, db_session: AsyncSession) -> None:
        admin = await _make_user(db_session, "admin2@test.com", role="admin")
        target = await _make_user(db_session, "target3@test.com")

        svc = ChangeRoleService(
            user_repo=UserRepository(db_session),
            audit_repo=AuditLogRepository(db_session),
        )
        with pytest.raises(InvalidRoleError):
            await svc.execute(
                ChangeRolePayload(
                    admin_user_id=admin.id,
                    target_user_id=target.id,
                    new_role="superuser",
                )
            )

    async def test_target_not_found_raises(self, db_session: AsyncSession) -> None:
        admin = await _make_user(db_session, "admin3@test.com", role="admin")

        svc = ChangeRoleService(
            user_repo=UserRepository(db_session),
            audit_repo=AuditLogRepository(db_session),
        )
        with pytest.raises(UserNotFoundError):
            await svc.execute(
                ChangeRolePayload(
                    admin_user_id=admin.id,
                    target_user_id=uuid.uuid4(),
                    new_role="guest",
                )
            )


class TestListAuditLogsService:
    async def test_admin_can_list_audit_logs(self, db_session: AsyncSession) -> None:
        admin = await _make_user(db_session, "auditadmin@test.com", role="admin")
        target = await _make_user(db_session, "audittarget@test.com")
        audit_repo = AuditLogRepository(db_session)
        await audit_repo.append(target.id, "LOGIN", {"ip": "1.2.3.4"})

        svc = ListAuditLogsService(
            user_repo=UserRepository(db_session),
            audit_repo=audit_repo,
        )
        result = await svc.execute(
            ListAuditLogsPayload(
                admin_user_id=admin.id,
                target_user_id=target.id,
                limit=10,
                offset=0,
            )
        )
        assert result.total_returned >= 1

    async def test_non_admin_raises_forbidden(self, db_session: AsyncSession) -> None:
        member = await _make_user(db_session, "auditnonadmin@test.com", role="member")
        svc = ListAuditLogsService(
            user_repo=UserRepository(db_session),
            audit_repo=AuditLogRepository(db_session),
        )
        with pytest.raises(AuthForbiddenError):
            await svc.execute(
                ListAuditLogsPayload(
                    admin_user_id=member.id,
                    target_user_id=uuid.uuid4(),
                )
            )
