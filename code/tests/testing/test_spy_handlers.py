from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest
from aod._internal.application.handler import (
    AsyncCommandPort,
    AsyncQueryPort,
    CommandPort,
    QueryPort,
)
from aod.application import Command, Query, UseCase
from aod.application.async_ import UseCase as AsyncUseCase
from aod.domain import Field, RootEntity
from aod.testing.doubles import (
    spy_async_command_handler,
    spy_async_query_handler,
    spy_command_handler,
    spy_query_handler,
)


class User(RootEntity):
    id: int = Field(id=True)
    name: str


class CreateUser(Command[User, User]):
    name: str


class GetUser(Query[User, User | None]):
    user_id: int


class TestSpyCommandHandler:
    def test_returns_command_port_instance(self) -> None:
        spy = spy_command_handler()
        assert isinstance(spy.handle, MagicMock)

    def test_handle_returns_none_by_default(self) -> None:
        spy = spy_command_handler()
        cmd = CreateUser(name="Alice")
        assert spy.handle(cmd) is None

    def test_handle_called_property(self) -> None:
        spy = spy_command_handler()
        assert not spy.handle.called
        spy.handle(CreateUser(name="Alice"))
        assert spy.handle.called

    def test_handle_tracks_calls(self) -> None:
        spy = spy_command_handler()
        cmd1 = CreateUser(name="Alice")
        cmd2 = CreateUser(name="Bob")
        spy.handle(cmd1)
        spy.handle(cmd2)
        assert spy.handle.call_count == 2
        assert spy.handle.call_args_list[0].args[0] == cmd1
        assert spy.handle.call_args_list[1].args[0] == cmd2

    def test_returns_parameter(self) -> None:
        user = User(id=1, name="Alice")
        spy = spy_command_handler(returns=user)
        result = spy.handle(CreateUser(name="Alice"))
        assert result is user

    def test_raises_parameter(self) -> None:
        error = ValueError("test error")
        spy = spy_command_handler(raises=error)
        with pytest.raises(ValueError, match="test error"):
            spy.handle(CreateUser(name="Alice"))

    def test_each_call_creates_independent_instance(self) -> None:
        spy1 = spy_command_handler()
        spy2 = spy_command_handler()
        assert spy1.handle is not spy2.handle
        spy1.handle(CreateUser(name="Alice"))
        assert spy1.handle.call_count == 1
        assert spy2.handle.call_count == 0


class TestSpyQueryHandler:
    def test_returns_query_port_instance(self) -> None:
        spy = spy_query_handler()
        assert isinstance(spy.handle, MagicMock)

    def test_handle_returns_none_by_default(self) -> None:
        spy = spy_query_handler()
        assert spy.handle(GetUser(user_id=1)) is None

    def test_handle_called_property(self) -> None:
        spy = spy_query_handler()
        assert not spy.handle.called
        spy.handle(GetUser(user_id=1))
        assert spy.handle.called

    def test_handle_tracks_calls(self) -> None:
        spy = spy_query_handler()
        q1 = GetUser(user_id=1)
        q2 = GetUser(user_id=2)
        spy.handle(q1)
        spy.handle(q2)
        assert spy.handle.call_count == 2
        assert spy.handle.call_args_list[0].args[0] == q1
        assert spy.handle.call_args_list[1].args[0] == q2

    def test_returns_parameter(self) -> None:
        user = User(id=1, name="Alice")
        spy = spy_query_handler(returns=user)
        result = spy.handle(GetUser(user_id=1))
        assert result is user

    def test_raises_parameter(self) -> None:
        error = RuntimeError("query error")
        spy = spy_query_handler(raises=error)
        with pytest.raises(RuntimeError, match="query error"):
            spy.handle(GetUser(user_id=1))

    def test_each_call_creates_independent_instance(self) -> None:
        spy1 = spy_query_handler()
        spy2 = spy_query_handler()
        assert spy1.handle is not spy2.handle
        spy1.handle(GetUser(user_id=1))
        assert spy1.handle.call_count == 1
        assert spy2.handle.call_count == 0


class TestSpyAsyncCommandHandler:
    def test_handle_is_async_mock(self) -> None:
        spy = spy_async_command_handler()
        assert isinstance(spy.handle, AsyncMock)

    def test_handle_is_coroutine_function(self) -> None:
        spy = spy_async_command_handler()
        assert inspect.iscoroutinefunction(spy.handle)

    async def test_handle_returns_none_by_default(self) -> None:
        spy = spy_async_command_handler()
        cmd = CreateUser(name="Alice")
        result = await spy.handle(cmd)
        assert result is None

    async def test_handle_called_property(self) -> None:
        spy = spy_async_command_handler()
        assert not spy.handle.called
        await spy.handle(CreateUser(name="Alice"))
        assert spy.handle.called

    async def test_handle_tracks_calls(self) -> None:
        spy = spy_async_command_handler()
        cmd1 = CreateUser(name="Alice")
        cmd2 = CreateUser(name="Bob")
        await spy.handle(cmd1)
        await spy.handle(cmd2)
        assert spy.handle.call_count == 2
        assert spy.handle.call_args_list[0].args[0] == cmd1
        assert spy.handle.call_args_list[1].args[0] == cmd2

    async def test_returns_parameter(self) -> None:
        user = User(id=1, name="Alice")
        spy = spy_async_command_handler(returns=user)
        result = await spy.handle(CreateUser(name="Alice"))
        assert result is user

    async def test_raises_parameter(self) -> None:
        error = ValueError("async error")
        spy = spy_async_command_handler(raises=error)
        with pytest.raises(ValueError, match="async error"):
            await spy.handle(CreateUser(name="Alice"))

    def test_each_call_creates_independent_instance(self) -> None:
        spy1 = spy_async_command_handler()
        spy2 = spy_async_command_handler()
        assert spy1.handle is not spy2.handle


class TestSpyAsyncQueryHandler:
    def test_handle_is_async_mock(self) -> None:
        spy = spy_async_query_handler()
        assert isinstance(spy.handle, AsyncMock)

    def test_handle_is_coroutine_function(self) -> None:
        spy = spy_async_query_handler()
        assert inspect.iscoroutinefunction(spy.handle)

    async def test_handle_returns_none_by_default(self) -> None:
        spy = spy_async_query_handler()
        result = await spy.handle(GetUser(user_id=1))
        assert result is None

    async def test_handle_called_property(self) -> None:
        spy = spy_async_query_handler()
        assert not spy.handle.called
        await spy.handle(GetUser(user_id=1))
        assert spy.handle.called

    async def test_handle_tracks_calls(self) -> None:
        spy = spy_async_query_handler()
        q1 = GetUser(user_id=1)
        q2 = GetUser(user_id=2)
        await spy.handle(q1)
        await spy.handle(q2)
        assert spy.handle.call_count == 2
        assert spy.handle.call_args_list[0].args[0] == q1
        assert spy.handle.call_args_list[1].args[0] == q2

    async def test_returns_parameter(self) -> None:
        user = User(id=1, name="Alice")
        spy = spy_async_query_handler(returns=user)
        result = await spy.handle(GetUser(user_id=1))
        assert result is user

    async def test_raises_parameter(self) -> None:
        error = RuntimeError("async query error")
        spy = spy_async_query_handler(raises=error)
        with pytest.raises(RuntimeError, match="async query error"):
            await spy.handle(GetUser(user_id=1))

    def test_each_call_creates_independent_instance(self) -> None:
        spy1 = spy_async_query_handler()
        spy2 = spy_async_query_handler()
        assert spy1.handle is not spy2.handle


class TestSpyCommandHandlerInUseCase:
    def test_handler_is_called(self) -> None:
        spy = spy_command_handler()

        class Create(UseCase):
            handler: CommandPort[CreateUser]

            def run(self, name: str) -> User:
                return self.handler.handle(CreateUser(name=name))

        uc = Create(handler=spy)
        result = uc.run(name="Alice")
        assert result is None
        assert spy.handle.call_count == 1
        captured = spy.handle.call_args_list[0].args[0]
        assert isinstance(captured, CreateUser)
        assert captured.name == "Alice"

    def test_handler_with_returns(self) -> None:
        user = User(id=1, name="Alice")
        spy = spy_command_handler(returns=user)

        class Create(UseCase):
            handler: CommandPort[CreateUser]

            def run(self, name: str) -> User:
                return self.handler.handle(CreateUser(name=name))

        uc = Create(handler=spy)
        result = uc.run(name="Alice")
        assert result is user
        assert spy.handle.call_count == 1

    def test_handler_with_raises(self) -> None:
        err = ValueError("unavailable")
        spy = spy_command_handler(raises=err)

        class Create(UseCase):
            handler: CommandPort[CreateUser]

            def run(self, name: str) -> User:
                return self.handler.handle(CreateUser(name=name))

        uc = Create(handler=spy)
        with pytest.raises(ValueError, match="unavailable"):
            uc.run(name="Alice")
        assert spy.handle.call_count == 1

    def test_multiple_handlers(self) -> None:
        user = User(id=1, name="Alice")
        save_spy = spy_command_handler(returns=user)
        notify_spy = spy_command_handler()

        class Create(UseCase):
            save: CommandPort[CreateUser]
            notify: CommandPort[CreateUser]

            def run(self, name: str) -> User:
                result = self.save.handle(CreateUser(name=name))
                self.notify.handle(CreateUser(name=name))
                return result

        uc = Create(save=save_spy, notify=notify_spy)
        result = uc.run(name="Alice")
        assert result is user
        assert save_spy.handle.call_count == 1
        assert notify_spy.handle.call_count == 1


class TestSpyQueryHandlerInUseCase:
    def test_handler_is_called(self) -> None:
        spy = spy_query_handler()

        class Get(UseCase):
            handler: QueryPort[GetUser]

            def run(self, user_id: int) -> User | None:
                return self.handler.handle(GetUser(user_id=user_id))

        uc = Get(handler=spy)
        result = uc.run(user_id=1)
        assert result is None
        assert spy.handle.call_count == 1
        captured = spy.handle.call_args_list[0].args[0]
        assert isinstance(captured, GetUser)
        assert captured.user_id == 1

    def test_handler_with_returns(self) -> None:
        user = User(id=1, name="Alice")
        spy = spy_query_handler(returns=user)

        class Get(UseCase):
            handler: QueryPort[GetUser]

            def run(self, user_id: int) -> User | None:
                return self.handler.handle(GetUser(user_id=user_id))

        uc = Get(handler=spy)
        result = uc.run(user_id=1)
        assert result is user
        assert spy.handle.call_count == 1

    def test_handler_returns_none(self) -> None:
        spy = spy_query_handler(returns=None)

        class Get(UseCase):
            handler: QueryPort[GetUser]

            def run(self, user_id: int) -> User | None:
                return self.handler.handle(GetUser(user_id=user_id))

        uc = Get(handler=spy)
        result = uc.run(user_id=1)
        assert result is None


class TestSpyAsyncCommandHandlerInUseCase:
    async def test_handler_is_called(self) -> None:
        spy = spy_async_command_handler()

        class Create(AsyncUseCase):
            handler: AsyncCommandPort[CreateUser]

            async def run(self, name: str) -> User:
                return await self.handler.handle(CreateUser(name=name))

        uc = Create(handler=spy)
        result = await uc.run(name="Alice")
        assert result is None
        assert spy.handle.call_count == 1

    async def test_handler_with_returns(self) -> None:
        user = User(id=1, name="Alice")
        spy = spy_async_command_handler(returns=user)

        class Create(AsyncUseCase):
            handler: AsyncCommandPort[CreateUser]

            async def run(self, name: str) -> User:
                return await self.handler.handle(CreateUser(name=name))

        uc = Create(handler=spy)
        result = await uc.run(name="Alice")
        assert result is user
        assert spy.handle.call_count == 1

    async def test_handler_with_raises(self) -> None:
        err = RuntimeError("unavailable")
        spy = spy_async_command_handler(raises=err)

        class Create(AsyncUseCase):
            handler: AsyncCommandPort[CreateUser]

            async def run(self, name: str) -> User:
                return await self.handler.handle(CreateUser(name=name))

        uc = Create(handler=spy)
        with pytest.raises(RuntimeError, match="unavailable"):
            await uc.run(name="Alice")
        assert spy.handle.call_count == 1


class TestSpyAsyncQueryHandlerInUseCase:
    async def test_handler_is_called(self) -> None:
        spy = spy_async_query_handler()

        class Get(AsyncUseCase):
            handler: AsyncQueryPort[GetUser]

            async def run(self, user_id: int) -> User | None:
                return await self.handler.handle(GetUser(user_id=user_id))

        uc = Get(handler=spy)
        result = await uc.run(user_id=1)
        assert result is None
        assert spy.handle.call_count == 1

    async def test_handler_with_returns(self) -> None:
        user = User(id=1, name="Alice")
        spy = spy_async_query_handler(returns=user)

        class Get(AsyncUseCase):
            handler: AsyncQueryPort[GetUser]

            async def run(self, user_id: int) -> User | None:
                return await self.handler.handle(GetUser(user_id=user_id))

        uc = Get(handler=spy)
        result = await uc.run(user_id=1)
        assert result is user
        assert spy.handle.call_count == 1

    async def test_handler_returns_none(self) -> None:
        spy = spy_async_query_handler(returns=None)

        class Get(AsyncUseCase):
            handler: AsyncQueryPort[GetUser]

            async def run(self, user_id: int) -> User | None:
                return await self.handler.handle(GetUser(user_id=user_id))

        uc = Get(handler=spy)
        result = await uc.run(user_id=1)
        assert result is None
