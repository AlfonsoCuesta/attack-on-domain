from __future__ import annotations

from typing import Any

import pytest
from aod._internal.application.cache.cache import Cache, _CacheEntry
from aod._internal.application.event_bus import EventBus
from aod._internal.application.logger import Logger
from aod._internal.application.transaction import AsyncTransaction, Transaction
from aod._internal.core.event_emitter import Event, IntegrationEvent
from aod._internal.infrastructure.commit_context import _CommitContext
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.core.fields.fields import PrivateField
from aod.testing.doubles import port_stub


class _CommitTrackSession(Session):
    _committed: bool = PrivateField(default=False)
    _rolled_back: bool = PrivateField(default=False)
    _begun: bool = PrivateField(default=False)

    def is_dirty(self) -> bool:
        return True

    def begin(self) -> None:
        self._begun = True

    def commit(self) -> None:
        self._committed = True

    def rollback(self) -> None:
        self._rolled_back = True

    def close(self) -> None:
        pass

    def execute(self, operation: object) -> object:
        return operation

    def query(self, operation: object) -> object:
        return operation


class _CleanSession(Session):
    def is_dirty(self) -> bool:
        return False

    def begin(self) -> None:
        pass

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass

    def execute(self, operation: object) -> object:
        return operation

    def query(self, operation: object) -> object:
        return operation


class _CommitTrackAsyncSession(AsyncSession):
    _committed: bool = PrivateField(default=False)
    _rolled_back: bool = PrivateField(default=False)
    _begun: bool = PrivateField(default=False)

    def is_dirty(self) -> bool:
        return True

    async def begin(self) -> None:
        self._begun = True

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        self._rolled_back = True

    async def close(self) -> None:
        pass

    async def execute(self, operation: object) -> object:
        return operation

    async def query(self, operation: object) -> object:
        return operation


class _CleanAsyncSession(AsyncSession):
    def is_dirty(self) -> bool:
        return False

    async def begin(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def execute(self, operation: object) -> object:
        return operation

    async def query(self, operation: object) -> object:
        return operation


class ConcreteCache(Cache):
    _stored: dict[str, Any] = PrivateField(default_factory=dict)

    def get(self, key: str) -> object:
        return self._stored.get(key)

    def set(self, key: str, value: object, ttl: float | None = None) -> None:
        self._stored[key] = value

    def delete(self, key: str) -> None:
        self._stored.pop(key, None)


class SampleEvent(Event):
    value: str


class IntegrationSampleEvent(IntegrationEvent):
    value: str


def _run(tx: Transaction, fn: Any, *args: Any, **kwargs: Any) -> Any:
    return tx.run_transaction(fn, *args, **kwargs)


async def _run_async(tx: AsyncTransaction, fn: Any, *args: Any, **kwargs: Any) -> Any:
    return await tx.run_transaction(fn, *args, **kwargs)


class TestTransactionConstruction:
    def test_default_construction(self) -> None:
        tx = Transaction()
        assert tx.sessions == []
        assert tx.caches == []
        assert tx.loggers == []
        assert tx.event_buses == []
        assert tx.operation_name == ""
        assert tx.only_read is False

    def test_custom_construction(self) -> None:
        session = _CommitTrackSession()
        cache = ConcreteCache()
        logger = port_stub(Logger)()
        bus = port_stub(EventBus)()
        tx = Transaction(
            sessions=[session],
            caches=[cache],
            loggers=[logger],
            event_buses=[bus],
            operation_name="test",
            only_read=True,
        )
        assert tx.sessions == [session]
        assert tx.caches == [cache]
        assert tx.loggers == [logger]
        assert tx.event_buses == [bus]
        assert tx.operation_name == "test"
        assert tx.only_read is True

    def test_add_session(self) -> None:
        tx = Transaction()
        s1 = _CommitTrackSession()
        s2 = _CommitTrackSession()
        tx.add_session(s1)
        tx.add_session(s2)
        assert tx.sessions == [s1, s2]

    def test_add_cache(self) -> None:
        tx = Transaction()
        c1 = ConcreteCache()
        c2 = ConcreteCache()
        tx.add_cache(c1)
        tx.add_cache(c2)
        assert tx.caches == [c1, c2]

    def test_add_logger(self) -> None:
        tx = Transaction()
        l1 = port_stub(Logger)()
        l2 = port_stub(Logger)()
        tx.add_logger(l1)
        tx.add_logger(l2)
        assert tx.loggers == [l1, l2]

    def test_add_event_bus(self) -> None:
        tx = Transaction()
        b1 = port_stub(EventBus)()
        b2 = port_stub(EventBus)()
        tx.add_event_bus(b1)
        tx.add_event_bus(b2)
        assert tx.event_buses == [b1, b2]

    def test_get_events_initial(self) -> None:
        tx = Transaction()
        assert tx.get_events() == []


class TestTransactionRunBasic:
    def test_run_basic_function(self) -> None:
        tx = Transaction()
        result = _run(tx, lambda a, b: a + b, 3, 4)
        assert result == 7

    def test_run_with_no_args(self) -> None:
        tx = Transaction()
        result = _run(tx, lambda: 42)
        assert result == 42

    def test_run_with_none_result(self) -> None:
        tx = Transaction()
        result = _run(tx, lambda: None)
        assert result is None

    def test_run_with_keyword_args(self) -> None:
        tx = Transaction()

        def fn(a: int, b: int) -> int:
            return a * b

        result = _run(tx, fn, 5, b=6)
        assert result == 30


class TestTransactionEvents:
    def test_collects_no_events(self) -> None:
        tx = Transaction()
        _run(tx, lambda: None)
        assert tx.get_events() == []

    def test_collects_events_via_event_emitter(self) -> None:
        tx = Transaction()

        def emit() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(SampleEvent(value="hello"))

        _run(tx, emit)
        events = tx.get_events()
        assert len(events) == 1
        assert isinstance(events[0], SampleEvent)
        assert events[0].value == "hello"

    def test_collects_events_even_on_failure(self) -> None:
        tx = Transaction()

        def emit_then_fail() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(SampleEvent(value="before_fail"))
            msg = "boom"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="boom"):
            _run(tx, emit_then_fail)
        events = tx.get_events()
        assert len(events) == 1
        assert events[0].value == "before_fail"

    def test_collects_only_events_during_run(self) -> None:
        tx = Transaction()

        def emit_two() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(SampleEvent(value="first"))
            ee.emit(SampleEvent(value="second"))

        _run(tx, emit_two)
        assert len(tx.get_events()) == 2

    def test_events_include_integration_events(self) -> None:
        tx = Transaction()

        def emit() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(IntegrationSampleEvent(value="cross"))

        _run(tx, emit)
        assert len(tx.get_events()) == 1
        assert isinstance(tx.get_events()[0], IntegrationSampleEvent)

    def test_new_run_replaces_previous_events(self) -> None:
        tx = Transaction()

        def emit_first() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(SampleEvent(value="first"))

        def emit_second() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(SampleEvent(value="second"))

        _run(tx, emit_first)
        assert len(tx.get_events()) == 1
        assert tx.get_events()[0].value == "first"
        _run(tx, emit_second)
        assert len(tx.get_events()) == 1
        assert tx.get_events()[0].value == "second"


class TestTransactionSessionLifecycle:
    def test_begin_called_on_dirty_sessions(self) -> None:
        s = _CommitTrackSession()
        tx = Transaction(sessions=[s])
        _run(tx, lambda: None)
        assert s._begun

    def test_commit_called_on_dirty_sessions(self) -> None:
        s = _CommitTrackSession()
        tx = Transaction(sessions=[s])
        _run(tx, lambda: None)
        assert s._committed

    def test_begin_not_called_on_read_only(self) -> None:
        s = _CommitTrackSession()
        tx = Transaction(sessions=[s], only_read=True)
        _run(tx, lambda: None)
        assert not s._begun

    def test_commit_not_called_on_read_only(self) -> None:
        s = _CommitTrackSession()
        tx = Transaction(sessions=[s], only_read=True)
        _run(tx, lambda: None)
        assert not s._committed

    def test_skip_commit_on_clean_session(self) -> None:
        s = _CleanSession()
        tx = Transaction(sessions=[s])
        _run(tx, lambda: None)

    def test_rollback_on_failure(self) -> None:
        s = _CommitTrackSession()
        tx = Transaction(sessions=[s])

        def fail() -> None:
            msg = "oops"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="oops"):
            _run(tx, fail)
        assert s._rolled_back
        assert not s._committed

    def test_rollback_on_commit_failure(self) -> None:
        class _FailCommitSession(_CommitTrackSession):
            def commit(self) -> None:
                raise RuntimeError("commit fail")

        s = _FailCommitSession()
        logger = port_stub(Logger)()
        tx = Transaction(sessions=[s], loggers=[logger])
        with pytest.raises(RuntimeError, match="commit fail"):
            _run(tx, lambda: None)
        assert s._rolled_back

    def test_rollback_skips_clean_sessions(self) -> None:
        s = _CleanSession()
        tx = Transaction(sessions=[s])

        def fail() -> None:
            msg = "oops"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="oops"):
            _run(tx, fail)

    def test_multiple_sessions_all_begin(self) -> None:
        s1 = _CommitTrackSession()
        s2 = _CommitTrackSession()
        tx = Transaction(sessions=[s1, s2])
        _run(tx, lambda: None)
        assert s1._begun
        assert s2._begun

    def test_multiple_sessions_all_commit(self) -> None:
        s1 = _CommitTrackSession()
        s2 = _CommitTrackSession()
        tx = Transaction(sessions=[s1, s2])
        _run(tx, lambda: None)
        assert s1._committed
        assert s2._committed

    def test_multiple_sessions_all_rollback_on_failure(self) -> None:
        s1 = _CommitTrackSession()
        s2 = _CommitTrackSession()
        tx = Transaction(sessions=[s1, s2])

        def fail() -> None:
            msg = "oops"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="oops"):
            _run(tx, fail)
        assert s1._rolled_back
        assert s2._rolled_back

    def test_session_begin_called_before_events(self) -> None:
        order: list[str] = []

        class _OrderSession(Session):
            def is_dirty(self) -> bool:
                return True

            def begin(self) -> None:
                order.append("begin")

            def commit(self) -> None:
                order.append("commit")

            def rollback(self) -> None:
                order.append("rollback")

            def close(self) -> None:
                pass

            def execute(self, operation: object) -> object:
                return operation

            def query(self, operation: object) -> object:
                return operation

        s = _OrderSession()
        tx = Transaction(sessions=[s])

        def emit() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(SampleEvent(value="test"))
            order.append("fn")

        _run(tx, emit)
        assert order == ["begin", "fn", "commit"]

    def test_commit_context_active_during_fn(self) -> None:
        s = _CommitTrackSession()
        tx = Transaction(sessions=[s])
        checked: list[bool] = []

        def check_context() -> None:
            checked.append(_CommitContext.get(False))

        _run(tx, check_context)
        assert checked == [True]

    def test_commit_context_inactive_during_read_only_fn(self) -> None:
        s = _CommitTrackSession()
        tx = Transaction(sessions=[s], only_read=True)
        checked: list[bool] = []

        def check_context() -> None:
            checked.append(_CommitContext.get(False))

        _run(tx, check_context)
        assert checked == [False]

    def test_commit_context_reset_after_fn(self) -> None:
        assert _CommitContext.get(False) is False
        s = _CommitTrackSession()
        tx = Transaction(sessions=[s])
        _run(tx, lambda: None)
        assert _CommitContext.get(False) is False

    def test_commit_context_reset_after_failure(self) -> None:
        assert _CommitContext.get(False) is False
        s = _CommitTrackSession()
        tx = Transaction(sessions=[s])

        def fail() -> None:
            msg = "oops"
            raise ValueError(msg)

        with pytest.raises(ValueError):
            _run(tx, fail)
        assert _CommitContext.get(False) is False

    def test_user_can_commit_inside_fn(self) -> None:
        s = _CommitTrackSession()
        tx = Transaction(sessions=[s])

        def user_commit() -> None:
            s.commit()

        _run(tx, user_commit)
        assert s._committed

    def test_user_commit_inside_then_tx_commits_dirty(self) -> None:
        call_count: list[int] = [0]

        class _CountCommitsSession(_CommitTrackSession):
            def commit(self) -> None:
                call_count[0] += 1
                super().commit()

        s = _CountCommitsSession()

        def user_commit() -> None:
            s.commit()

        tx = Transaction(sessions=[s])
        _run(tx, user_commit)
        assert call_count[0] == 2


class TestTransactionCaches:
    def test_flush_caches_on_success(self) -> None:
        from aod._internal.application.cache.cache import _CacheEntry

        cache = ConcreteCache()
        object.__setattr__(cache, "_to_set", [_CacheEntry("k", "v")])
        assert len(cache._to_set) == 1

        tx = Transaction(caches=[cache])
        _run(tx, lambda: None)
        assert len(cache._to_set) == 0

    def test_discard_on_failure(self) -> None:
        from aod._internal.application.cache.cache import _CacheEntry

        cache = ConcreteCache()
        object.__setattr__(cache, "_to_set", [_CacheEntry("k", "v")])
        object.__setattr__(cache, "_to_delete", ["k"])
        tx = Transaction(caches=[cache])

        def fail() -> None:
            msg = "oops"
            raise ValueError(msg)

        with pytest.raises(ValueError):
            _run(tx, fail)
        assert cache._to_set == []
        assert cache._to_delete == []

    def test_flush_skipped_on_read_only(self) -> None:
        from aod._internal.application.cache.cache import _CacheEntry

        cache = ConcreteCache()
        object.__setattr__(cache, "_to_set", [_CacheEntry("k", "v")])
        tx = Transaction(caches=[cache], only_read=True)
        _run(tx, lambda: None)
        assert len(cache._to_set) == 1

    def test_discard_on_commit_failure(self) -> None:
        cache = ConcreteCache()
        cache._to_set.append(_CacheEntry("k", "v", None))

        class _FailCommitSession(_CommitTrackSession):
            def commit(self) -> None:
                raise RuntimeError("commit fail")

        s = _FailCommitSession()
        logger = port_stub(Logger)()
        tx = Transaction(sessions=[s], caches=[cache], loggers=[logger])
        with pytest.raises(RuntimeError):
            _run(tx, lambda: None)
        assert cache._to_set == []


class TestTransactionLogging:
    def test_logs_completion_on_success(self) -> None:
        logger = port_stub(Logger)()
        tx = Transaction(loggers=[logger], operation_name="TestOp")
        _run(tx, lambda: None)
        completions = [c for c in logger.info.call_args_list if "completed" in str(c.args[0])]
        assert len(completions) == 1
        assert "TestOp" in str(completions[0].args[0])

    def test_logs_events_on_success(self) -> None:
        logger = port_stub(Logger)()
        tx = Transaction(loggers=[logger], operation_name="TestOp")

        def emit() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(SampleEvent(value="test"))

        _run(tx, emit)
        events_logs = [c for c in logger.info.call_args_list if "events" in str(c.args[0])]
        assert len(events_logs) >= 1
        evts = events_logs[0].kwargs.get("events")
        assert evts is not None
        assert len(evts) == 1

    def test_logs_error_on_failure(self) -> None:
        logger = port_stub(Logger)()
        tx = Transaction(loggers=[logger], operation_name="TestOp")

        def fail() -> None:
            msg = "oops"
            raise ValueError(msg)

        with pytest.raises(ValueError):
            _run(tx, fail)
        errors = [c for c in logger.error.call_args_list if "failed" in str(c.args[0])]
        assert len(errors) >= 1

    def test_logs_error_on_commit_failure(self) -> None:
        class _FailCommitSession(_CommitTrackSession):
            def commit(self) -> None:
                raise RuntimeError("commit fail")

        logger = port_stub(Logger)()
        s = _FailCommitSession()
        tx = Transaction(sessions=[s], loggers=[logger], operation_name="TestOp")
        with pytest.raises(RuntimeError):
            _run(tx, lambda: None)
        errors = [c for c in logger.error.call_args_list if "failed" in str(c.args[0])]
        assert len(errors) >= 1

    def test_multiple_loggers_all_called(self) -> None:
        l1 = port_stub(Logger)()
        l2 = port_stub(Logger)()
        tx = Transaction(loggers=[l1, l2], operation_name="Test")
        _run(tx, lambda: None)
        assert l1.info.call_count >= 2
        assert l2.info.call_count >= 2


class TestTransactionEventBus:
    def test_publishes_on_success(self) -> None:
        bus = port_stub(EventBus)()
        tx = Transaction(event_buses=[bus])

        def emit() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(SampleEvent(value="test"))

        _run(tx, emit)
        assert bus.publish.call_count == 1

    def test_does_not_publish_on_failure(self) -> None:
        bus = port_stub(EventBus)()
        tx = Transaction(event_buses=[bus])

        def fail() -> None:
            msg = "oops"
            raise ValueError(msg)

        with pytest.raises(ValueError):
            _run(tx, fail)
        assert bus.publish.call_count == 0

    def test_multiple_buses_all_publish(self) -> None:
        b1 = port_stub(EventBus)()
        b2 = port_stub(EventBus)()
        tx = Transaction(event_buses=[b1, b2])

        def emit() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(SampleEvent(value="test"))

        _run(tx, emit)
        assert b1.publish.call_count == 1
        assert b2.publish.call_count == 1

    def test_publishes_correct_events(self) -> None:
        bus = port_stub(EventBus)()
        tx = Transaction(event_buses=[bus])

        def emit() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(SampleEvent(value="published"))

        _run(tx, emit)
        call = bus.publish.call_args
        assert call is not None
        published_events = call[0]
        assert len(published_events) == 1
        assert published_events[0].value == "published"


class TestTransactionExceptionHandling:
    def test_raises_original_exception(self) -> None:
        tx = Transaction()

        def fail() -> None:
            msg = "custom error"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="custom error"):
            _run(tx, fail)

    def test_raises_commit_exception(self) -> None:
        class _FailCommitSession(_CommitTrackSession):
            def commit(self) -> None:
                raise RuntimeError("commit failure")

        s = _FailCommitSession()
        tx = Transaction(sessions=[s])
        with pytest.raises(RuntimeError, match="commit failure"):
            _run(tx, lambda: None)

    def test_keyboard_interrupt_propagates(self) -> None:
        tx = Transaction()

        def interrupt() -> None:
            raise KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            _run(tx, interrupt)

    def test_system_exit_propagates(self) -> None:
        tx = Transaction()

        def exit_func() -> None:
            raise SystemExit(1)

        with pytest.raises(SystemExit):
            _run(tx, exit_func)


class TestTransactionOnlyRead:
    def test_no_begin_no_commit_on_read(self) -> None:
        s = _CommitTrackSession()
        tx = Transaction(sessions=[s], only_read=True)
        _run(tx, lambda: None)
        assert not s._begun
        assert not s._committed

    def test_no_rollback_on_read_failure(self) -> None:
        s = _CommitTrackSession()
        tx = Transaction(sessions=[s], only_read=True)

        def fail() -> None:
            msg = "oops"
            raise ValueError(msg)

        with pytest.raises(ValueError):
            _run(tx, fail)
        assert not s._rolled_back

    def test_still_collects_events_on_read(self) -> None:
        tx = Transaction(only_read=True)

        def emit() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(SampleEvent(value="read_event"))

        _run(tx, emit)
        assert len(tx.get_events()) == 1

    def test_still_logs_on_read(self) -> None:
        logger = port_stub(Logger)()
        tx = Transaction(loggers=[logger], operation_name="ReadOp", only_read=True)
        _run(tx, lambda: None)
        completions = [c for c in logger.info.call_args_list if "completed" in str(c.args[0])]
        assert len(completions) == 1

    def test_still_publishes_on_read(self) -> None:
        bus = port_stub(EventBus)()
        tx = Transaction(event_buses=[bus], only_read=True)

        def emit() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(SampleEvent(value="read_pub"))

        _run(tx, emit)
        assert bus.publish.call_count == 1


class TestTransactionEdgeCases:
    def test_no_sessions_no_caches_no_loggers_no_buses(self) -> None:
        tx = Transaction()
        result = _run(tx, lambda: 99)
        assert result == 99

    def test_no_sessions_on_failure_still_raises(self) -> None:
        tx = Transaction()

        def fail() -> None:
            msg = "oops"
            raise ValueError(msg)

        with pytest.raises(ValueError):
            _run(tx, fail)

    def test_empty_sessions_does_not_crash(self) -> None:
        tx = Transaction(sessions=[])
        _run(tx, lambda: None)

    def test_empty_caches_does_not_crash(self) -> None:
        tx = Transaction(caches=[])
        _run(tx, lambda: None)

    def test_empty_loggers_does_not_crash(self) -> None:
        tx = Transaction(loggers=[])
        _run(tx, lambda: None)

    def test_empty_event_buses_does_not_crash(self) -> None:
        tx = Transaction(event_buses=[])
        _run(tx, lambda: None)

    def test_handler_function_with_args(self) -> None:
        tx = Transaction()

        def greet(name: str) -> str:
            return f"Hello, {name}"

        result = _run(tx, greet, "World")
        assert result == "Hello, World"

    def test_handler_function_with_kwargs(self) -> None:
        tx = Transaction()

        def greet(greeting: str, name: str) -> str:
            return f"{greeting}, {name}"

        result = _run(tx, greet, greeting="Hi", name="Alice")
        assert result == "Hi, Alice"


class TestAsyncTransactionConstruction:
    async def test_default_construction(self) -> None:
        tx = AsyncTransaction()
        assert tx.sessions == []
        assert tx.caches == []
        assert tx.loggers == []
        assert tx.event_buses == []
        assert tx.operation_name == ""
        assert tx.only_read is False

    async def test_custom_construction(self) -> None:
        session = _CommitTrackAsyncSession()
        cache = ConcreteCache()
        logger = port_stub(Logger)()
        bus = port_stub(EventBus)()
        tx = AsyncTransaction(
            sessions=[session],
            caches=[cache],
            loggers=[logger],
            event_buses=[bus],
            operation_name="test",
            only_read=True,
        )
        assert tx.sessions == [session]
        assert tx.caches == [cache]
        assert tx.loggers == [logger]
        assert tx.event_buses == [bus]
        assert tx.operation_name == "test"
        assert tx.only_read is True


class TestAsyncTransactionRunBasic:
    async def test_run_basic_function(self) -> None:
        tx = AsyncTransaction()
        result = await _run_async(tx, lambda a, b: a + b, 3, 4)
        assert result == 7

    async def test_run_async_function(self) -> None:
        tx = AsyncTransaction()

        async def async_add(a: int, b: int) -> int:
            return a + b

        result = await _run_async(tx, async_add, 3, 4)
        assert result == 7

    async def test_run_with_no_args(self) -> None:
        tx = AsyncTransaction()
        result = await _run_async(tx, lambda: 42)
        assert result == 42

    async def test_run_with_none_result(self) -> None:
        tx = AsyncTransaction()
        result = await _run_async(tx, lambda: None)
        assert result is None

    async def test_run_with_keyword_args(self) -> None:
        tx = AsyncTransaction()

        def fn(a: int, b: int) -> int:
            return a * b

        result = await _run_async(tx, fn, 5, b=6)
        assert result == 30


class TestAsyncTransactionEvents:
    async def test_collects_no_events(self) -> None:
        tx = AsyncTransaction()
        await _run_async(tx, lambda: None)
        assert tx.get_events() == []

    async def test_collects_events(self) -> None:
        tx = AsyncTransaction()

        def emit() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(SampleEvent(value="async_event"))

        await _run_async(tx, emit)
        assert len(tx.get_events()) == 1
        assert tx.get_events()[0].value == "async_event"

    async def test_collects_events_even_on_failure(self) -> None:
        tx = AsyncTransaction()

        def emit_then_fail() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(SampleEvent(value="before_fail"))
            msg = "boom"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="boom"):
            await _run_async(tx, emit_then_fail)
        assert len(tx.get_events()) == 1


class TestAsyncTransactionSessionLifecycle:
    async def test_begin_called_on_dirty_sessions(self) -> None:
        s = _CommitTrackAsyncSession()
        tx = AsyncTransaction(sessions=[s])
        await _run_async(tx, lambda: None)
        assert s._begun

    async def test_commit_called_on_dirty(self) -> None:
        s = _CommitTrackAsyncSession()
        tx = AsyncTransaction(sessions=[s])
        await _run_async(tx, lambda: None)
        assert s._committed

    async def test_begin_not_called_on_read_only(self) -> None:
        s = _CommitTrackAsyncSession()
        tx = AsyncTransaction(sessions=[s], only_read=True)
        await _run_async(tx, lambda: None)
        assert not s._begun

    async def test_commit_not_called_on_read_only(self) -> None:
        s = _CommitTrackAsyncSession()
        tx = AsyncTransaction(sessions=[s], only_read=True)
        await _run_async(tx, lambda: None)
        assert not s._committed

    async def test_skip_commit_on_clean_session(self) -> None:
        s = _CleanAsyncSession()
        tx = AsyncTransaction(sessions=[s])
        await _run_async(tx, lambda: None)

    async def test_rollback_on_failure(self) -> None:
        s = _CommitTrackAsyncSession()
        tx = AsyncTransaction(sessions=[s])

        def fail() -> None:
            msg = "oops"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="oops"):
            await _run_async(tx, fail)
        assert s._rolled_back
        assert not s._committed

    async def test_rollback_on_commit_failure(self) -> None:
        class _FailCommitSession(_CommitTrackAsyncSession):
            async def commit(self) -> None:
                raise RuntimeError("commit fail")

        s = _FailCommitSession()
        logger = port_stub(Logger)()
        tx = AsyncTransaction(sessions=[s], loggers=[logger])
        with pytest.raises(RuntimeError, match="commit fail"):
            await _run_async(tx, lambda: None)
        assert s._rolled_back

    async def test_rollback_skips_clean(self) -> None:
        s = _CleanAsyncSession()
        tx = AsyncTransaction(sessions=[s])

        def fail() -> None:
            msg = "oops"
            raise ValueError(msg)

        with pytest.raises(ValueError):
            await _run_async(tx, fail)

    async def test_multiple_sessions(self) -> None:
        s1 = _CommitTrackAsyncSession()
        s2 = _CommitTrackAsyncSession()
        tx = AsyncTransaction(sessions=[s1, s2])
        await _run_async(tx, lambda: None)
        assert s1._begun
        assert s2._begun
        assert s1._committed
        assert s2._committed

    async def test_commit_context_active_during_fn(self) -> None:
        s = _CommitTrackAsyncSession()
        tx = AsyncTransaction(sessions=[s])
        checked: list[bool] = []

        def check_context() -> None:
            checked.append(_CommitContext.get(False))

        await _run_async(tx, check_context)
        assert checked == [True]

    async def test_commit_context_inactive_during_read_only(self) -> None:
        s = _CommitTrackAsyncSession()
        tx = AsyncTransaction(sessions=[s], only_read=True)
        checked: list[bool] = []

        def check_context() -> None:
            checked.append(_CommitContext.get(False))

        await _run_async(tx, check_context)
        assert checked == [False]

    async def test_commit_context_reset_after_fn(self) -> None:
        assert _CommitContext.get(False) is False
        s = _CommitTrackAsyncSession()
        tx = AsyncTransaction(sessions=[s])
        await _run_async(tx, lambda: None)
        assert _CommitContext.get(False) is False

    async def test_commit_context_reset_after_failure(self) -> None:
        assert _CommitContext.get(False) is False
        s = _CommitTrackAsyncSession()
        tx = AsyncTransaction(sessions=[s])

        def fail() -> None:
            msg = "oops"
            raise ValueError(msg)

        with pytest.raises(ValueError):
            await _run_async(tx, fail)
        assert _CommitContext.get(False) is False


class TestAsyncTransactionCaches:
    async def test_flush_on_success(self) -> None:
        from aod._internal.application.cache.cache import _CacheEntry

        cache = ConcreteCache()
        object.__setattr__(cache, "_to_set", [_CacheEntry("k", "v")])
        tx = AsyncTransaction(caches=[cache])
        await _run_async(tx, lambda: None)
        assert len(cache._to_set) == 0

    async def test_discard_on_failure(self) -> None:
        cache = ConcreteCache()
        cache._to_set.append(_CacheEntry("k", "v", None))
        cache._to_delete.append("dummy")
        tx = AsyncTransaction(caches=[cache])

        def fail() -> None:
            msg = "oops"
            raise ValueError(msg)

        with pytest.raises(ValueError):
            await _run_async(tx, fail)
        assert cache._to_set == []
        assert cache._to_delete == []


class TestAsyncTransactionLogging:
    async def test_logs_completion_on_success(self) -> None:
        logger = port_stub(Logger)()
        tx = AsyncTransaction(loggers=[logger], operation_name="AsyncOp")
        await _run_async(tx, lambda: None)
        completions = [c for c in logger.info.call_args_list if "completed" in str(c.args[0])]
        assert len(completions) >= 1

    async def test_logs_error_on_failure(self) -> None:
        logger = port_stub(Logger)()
        tx = AsyncTransaction(loggers=[logger], operation_name="AsyncOp")

        def fail() -> None:
            msg = "oops"
            raise ValueError(msg)

        with pytest.raises(ValueError):
            await _run_async(tx, fail)
        errors = [c for c in logger.error.call_args_list if "failed" in str(c.args[0])]
        assert len(errors) >= 1


class TestAsyncTransactionEventBus:
    async def test_publishes_on_success(self) -> None:
        bus = port_stub(EventBus)()
        tx = AsyncTransaction(event_buses=[bus])

        def emit() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(SampleEvent(value="test"))

        await _run_async(tx, emit)
        assert bus.publish.call_count == 1

    async def test_does_not_publish_on_failure(self) -> None:
        bus = port_stub(EventBus)()
        tx = AsyncTransaction(event_buses=[bus])

        def fail() -> None:
            msg = "oops"
            raise ValueError(msg)

        with pytest.raises(ValueError):
            await _run_async(tx, fail)
        assert bus.publish.call_count == 0


class TestAsyncTransactionExceptionHandling:
    async def test_raises_original(self) -> None:
        tx = AsyncTransaction()

        def fail() -> None:
            msg = "custom error"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="custom error"):
            await _run_async(tx, fail)

    async def test_raises_commit_exception(self) -> None:
        class _FailCommitSession(_CommitTrackAsyncSession):
            async def commit(self) -> None:
                raise RuntimeError("commit failure")

        s = _FailCommitSession()
        tx = AsyncTransaction(sessions=[s])
        with pytest.raises(RuntimeError, match="commit failure"):
            await _run_async(tx, lambda: None)

    async def test_keyboard_interrupt_propagates(self) -> None:
        tx = AsyncTransaction()

        def interrupt() -> None:
            raise KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            await _run_async(tx, interrupt)


class TestAsyncTransactionOnlyRead:
    async def test_no_begin_no_commit_on_read(self) -> None:
        s = _CommitTrackAsyncSession()
        tx = AsyncTransaction(sessions=[s], only_read=True)
        await _run_async(tx, lambda: None)
        assert not s._begun
        assert not s._committed

    async def test_still_collects_events_on_read(self) -> None:
        tx = AsyncTransaction(only_read=True)

        def emit() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(SampleEvent(value="read_event"))

        await _run_async(tx, emit)
        assert len(tx.get_events()) == 1

    async def test_still_logs_on_read(self) -> None:
        logger = port_stub(Logger)()
        tx = AsyncTransaction(loggers=[logger], operation_name="ReadOp", only_read=True)
        await _run_async(tx, lambda: None)
        completions = [c for c in logger.info.call_args_list if "completed" in str(c.args[0])]
        assert len(completions) >= 1

    async def test_still_publishes_on_read(self) -> None:
        bus = port_stub(EventBus)()
        tx = AsyncTransaction(event_buses=[bus], only_read=True)

        def emit() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(SampleEvent(value="read_pub"))

        await _run_async(tx, emit)
        assert bus.publish.call_count == 1


class TestAsyncTransactionEdgeCases:
    async def test_no_resources(self) -> None:
        tx = AsyncTransaction()
        result = await _run_async(tx, lambda: 99)
        assert result == 99

    async def test_async_function_called(self) -> None:
        tx = AsyncTransaction()

        async def fetch() -> str:
            return "data"

        result = await _run_async(tx, fetch)
        assert result == "data"

    async def test_sync_function_in_async_transaction(self) -> None:
        tx = AsyncTransaction()
        result = await _run_async(tx, lambda: "sync_result")
        assert result == "sync_result"

    async def test_mixed_sync_sessions(self) -> None:
        s = _CommitTrackSession()
        tx = AsyncTransaction(sessions=[s])
        await _run_async(tx, lambda: None)
        assert s._begun
        assert s._committed

    async def test_mixed_sync_logger(self) -> None:
        logger = port_stub(Logger)()
        tx = AsyncTransaction(loggers=[logger], operation_name="AsyncOp")
        await _run_async(tx, lambda: None)
        assert logger.info.call_count >= 2

    async def test_mixed_sync_event_bus(self) -> None:
        bus = port_stub(EventBus)()
        tx = AsyncTransaction(event_buses=[bus])

        def emit() -> None:
            from aod._internal.core.event_emitter import EventEmitter

            ee = EventEmitter()
            ee.emit(SampleEvent(value="sync_bus"))

        await _run_async(tx, emit)
        assert bus.publish.call_count == 1
