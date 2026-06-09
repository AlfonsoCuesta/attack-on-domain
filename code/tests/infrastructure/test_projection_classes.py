from __future__ import annotations


import pytest
from aod._internal.core.event_emitter import Event
from aod._internal.infrastructure.commit_context import _CommitContext
from aod._internal.infrastructure.projection import (
    Projection,
    ProjectionBase,
    ReadModel,
    ReadProjection,
    WriteModel,
    WriteProjection,
)
from aod._internal.infrastructure.session import Session


class UserReadModel(ReadModel):
    user_id: int


class UserWriteModel(WriteModel):
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


class TestReadModel:
    def test_can_instantiate(self) -> None:
        m = UserReadModel(user_id=1)
        assert m.user_id == 1

    def test_is_immutable(self) -> None:
        m = UserReadModel(user_id=1)
        with pytest.raises(Exception):
            m.user_id = 99


class TestWriteModel:
    def test_can_instantiate(self) -> None:
        m = UserWriteModel(user_id=1, name="Alice")
        assert m.user_id == 1
        assert m.name == "Alice"

    def test_is_immutable(self) -> None:
        m = UserWriteModel(user_id=1, name="Alice")
        with pytest.raises(Exception):
            m.name = "Bob"


class TestProjectionBase:
    def test_can_instantiate(self) -> None:
        p = ProjectionBase()
        assert p.session is None

    def test_with_session(self) -> None:
        session = _TestSession()
        p = ProjectionBase(session=session)
        assert isinstance(p.session, _TestSession)

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
            def read(self, model: ReadModel) -> str:  # type: ignore[override]
                return f"user-{model.user_id}"  # type: ignore[attr-defined]

        p = GetUser()
        result = p.read(UserReadModel(user_id=1))
        assert result == "user-1"

    def test_read_captures_events(self) -> None:
        class GetUser(ReadProjection):
            def read(self, model: ReadModel) -> str:  # type: ignore[override]
                self._event_emitter.emit(UserCreated(user_id=model.user_id, name="test"))  # type: ignore[attr-defined]
                return "ok"

        p = GetUser()
        p.read(UserReadModel(user_id=1))
        assert len(p.events) == 1
        assert p.events[0].user_id == 1

    def test_events_cleared_on_new_read(self) -> None:
        class GetUser(ReadProjection):
            def read(self, model: ReadModel) -> str:  # type: ignore[override]
                self._event_emitter.emit(UserCreated(user_id=model.user_id, name="test"))  # type: ignore[attr-defined]
                return "ok"

        p = GetUser()
        p.read(UserReadModel(user_id=1))
        assert len(p.events) == 1
        p.read(UserReadModel(user_id=2))
        assert len(p.events) == 1

    def test_read_exception_is_logged_and_re_raised(self) -> None:
        class FailingRead(ReadProjection):
            def read(self, model: ReadModel) -> str:  # type: ignore[override]
                raise ValueError("read failed")

        p = FailingRead()
        with pytest.raises(ValueError, match="read failed"):
            p.read(UserReadModel(user_id=1))

    def test_read_handles_model_with_defaults(self) -> None:
        class SearchUsers(ReadProjection):
            def read(self, model: ReadModel) -> dict:  # type: ignore[override]
                return {"found": model.user_id > 0}  # type: ignore[attr-defined]

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
            def write(self, model: WriteModel) -> str:  # type: ignore[override]
                self._event_emitter.emit(UserCreated(user_id=model.user_id, name=model.name))  # type: ignore[attr-defined]
                return "created"

        p = CreateUser()
        result = p.write(UserWriteModel(user_id=1, name="Alice"))
        assert result == "created"
        assert len(p.events) == 1
        assert p.events[0].name == "Alice"

    def test_write_commit_context_enabled(self) -> None:
        class CreateUser(WriteProjection):
            def write(self, model: WriteModel) -> str:  # type: ignore[override]
                assert _CommitContext.get(False) is True
                return "created"

        p = CreateUser()
        result = p.write(UserWriteModel(user_id=1, name="Alice"))
        assert result == "created"

    def test_write_can_commit_session(self) -> None:
        class CreateUser(WriteProjection):
            def write(self, model: WriteModel) -> str:  # type: ignore[override]
                assert self.session is not None
                self.session.commit()
                return "created"

        session = _TestSession()
        p = CreateUser(session=session)
        p.write(UserWriteModel(user_id=1, name="Alice"))
        assert session._committed

    def test_write_rolls_back_session_on_error(self) -> None:
        class FailingWrite(WriteProjection):
            def write(self, model: WriteModel) -> str:  # type: ignore[override]
                raise ValueError("write failed")

        session = _TestSession()
        p = FailingWrite(session=session)
        with pytest.raises(ValueError, match="write failed"):
            p.write(UserWriteModel(user_id=1, name="Alice"))
        assert session._rolled_back

    def test_write_without_session_does_not_crash_on_error(self) -> None:
        class FailingWrite(WriteProjection):
            def write(self, model: WriteModel) -> str:  # type: ignore[override]
                raise ValueError("write failed")

        p = FailingWrite()
        with pytest.raises(ValueError, match="write failed"):
            p.write(UserWriteModel(user_id=1, name="Alice"))

    def test_commit_context_reset_after_error(self) -> None:
        class FailingWrite(WriteProjection):
            def write(self, model: WriteModel) -> str:  # type: ignore[override]
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
            def read(self, model: ReadModel) -> dict:
                return {"action": "read", "id": model.user_id}

            def write(self, model: WriteModel) -> str:
                return "written"

        p = UserProjection()
        read_result = p.read(UserReadModel(user_id=42))
        assert read_result == {"action": "read", "id": 42}

        write_result = p.write(UserWriteModel(user_id=1, name="test"))
        assert write_result == "written"

    def test_read_captures_events(self) -> None:
        class UserProjection(Projection):
            def read(self, model: ReadModel) -> str:
                self._event_emitter.emit(UserCreated(user_id=1, name="from_read"))
                return "ok"

            def write(self, model: WriteModel) -> str:
                return "ok"

        p = UserProjection()
        p.read(UserReadModel(user_id=1))
        assert len(p.events) == 1
        assert p.events[0].name == "from_read"

    def test_write_captures_events(self) -> None:
        class UserProjection(Projection):
            def read(self, model: ReadModel) -> str:
                return "ok"

            def write(self, model: WriteModel) -> str:
                self._event_emitter.emit(UserCreated(user_id=2, name="from_write"))
                return "ok"

        p = UserProjection()
        p.write(UserWriteModel(user_id=2, name="from_write"))
        assert len(p.events) == 1
        assert p.events[0].name == "from_write"

    def test_commit_context_active_during_write(self) -> None:
        class UserProjection(Projection):
            def read(self, model: ReadModel) -> str:
                return "ok"

            def write(self, model: WriteModel) -> str:
                assert _CommitContext.get(False) is True
                return "ok"

        p = UserProjection()
        p.write(UserWriteModel(user_id=1, name="test"))

    def test_commit_context_not_active_during_read(self) -> None:
        class UserProjection(Projection):
            def read(self, model: ReadModel) -> str:
                assert _CommitContext.get(False) is False
                return "ok"

            def write(self, model: WriteModel) -> str:
                return "ok"

        p = UserProjection()
        p.read(UserReadModel(user_id=1))

    def test_write_rolls_back_on_error(self) -> None:
        class UserProjection(Projection):
            def read(self, model: ReadModel) -> str:
                return "ok"

            def write(self, model: WriteModel) -> str:
                raise ValueError("write failed")

        session = _TestSession()
        p = UserProjection(session=session)
        with pytest.raises(ValueError):
            p.write(UserWriteModel(user_id=1, name="test"))
        assert session._rolled_back

    def test_write_commit_context_reset_after_error(self) -> None:
        class UserProjection(Projection):
            def read(self, model: ReadModel) -> str:
                return "ok"

            def write(self, model: WriteModel) -> str:
                raise ValueError("write failed")

        p = UserProjection()
        with pytest.raises(ValueError):
            p.write(UserWriteModel(user_id=1, name="test"))
        assert _CommitContext.get(False) is False