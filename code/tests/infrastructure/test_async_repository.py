from __future__ import annotations

import pytest
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import ApplicationException, DomainException
from aod._internal.domain.entity import RootEntity
from aod._internal.type_checks.handler_checks import (
    extract_handler_type,
    validate_handler_type,
)
from aod.application import Command, Query
from aod.infrastructure.handlers.async_ import CommandHandler, QueryHandler
from aod.infrastructure.repository.async_ import Repository


class User(RootEntity):
    id: int
    name: str


class Order(RootEntity):
    id: int
    total: float


class CreateUser(Command[User, User]):
    name: str


class GetUser(Query[User, User | None]):
    user_id: int


class DeleteUser(Command[User, None]):
    user_id: int


class CountUsers(Query[User, tuple[int, User]]):
    pass


class CreateOrder(Command[Order, Order]):
    total: float


class CreateUserHandler(CommandHandler[CreateUser]):
    async def handle(self, cmd: CreateUser) -> User:
        return User(id=1, name=cmd.name)


class GetUserHandler(QueryHandler[GetUser]):
    async def handle(self, query: GetUser) -> User | None:
        if query.user_id == 1:
            return User(id=1, name="Alice")
        return None


class DeleteUserHandler(CommandHandler[DeleteUser]):
    async def handle(self, cmd: DeleteUser) -> None: ...


class CountUsersHandler(QueryHandler[CountUsers]):
    async def handle(self, query: CountUsers) -> tuple[int, User]:
        return (42, User(id=1, name="dummy"))


class CreateOrderHandler(CommandHandler[CreateOrder]):
    async def handle(self, cmd: CreateOrder) -> Order:
        return Order(id=1, total=cmd.total)


class BaseCommandHandler(CommandHandler[CreateUser]):
    async def handle(self, cmd: CreateUser) -> User:
        return User(id=99, name=cmd.name)


async def test_empty_init() -> None:
    class EmptyRepo(Repository[User]):
        pass

    repo = EmptyRepo()
    assert repo is not None


async def test_dispatches_command() -> None:
    class UserRepo(Repository[User]):
        pass

    repo = UserRepo(command_handlers=[CreateUserHandler()])
    result = await repo.command(CreateUser(name="Alice"))
    assert isinstance(result, User)
    assert result.name == "Alice"


async def test_dispatches_query() -> None:
    class UserRepo(Repository[User]):
        pass

    repo = UserRepo(query_handlers=[GetUserHandler()])
    result = await repo.query(GetUser(user_id=1))
    assert isinstance(result, User | None)


async def test_unknown_command_raises() -> None:
    class UserRepo(Repository[User]):
        pass

    repo = UserRepo()
    cmd = CreateUser(name="Alice")
    with pytest.raises(ApplicationException, match="No command handler registered for CreateUser"):
        await repo.command(cmd)


async def test_unknown_query_raises() -> None:
    class UserRepo(Repository[User]):
        pass

    repo = UserRepo()
    with pytest.raises(ApplicationException, match="No query handler registered for GetUser"):
        await repo.query(GetUser(user_id=1))


async def test_duplicate_command_handler_raises() -> None:
    class UserRepo(Repository[User]):
        pass

    with pytest.raises(ApplicationException, match="Duplicate handler for CreateUser"):
        UserRepo(command_handlers=[CreateUserHandler(), CreateUserHandler()])


async def test_duplicate_query_handler_raises() -> None:
    class UserRepo(Repository[User]):
        pass

    with pytest.raises(ApplicationException, match="Duplicate handler for GetUser"):
        UserRepo(query_handlers=[GetUserHandler(), GetUserHandler()])


async def test_multiple_handlers() -> None:
    class UserRepo(Repository[User]):
        pass

    repo = UserRepo(
        command_handlers=[CreateUserHandler(), DeleteUserHandler()],
        query_handlers=[GetUserHandler(), CountUsersHandler()],
    )

    user = await repo.command(CreateUser(name="Charlie"))
    assert user is not None
    assert user.name == "Charlie"

    found = await repo.query(GetUser(user_id=1))
    assert found is not None
    assert found.name == "Alice"

    count = await repo.query(CountUsers())
    assert count[0] == 42
    assert count[1].id == 1

    result = await repo.command(DeleteUser(user_id=5))
    assert result is None


async def test_many_commands_do_not_share_state() -> None:
    class UserRepo(Repository[User]):
        pass

    repo = UserRepo(command_handlers=[CreateUserHandler()])

    user1 = await repo.command(CreateUser(name="A"))
    user2 = await repo.command(CreateUser(name="B"))
    assert user1.id == 1
    assert user1.name == "A"
    assert user2.name == "B"


async def test_repository_marker() -> None:
    class UserRepo(Repository[User]):
        pass

    repo = UserRepo()
    assert isinstance(repo, BaseSealed)


async def test_with_handler_inheritance() -> None:
    class UserRepo(Repository[User]):
        pass

    repo = UserRepo(command_handlers=[BaseCommandHandler()])
    user = await repo.command(CreateUser(name="Test"))
    assert user.id == 99


async def test_commands_and_queries_independent() -> None:
    class UserRepo(Repository[User]):
        pass

    repo = UserRepo(
        command_handlers=[CreateUserHandler()],
        query_handlers=[CountUsersHandler()],
    )

    user = await repo.command(CreateUser(name="X"))
    assert user is not None
    assert user.name == "X"

    count = await repo.query(CountUsers())
    assert count[0] == 42
    assert count[1].id == 1


async def test_no_queried_type_leak() -> None:
    class OrderRepo(Repository[Order]):
        pass

    repo = OrderRepo(command_handlers=[CreateOrderHandler()])
    order = await repo.command(CreateOrder(total=99.99))
    assert isinstance(order, Order)
    assert order.total == 99.99


async def test_handler_for_wrong_entity_type() -> None:
    class OrderHandler(CommandHandler[CreateOrder]):
        async def handle(self, cmd: CreateOrder) -> Order:
            return Order(id=1, total=cmd.total)

    class UserRepo(Repository[User]):
        pass

    with pytest.raises(
        DomainException, match="handles entity Order, but repository is for entity User"
    ):
        UserRepo(command_handlers=[OrderHandler()])


async def test_validate_handler_type_raises_async() -> None:
    class NotAHandler(BaseSealed):
        pass

    with pytest.raises(DomainException, match="does not handle"):
        validate_handler_type(NotAHandler(), CommandHandler)

    with pytest.raises(DomainException, match="does not handle"):
        validate_handler_type(NotAHandler(), QueryHandler)


async def test_extract_handler_type_raises_async() -> None:
    class BadHandler(CommandHandler):
        async def handle(self, cmd):
            return None

    with pytest.raises(DomainException):
        extract_handler_type(BadHandler(), (CommandHandler, QueryHandler))
