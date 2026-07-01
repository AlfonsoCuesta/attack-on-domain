from __future__ import annotations

from typing import cast

import pytest
from aod._internal.application.dto import DTO
from aod._internal.core.event_emitter import Event
from aod._internal.core.infrastructure_exception import InvalidPortFieldError
from aod._internal.infrastructure.commit_context import _CommitContext
from aod._internal.infrastructure.projection import (
    AsyncProjection,
    AsyncReadProjection,
    AsyncWriteProjection,
    Projection,
    ProjectionBase,
    ReadProjection,
    WriteProjection,
)
from aod._internal.infrastructure.session import AsyncSession, Session


class UserReadModel(DTO):
    user_id: int


class UserWriteModel(DTO):
    user_id: int
    name: str


class UserCreated(Event):
    user_id: int
    name: str


class _TestSession(Session):
    def __init__(self) -> None:
        super().__init__()
        object.__setattr__(self, "_committed", False)
        object.__setattr__(self, "_rolled_back", False)

    def is_dirty(self) -> bool:
        return True

    def execute(self, operation: object) -> object:
        return operation

    def query(self, operation: object) -> object:
        return operation

    def begin(self) -> None:
        pass

    def commit(self) -> None:
        object.__setattr__(self, "_committed", True)

    def rollback(self) -> None:
        object.__setattr__(self, "_rolled_back", True)

    def close(self) -> None:
        pass


class _TestAsyncSession(AsyncSession):
    def __init__(self) -> None:
        super().__init__()
        object.__setattr__(self, "_committed", False)
        object.__setattr__(self, "_rolled_back", False)

    def is_dirty(self) -> bool:
        return True

    async def execute(self, operation: object) -> object:
        return operation

    async def query(self, operation: object) -> object:
        return operation

    async def begin(self) -> None:
        pass

    async def commit(self) -> None:
        object.__setattr__(self, "_committed", True)

    async def rollback(self) -> None:
        object.__setattr__(self, "_rolled_back", True)

    async def close(self) -> None:
        pass


class TestDTO:
    def test_can_instantiate_read_like(self) -> None:
        m = UserReadModel(user_id=1)
        assert m.user_id == 1

    def test_can_instantiate_write_like(self) -> None:
        m = UserWriteModel(user_id=1, name="Alice")
        assert m.user_id == 1
        assert m.name == "Alice"

    def test_is_mutable(self) -> None:
        m = UserWriteModel(user_id=1, name="Alice")
        m.name = "Bob"
        assert m.name == "Bob"


class TestProjectionBase:
    def test_can_instantiate(self) -> None:
        ProjectionBase()

    def test_has_default_logger(self) -> None:
        p = ProjectionBase()
        assert p.logger is not None


class TestReadProjection:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            ReadProjection()

    def test_subclass_without_read_is_abstract(self) -> None:
        class Incomplete(ReadProjection):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_read_returns_result(self) -> None:
        class GetUser(ReadProjection):
            def read(self, model: UserReadModel) -> str:
                return f"user-{model.user_id}"

        p = GetUser()
        result = p.read(UserReadModel(user_id=1))
        assert result == "user-1"

    def test_read_captures_events(self) -> None:
        class GetUser(ReadProjection):
            def read(self, model: UserReadModel) -> str:
                self._event_emitter.emit(UserCreated(user_id=model.user_id, name="test"))
                return "ok"

        p = GetUser()
        p.read(UserReadModel(user_id=1))
        assert len(p.events) == 1
        assert p.events[0].user_id == 1

    def test_events_cleared_on_new_read(self) -> None:
        class GetUser(ReadProjection):
            def read(self, model: UserReadModel) -> str:
                self._event_emitter.emit(UserCreated(user_id=model.user_id, name="test"))
                return "ok"

        p = GetUser()
        p.read(UserReadModel(user_id=1))
        assert len(p.events) == 1
        p.read(UserReadModel(user_id=2))
        assert len(p.events) == 1

    def test_read_exception_is_logged_and_re_raised(self) -> None:
        class FailingRead(ReadProjection):
            def read(self, model: UserReadModel) -> str:
                raise ValueError("read failed")

        p = FailingRead()
        with pytest.raises(ValueError, match="read failed"):
            p.read(UserReadModel(user_id=1))

    def test_read_handles_model_with_defaults(self) -> None:
        class SearchUsers(ReadProjection):
            def read(self, model: UserReadModel) -> dict:
                return {"found": model.user_id > 0}

        p = SearchUsers()
        result = p.read(UserReadModel(user_id=1))
        assert result == {"found": True}


class TestWriteProjection:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            WriteProjection()

    def test_subclass_without_write_is_abstract(self) -> None:
        class Incomplete(WriteProjection):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_write_captures_events(self) -> None:
        class CreateUser(WriteProjection):
            def write(self, model: UserWriteModel) -> str:
                self._event_emitter.emit(UserCreated(user_id=model.user_id, name=model.name))
                return "created"

        p = CreateUser()
        result = p.write(UserWriteModel(user_id=1, name="Alice"))
        assert result == "created"
        assert len(p.events) == 1
        assert p.events[0].name == "Alice"

    def test_write_commit_context_enabled(self) -> None:
        class CreateUser(WriteProjection):
            def write(self, model: UserWriteModel) -> str:
                assert _CommitContext.get(False) is True
                return "created"

        p = CreateUser()
        result = p.write(UserWriteModel(user_id=1, name="Alice"))
        assert result == "created"

    def test_write_can_commit_session(self) -> None:
        class CreateUser(WriteProjection):
            def write(self, model: UserWriteModel) -> str:
                assert self.session is not None
                self.session.commit()
                return "created"

        session = _TestSession()
        p = CreateUser(session=session)
        p.write(UserWriteModel(user_id=1, name="Alice"))
        assert session._committed

    def test_write_rolls_back_session_on_error(self) -> None:
        class FailingWrite(WriteProjection):
            def write(self, model: UserWriteModel) -> str:
                raise ValueError("write failed")

        session = _TestSession()
        p = FailingWrite(session=session)
        with pytest.raises(ValueError, match="write failed"):
            p.write(UserWriteModel(user_id=1, name="Alice"))
        assert session._rolled_back

    def test_write_without_session_does_not_crash_on_error(self) -> None:
        class FailingWrite(WriteProjection):
            def write(self, model: UserWriteModel) -> str:
                raise ValueError("write failed")

        p = FailingWrite()
        with pytest.raises(ValueError, match="write failed"):
            p.write(UserWriteModel(user_id=1, name="Alice"))

    def test_commit_context_reset_after_error(self) -> None:
        class FailingWrite(WriteProjection):
            def write(self, model: UserWriteModel) -> str:
                raise ValueError("write failed")

        p = FailingWrite()
        with pytest.raises(ValueError):
            p.write(UserWriteModel(user_id=1, name="Alice"))
        assert _CommitContext.get(False) is False


class TestProjection:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            Projection()

    def test_subclass_without_methods_is_abstract(self) -> None:
        class Incomplete(Projection):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_read_and_write_work(self) -> None:
        class UserProjection(Projection):
            def read(self, model: UserReadModel) -> dict:
                return {"action": "read", "id": model.user_id}

            def write(self, model: UserWriteModel) -> str:
                return "written"

        p = UserProjection()
        read_result = p.read(UserReadModel(user_id=42))
        assert read_result == {"action": "read", "id": 42}

        write_result = p.write(UserWriteModel(user_id=1, name="test"))
        assert write_result == "written"

    def test_read_captures_events(self) -> None:
        class UserProjection(Projection):
            def read(self, model: DTO) -> str:
                self._event_emitter.emit(UserCreated(user_id=1, name="from_read"))
                return "ok"

            def write(self, model: DTO) -> str:
                return "ok"

        p = UserProjection()
        p.read(UserReadModel(user_id=1))
        assert len(p.events) == 1
        assert p.events[0].name == "from_read"

    def test_write_captures_events(self) -> None:
        class UserProjection(Projection):
            def read(self, model: DTO) -> str:
                return "ok"

            def write(self, model: DTO) -> str:
                self._event_emitter.emit(UserCreated(user_id=2, name="from_write"))
                return "ok"

        p = UserProjection()
        p.write(UserWriteModel(user_id=2, name="from_write"))
        assert len(p.events) == 1
        assert p.events[0].name == "from_write"

    def test_commit_context_active_during_write(self) -> None:
        class UserProjection(Projection):
            def read(self, model: DTO) -> str:
                return "ok"

            def write(self, model: DTO) -> str:
                assert _CommitContext.get(False) is True
                return "ok"

        p = UserProjection()
        p.write(UserWriteModel(user_id=1, name="test"))

    def test_commit_context_not_active_during_read(self) -> None:
        class UserProjection(Projection):
            def read(self, model: DTO) -> str:
                assert _CommitContext.get(False) is False
                return "ok"

            def write(self, model: DTO) -> str:
                return "ok"

        p = UserProjection()
        p.read(UserReadModel(user_id=1))


class TestAsyncReadProjection:
    async def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            AsyncReadProjection()

    async def test_subclass_without_read_is_abstract(self) -> None:
        class Incomplete(AsyncReadProjection):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    async def test_read_returns_result(self) -> None:
        class GetUser(AsyncReadProjection):
            async def read(self, model: UserReadModel) -> str:
                return f"user-{model.user_id}"

        p = GetUser()
        result = await p.read(UserReadModel(user_id=1))
        assert result == "user-1"

    async def test_read_captures_events(self) -> None:
        class GetUser(AsyncReadProjection):
            async def read(self, model: UserReadModel) -> str:
                self._event_emitter.emit(UserCreated(user_id=model.user_id, name="test"))
                return "ok"

        p = GetUser()
        await p.read(UserReadModel(user_id=1))
        assert len(p.events) == 1
        assert p.events[0].user_id == 1

    async def test_read_exception_is_logged_and_re_raised(self) -> None:
        class FailingRead(AsyncReadProjection):
            async def read(self, model: UserReadModel) -> str:
                raise ValueError("read failed")

        p = FailingRead()
        with pytest.raises(ValueError, match="read failed"):
            await p.read(UserReadModel(user_id=1))


class TestAsyncWriteProjection:
    async def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            AsyncWriteProjection()

    async def test_subclass_without_write_is_abstract(self) -> None:
        class Incomplete(AsyncWriteProjection):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    async def test_write_captures_events(self) -> None:
        class CreateUser(AsyncWriteProjection):
            async def write(self, model: UserWriteModel) -> str:
                self._event_emitter.emit(UserCreated(user_id=model.user_id, name=model.name))
                return "created"

        p = CreateUser()
        result = await p.write(UserWriteModel(user_id=1, name="Alice"))
        assert result == "created"
        assert len(p.events) == 1
        assert p.events[0].name == "Alice"

    async def test_write_commit_context_enabled(self) -> None:
        class CreateUser(AsyncWriteProjection):
            async def write(self, model: UserWriteModel) -> str:
                assert _CommitContext.get(False) is True
                return "created"

        p = CreateUser()
        result = await p.write(UserWriteModel(user_id=1, name="Alice"))
        assert result == "created"

    async def test_write_can_commit_session(self) -> None:
        class CreateUser(AsyncWriteProjection):
            async def write(self, model: UserWriteModel) -> str:
                assert self.session is not None
                await cast(AsyncSession, self.session).commit()
                return "created"

        session = _TestAsyncSession()
        p = CreateUser(session=session)
        await p.write(UserWriteModel(user_id=1, name="Alice"))
        assert session._committed

    async def test_write_rolls_back_session_on_error(self) -> None:
        class FailingWrite(AsyncWriteProjection):
            async def write(self, model: UserWriteModel) -> str:
                raise ValueError("write failed")

        session = _TestAsyncSession()
        p = FailingWrite(session=session)
        with pytest.raises(ValueError, match="write failed"):
            await p.write(UserWriteModel(user_id=1, name="Alice"))
        assert session._rolled_back

    async def test_commit_context_reset_after_error(self) -> None:
        class FailingWrite(AsyncWriteProjection):
            async def write(self, model: UserWriteModel) -> str:
                raise ValueError("write failed")

        p = FailingWrite()
        with pytest.raises(ValueError):
            await p.write(UserWriteModel(user_id=1, name="Alice"))
        assert _CommitContext.get(False) is False


class TestAsyncProjection:
    async def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            AsyncProjection()

    async def test_read_and_write_work(self) -> None:
        class UserProjection(AsyncProjection):
            async def read(self, model: UserReadModel) -> dict:
                return {"action": "read", "id": model.user_id}

            async def write(self, model: UserWriteModel) -> str:
                return "written"

        p = UserProjection()
        read_result = await p.read(UserReadModel(user_id=42))
        assert read_result == {"action": "read", "id": 42}

        write_result = await p.write(UserWriteModel(user_id=1, name="test"))
        assert write_result == "written"

    def test_write_rolls_back_on_error(self) -> None:
        class UserProjection(Projection):
            def read(self, model: DTO) -> str:
                return "ok"

            def write(self, model: DTO) -> str:
                raise ValueError("write failed")

        session = _TestSession()
        p = UserProjection(session=session)
        with pytest.raises(ValueError):
            p.write(UserWriteModel(user_id=1, name="test"))
        assert session._rolled_back

    def test_write_commit_context_reset_after_error(self) -> None:
        class UserProjection(Projection):
            def read(self, model: DTO) -> str:
                return "ok"

            def write(self, model: DTO) -> str:
                raise ValueError("write failed")

        p = UserProjection()
        with pytest.raises(ValueError):
            p.write(UserWriteModel(user_id=1, name="test"))
        assert _CommitContext.get(False) is False


class TestProjectionMultipleSessions:
    def test_multiple_session_fields_raises_error(self) -> None:
        with pytest.raises(InvalidPortFieldError, match="session"):

            class _Bad(ReadProjection):
                session: Session
                other_session: AsyncSession | None

                def read(self, model: DTO) -> str:
                    return "ok"
