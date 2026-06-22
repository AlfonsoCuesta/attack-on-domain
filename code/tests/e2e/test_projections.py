from __future__ import annotations


import pytest
from aod._internal.core.event_emitter import Event
from aod._internal.infrastructure.commit_context import _CommitContext
from aod._internal.infrastructure.container import AdapterContainer
from aod._internal.core.infrastructure_exception import SessionNotFoundError
from aod._internal.infrastructure.projection import (
    AsyncProjection,
    AsyncReadProjection,
    AsyncWriteProjection,
    Projection,
    ReadModel,
    ReadProjection,
    WriteModel,
    WriteProjection,
)
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.testing.doubles.application import SpyLogger, SpyEventBus


# ---------------------------------------------------------------------------
# Domain events
# ---------------------------------------------------------------------------


class UserCreated(Event):
    user_id: int
    name: str


class OrderPlaced(Event):
    order_id: str
    total: int


# ---------------------------------------------------------------------------
# Projection models
# ---------------------------------------------------------------------------


class UserReadModel(ReadModel):
    user_id: int


class UserWriteModel(WriteModel):
    user_id: int
    name: str


class OrderWriteModel(WriteModel):
    order_id: str
    items: list[str]
    total: int


# ---------------------------------------------------------------------------
# Session implementations
# ---------------------------------------------------------------------------


class _TestSession(Session):
    def __init__(self) -> None:
        super().__init__()
        object.__setattr__(self, "_committed", False)
        object.__setattr__(self, "_rolled_back", False)

    def is_dirty(self) -> bool:
        return True

    def execute(self, operation: object) -> object: ...
    def query(self, operation: object) -> object: ...
    def begin(self) -> None: ...
    def commit(self) -> None:
        object.__setattr__(self, "_committed", True)

    def rollback(self) -> None:
        object.__setattr__(self, "_rolled_back", True)

    def close(self) -> None: ...


class _TestAsyncSession(AsyncSession):
    def __init__(self) -> None:
        super().__init__()
        object.__setattr__(self, "_committed", False)
        object.__setattr__(self, "_rolled_back", False)

    def is_dirty(self) -> bool:
        return True

    async def execute(self, operation: object) -> object: ...
    async def query(self, operation: object) -> object: ...
    async def begin(self) -> None: ...
    async def commit(self) -> None:
        object.__setattr__(self, "_committed", True)

    async def rollback(self) -> None:
        object.__setattr__(self, "_rolled_back", True)

    async def close(self) -> None: ...


# ---------------------------------------------------------------------------
# Concrete projections
# ---------------------------------------------------------------------------


class GetUserProjection(ReadProjection):
    def read(self, model: UserReadModel) -> dict:
        return {"id": model.user_id, "name": "Alice"}


class CreateUserProjection(WriteProjection):
    def write(self, model: UserWriteModel) -> str:
        self._event_emitter.emit(UserCreated(user_id=model.user_id, name=model.name))
        return "created"


class FullUserProjection(Projection):
    def read(self, model: UserReadModel) -> dict:
        return {"id": model.user_id}

    def write(self, model: UserWriteModel) -> str:
        self._event_emitter.emit(UserCreated(user_id=model.user_id, name=model.name))
        return "ok"


class AsyncGetUserProjection(AsyncReadProjection):
    async def read(self, model: UserReadModel) -> dict:
        return {"id": model.user_id, "name": "Async Alice"}


class AsyncCreateUserProjection(AsyncWriteProjection):
    async def write(self, model: UserWriteModel) -> str:
        self._event_emitter.emit(UserCreated(user_id=model.user_id, name=model.name))
        return "async-created"


class AsyncFullUserProjection(AsyncProjection):
    async def read(self, model: UserReadModel) -> dict:
        return {"id": model.user_id}

    async def write(self, model: UserWriteModel) -> str:
        self._event_emitter.emit(UserCreated(user_id=model.user_id, name=model.name))
        return "async-ok"


# ---------------------------------------------------------------------------
# Container for injection tests
# ---------------------------------------------------------------------------


class ProjectionContainer(AdapterContainer):
    pass


# ===========================================================================
# TESTS
# ===========================================================================


class TestReadProjection:
    def test_read_returns_result(self) -> None:
        p = GetUserProjection()
        result = p.read(UserReadModel(user_id=42))
        assert result == {"id": 42, "name": "Alice"}

    def test_read_captures_events(self) -> None:
        class EmittingRead(ReadProjection):
            def read(self, model: UserReadModel) -> str:
                self._event_emitter.emit(UserCreated(user_id=model.user_id, name="test"))
                return "ok"

        p = EmittingRead()
        p.read(UserReadModel(user_id=1))
        assert len(p.events) == 1
        assert p.events[0].user_id == 1

    def test_read_events_cleared_on_new_call(self) -> None:
        class EmittingRead(ReadProjection):
            def read(self, model: UserReadModel) -> str:
                self._event_emitter.emit(UserCreated(user_id=model.user_id, name="test"))
                return "ok"

        p = EmittingRead()
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

    def test_read_with_logger_and_event_bus(self) -> None:
        logger = SpyLogger()
        bus = SpyEventBus()
        p = GetUserProjection(logger=logger, event_bus=bus)
        p.read(UserReadModel(user_id=1))
        completions = [e for e in logger.entries if "completed" in str(e.msg)]
        assert len(completions) >= 1

    def test_read_with_session(self) -> None:
        session = _TestSession()
        p = GetUserProjection(session=session)
        p.read(UserReadModel(user_id=1))
        assert isinstance(p.session, Session)


class TestWriteProjection:
    def test_write_returns_result(self) -> None:
        p = CreateUserProjection()
        result = p.write(UserWriteModel(user_id=1, name="Alice"))
        assert result == "created"

    def test_write_captures_events(self) -> None:
        p = CreateUserProjection()
        p.write(UserWriteModel(user_id=1, name="Alice"))
        assert len(p.events) == 1
        assert p.events[0].name == "Alice"

    def test_write_commit_context_enabled(self) -> None:
        class CheckContext(WriteProjection):
            def write(self, model: UserWriteModel) -> str:
                assert _CommitContext.get(False) is True
                return "ok"

        p = CheckContext()
        p.write(UserWriteModel(user_id=1, name="test"))

    def test_write_rolls_back_on_error(self) -> None:
        session = _TestSession()

        class FailingWrite(WriteProjection):
            def write(self, model: UserWriteModel) -> str:
                raise ValueError("write failed")

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

    def test_write_with_logger_and_event_bus(self) -> None:
        logger = SpyLogger()
        bus = SpyEventBus()
        p = CreateUserProjection(logger=logger, event_bus=bus)
        p.write(UserWriteModel(user_id=1, name="Alice"))
        assert len(bus.published) >= 1
        completions = [e for e in logger.entries if "completed" in str(e.msg)]
        assert len(completions) >= 1


class TestFullProjection:
    def test_read_and_write(self) -> None:
        p = FullUserProjection()
        read_result = p.read(UserReadModel(user_id=42))
        assert read_result == {"id": 42}
        write_result = p.write(UserWriteModel(user_id=1, name="Alice"))
        assert write_result == "ok"

    def test_read_captures_events(self) -> None:
        p = FullUserProjection()
        p.read(UserReadModel(user_id=1))
        assert len(p.events) == 0

    def test_write_captures_events(self) -> None:
        p = FullUserProjection()
        p.write(UserWriteModel(user_id=1, name="Alice"))
        assert len(p.events) == 1

    def test_commit_context_active_during_write_only(self) -> None:
        class CheckContext(Projection):
            def read(self, model: UserReadModel) -> str:
                assert _CommitContext.get(False) is False
                return "ok"

            def write(self, model: UserWriteModel) -> str:
                assert _CommitContext.get(False) is True
                return "ok"

        p = CheckContext()
        p.read(UserReadModel(user_id=1))
        p.write(UserWriteModel(user_id=1, name="test"))


class TestAsyncReadProjection:
    async def test_read_returns_result(self) -> None:
        p = AsyncGetUserProjection()
        result = await p.read(UserReadModel(user_id=42))
        assert result == {"id": 42, "name": "Async Alice"}

    async def test_read_captures_events(self) -> None:
        class Emitting(AsyncReadProjection):
            async def read(self, model: UserReadModel) -> str:
                self._event_emitter.emit(UserCreated(user_id=model.user_id, name="test"))
                return "ok"

        p = Emitting()
        await p.read(UserReadModel(user_id=1))
        assert len(p.events) == 1

    async def test_read_exception_is_logged_and_re_raised(self) -> None:
        class Failing(AsyncReadProjection):
            async def read(self, model: UserReadModel) -> str:
                raise ValueError("async read failed")

        p = Failing()
        with pytest.raises(ValueError, match="async read failed"):
            await p.read(UserReadModel(user_id=1))


class TestAsyncWriteProjection:
    async def test_write_returns_result(self) -> None:
        p = AsyncCreateUserProjection()
        result = await p.write(UserWriteModel(user_id=1, name="Alice"))
        assert result == "async-created"

    async def test_write_captures_events(self) -> None:
        p = AsyncCreateUserProjection()
        await p.write(UserWriteModel(user_id=1, name="Alice"))
        assert len(p.events) == 1

    async def test_write_commit_context_enabled(self) -> None:
        class CheckContext(AsyncWriteProjection):
            async def write(self, model: UserWriteModel) -> str:
                assert _CommitContext.get(False) is True
                return "ok"

        p = CheckContext()
        await p.write(UserWriteModel(user_id=1, name="test"))

    async def test_write_rolls_back_on_error(self) -> None:
        class Failing(AsyncWriteProjection):
            async def write(self, model: UserWriteModel) -> str:
                raise ValueError("async write failed")

        session = _TestAsyncSession()
        p = Failing(session=session)
        with pytest.raises(ValueError, match="async write failed"):
            await p.write(UserWriteModel(user_id=1, name="Alice"))
        assert session._rolled_back

    async def test_commit_context_reset_after_error(self) -> None:
        class Failing(AsyncWriteProjection):
            async def write(self, model: UserWriteModel) -> str:
                raise ValueError("async write failed")

        p = Failing()
        with pytest.raises(ValueError):
            await p.write(UserWriteModel(user_id=1, name="Alice"))
        assert _CommitContext.get(False) is False


class TestAsyncFullProjection:
    async def test_read_and_write(self) -> None:
        p = AsyncFullUserProjection()
        read_result = await p.read(UserReadModel(user_id=42))
        assert read_result == {"id": 42}
        write_result = await p.write(UserWriteModel(user_id=1, name="Alice"))
        assert write_result == "async-ok"

    async def test_write_captures_events(self) -> None:
        p = AsyncFullUserProjection()
        await p.write(UserWriteModel(user_id=1, name="Alice"))
        assert len(p.events) == 1


class TestProjectionInjection:
    def test_inject_read_projection(self) -> None:
        container = ProjectionContainer(sessions={_TestSession})
        uc = container.adapt_projection(GetUserProjection)
        p = uc
        assert isinstance(p.session, Session)
        assert p.logger is not None
        assert p.event_bus is not None

    def test_inject_write_projection(self) -> None:
        container = ProjectionContainer(sessions={_TestSession})
        uc = container.adapt_projection(CreateUserProjection)
        p = uc
        assert isinstance(p.session, Session)

    def test_inject_full_projection(self) -> None:
        container = ProjectionContainer(sessions={_TestSession})
        uc = container.adapt_projection(FullUserProjection)
        p = uc
        assert isinstance(p.session, Session)

    def test_inject_with_logger_and_event_bus(self) -> None:
        logger = SpyLogger()
        bus = SpyEventBus()
        container = ProjectionContainer(sessions={_TestSession})
        uc = container.adapt_projection(GetUserProjection, logger=logger, event_bus=bus)
        p = uc
        p.read(UserReadModel(user_id=1))
        completions = [e for e in logger.entries if "completed" in str(e.msg)]
        assert len(completions) >= 1

    def test_inject_without_session(self) -> None:
        container = ProjectionContainer()

        with pytest.raises(SessionNotFoundError):
            container.adapt_projection(GetUserProjection)
