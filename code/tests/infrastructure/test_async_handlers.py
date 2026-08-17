from __future__ import annotations

import pytest
from typing import cast
from aod._internal.core.fields.fields import Field
from aod._internal.domain.entity import RootEntity
from aod._internal.application.transaction import AsyncTransaction
from aod._internal.core.fields.fields import PrivateField
from aod._internal.infrastructure.session import AsyncSession
from aod.application import Command, Query
from aod.infrastructure.async_ import CommandHandler, QueryHandler


class User(RootEntity):
    id: int = Field(id=True)
    name: str


class CreateUser(Command[User, User]):
    name: str


class GetUser(Query[User, User | None]):
    user_id: int


class CreateUserHandler(CommandHandler[CreateUser]):
    async def handle(self, command: CreateUser) -> User:
        return User(id=1, name=command.name)


class GetUserHandler(QueryHandler[GetUser]):
    async def handle(self, query: GetUser) -> User | None:
        if query.user_id == 1:
            return User(id=1, name="Alice")
        return None


class _AsyncSession(AsyncSession):
    _begun: bool = PrivateField(default=False)

    async def begin(self) -> None:
        self._begun = True

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def close(self) -> None:
        pass

    def is_dirty(self) -> bool:
        return False

    async def query(self, operation: object) -> object:
        return operation


class SessionAwareGetUserHandler(QueryHandler[GetUser]):
    session: _AsyncSession

    async def handle(self, query: GetUser) -> GetUser:
        return cast(GetUser, await self.session.query(query))


async def test_is_abstract() -> None:
    with pytest.raises(TypeError):
        CommandHandler[CreateUser]()


async def test_without_handle_is_abstract() -> None:
    class Incomplete(CommandHandler[CreateUser]):
        pass

    with pytest.raises(TypeError):
        Incomplete()


async def test_concrete_handler_works() -> None:
    h = CreateUserHandler()
    cmd = CreateUser(name="Alice")
    result = await h.handle(cmd)
    assert isinstance(result, User)
    assert result.name == "Alice"


async def test_query_handler_works() -> None:
    h = GetUserHandler()
    result = await h.handle(GetUser(user_id=1))
    assert result is not None
    assert result.name == "Alice"


async def test_query_handler_returns_none() -> None:
    h = GetUserHandler()
    result = await h.handle(GetUser(user_id=999))
    assert result is None


@pytest.mark.asyncio
async def test_async_handlers_register_a_shared_session_once_per_transaction() -> None:
    session = _AsyncSession()
    first = SessionAwareGetUserHandler(session=session)
    second = SessionAwareGetUserHandler(session=session)

    async with AsyncTransaction() as transaction:
        assert transaction.sessions == []

        await first.handle(GetUser(user_id=1))
        assert transaction.sessions == [session]
        assert session._is_begun

        await second.handle(GetUser(user_id=2))
        assert transaction.sessions == [session]
