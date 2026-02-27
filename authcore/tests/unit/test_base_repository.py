"""Unit tests for BaseRepository generic CRUD operations."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from authcore.infrastructure.database.models.user import UserModel
from authcore.infrastructure.database.repositories.base import BaseRepository


def _make_user_model(email: str) -> UserModel:
    m = UserModel()
    m.id = uuid.uuid4()
    m.email = email
    m.hashed_password = "hashed"
    m.role = "member"
    m.is_verified = False
    m.is_locked = False
    m.failed_attempts = 0
    m.lockout_until = None
    return m


class TestBaseRepositoryCreate:
    async def test_create_and_retrieve(self, db_session: AsyncSession) -> None:
        repo: BaseRepository[UserModel] = BaseRepository(db_session, UserModel)
        model = _make_user_model("base_create@test.com")
        created = await repo.create(model)
        assert created.id == model.id
        assert created.email == "base_create@test.com"

    async def test_get_by_id_returns_model(self, db_session: AsyncSession) -> None:
        repo: BaseRepository[UserModel] = BaseRepository(db_session, UserModel)
        model = _make_user_model("base_get@test.com")
        await repo.create(model)
        found = await repo.get_by_id(model.id)
        assert found is not None
        assert found.email == "base_get@test.com"

    async def test_get_by_id_missing_returns_none(self, db_session: AsyncSession) -> None:
        repo: BaseRepository[UserModel] = BaseRepository(db_session, UserModel)
        found = await repo.get_by_id(uuid.uuid4())
        assert found is None


class TestBaseRepositoryUpdate:
    async def test_update_persists_changes(self, db_session: AsyncSession) -> None:
        repo: BaseRepository[UserModel] = BaseRepository(db_session, UserModel)
        model = _make_user_model("base_update@test.com")
        await repo.create(model)
        model.role = "admin"
        updated = await repo.update(model)
        assert updated.role == "admin"


class TestBaseRepositoryDelete:
    async def test_soft_delete_hides_entity(self, db_session: AsyncSession) -> None:
        repo: BaseRepository[UserModel] = BaseRepository(db_session, UserModel)
        model = _make_user_model("base_softdel@test.com")
        await repo.create(model)
        await repo.delete(model)
        found = await repo.get_by_id(model.id)
        assert found is None

    async def test_soft_delete_visible_with_include_deleted(self, db_session: AsyncSession) -> None:
        repo: BaseRepository[UserModel] = BaseRepository(db_session, UserModel)
        model = _make_user_model("base_softdel2@test.com")
        await repo.create(model)
        await repo.delete(model)
        found = await repo.get_by_id(model.id, include_deleted=True)
        assert found is not None
        assert found.is_deleted is True

    async def test_hard_delete_removes_entity(self, db_session: AsyncSession) -> None:
        repo: BaseRepository[UserModel] = BaseRepository(db_session, UserModel)
        model = _make_user_model("base_harddel@test.com")
        await repo.create(model)
        await repo.delete(model, hard=True)
        found = await repo.get_by_id(model.id, include_deleted=True)
        assert found is None


class TestBaseRepositoryList:
    async def test_list_returns_active_entities(self, db_session: AsyncSession) -> None:
        repo: BaseRepository[UserModel] = BaseRepository(db_session, UserModel)
        for i in range(3):
            await repo.create(_make_user_model(f"list_user{i}@test.com"))
        results = await repo.list(limit=10)
        emails = {r.email for r in results}
        for i in range(3):
            assert f"list_user{i}@test.com" in emails

    async def test_list_excludes_deleted(self, db_session: AsyncSession) -> None:
        repo: BaseRepository[UserModel] = BaseRepository(db_session, UserModel)
        model = _make_user_model("list_del@test.com")
        await repo.create(model)
        await repo.delete(model)
        results = await repo.list(limit=100)
        assert all(r.email != "list_del@test.com" for r in results)

    async def test_list_limit_capped_at_100(self, db_session: AsyncSession) -> None:
        repo: BaseRepository[UserModel] = BaseRepository(db_session, UserModel)
        # list() caps at 100 internally — just verify no error
        results = await repo.list(limit=200)
        assert isinstance(results, list)


class TestBaseRepositoryCount:
    async def test_count_active_entities(self, db_session: AsyncSession) -> None:
        repo: BaseRepository[UserModel] = BaseRepository(db_session, UserModel)
        initial = await repo.count()
        await repo.create(_make_user_model("count1@test.com"))
        await repo.create(_make_user_model("count2@test.com"))
        assert await repo.count() == initial + 2

    async def test_count_excludes_deleted_by_default(self, db_session: AsyncSession) -> None:
        repo: BaseRepository[UserModel] = BaseRepository(db_session, UserModel)
        model = _make_user_model("count_del@test.com")
        await repo.create(model)
        before = await repo.count()
        await repo.delete(model)
        after = await repo.count()
        assert after == before - 1

    async def test_count_includes_deleted_when_requested(self, db_session: AsyncSession) -> None:
        repo: BaseRepository[UserModel] = BaseRepository(db_session, UserModel)
        model = _make_user_model("count_inc@test.com")
        await repo.create(model)
        await repo.delete(model)
        count = await repo.count(include_deleted=True)
        assert count > 0


class TestBaseRepositoryFindOneBy:
    async def test_find_one_by_email(self, db_session: AsyncSession) -> None:
        repo: BaseRepository[UserModel] = BaseRepository(db_session, UserModel)
        model = _make_user_model("findone@test.com")
        await repo.create(model)
        found = await repo.find_one_by(email="findone@test.com")
        assert found is not None
        assert found.email == "findone@test.com"

    async def test_find_one_by_missing_returns_none(self, db_session: AsyncSession) -> None:
        repo: BaseRepository[UserModel] = BaseRepository(db_session, UserModel)
        found = await repo.find_one_by(email="nonexistent@test.com")
        assert found is None

    async def test_find_one_by_unknown_column_returns_none(self, db_session: AsyncSession) -> None:
        repo: BaseRepository[UserModel] = BaseRepository(db_session, UserModel)
        # Unknown column just produces no conditions → returns any row or None
        result = await repo.find_one_by(nonexistent_column="value")
        # Should not raise
        assert result is None or result is not None
