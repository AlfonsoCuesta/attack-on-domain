from __future__ import annotations

from typing import Any, cast

from aod._internal.application.contracts import Command, Query
from aod._internal.application.handler import CommandHandler as AppCommandHandler
from aod._internal.application.handler import QueryHandler as AppQueryHandler
from aod._internal.application.port import Port
from aod._internal.application.use_case import UseCase
from aod._internal.core.fields.fields import PrivateField
from aod._internal.domain.entity import RootEntity
from aod._internal.infrastructure.container import AdapterContainerBase
from aod._internal.infrastructure.handlers import CommandHandler, QueryHandler
from aod._internal.infrastructure.session import Session
from aod._internal.testing.doubles.infrastructure.container import spy_adapter_container


class User(RootEntity):
    id: int
    name: str
    email: str


class SaveUser(Command[User, None]):
    user_id: str
    name: str
    email: str


class GetUser(Query[User, User | None]):
    user_id: str


class MongoSession(Session):
    def execute(self, operation: object) -> object:
        return None

    def query(self, operation: object) -> object:
        return None

    def begin(self) -> None:
        pass

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass

    def is_dirty(self) -> bool:
        return False


class PSQLSession(Session):
    def execute(self, operation: object) -> object:
        return None

    def query(self, operation: object) -> object:
        return None

    def begin(self) -> None:
        pass

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass

    def is_dirty(self) -> bool:
        return False


class InMemoryMongoSession(MongoSession):
    _saved: list[dict[str, Any]] = PrivateField(default_factory=list)

    def save(self, collection: str, document: object) -> None:
        self._saved.append({"collection": collection, "document": document})

    def find(self, collection: str, doc_id: str) -> object | None:
        for doc in self._saved:
            if doc["collection"] == collection and doc["document"] == doc_id:
                return doc["document"]
        return None


class InMemoryPSQLSession(PSQLSession):
    _inserted: list[dict[str, Any]] = PrivateField(default_factory=list)
    _selected: list[dict[str, Any]] = PrivateField(default_factory=list)

    def insert(self, table: str, row: object) -> None:
        self._inserted.append({"table": table, "row": row})

    def select(self, table: str, row_id: str) -> object | None:
        self._selected.append({"table": table, "id": row_id})
        for row in self._inserted:
            if row["table"] == table and row["row"] == row_id:
                return row["row"]
        return None


class SaveUserHandler(CommandHandler[SaveUser]):
    session: MongoSession

    def handle(self, command: SaveUser) -> None:
        assert isinstance(self.session, InMemoryMongoSession)
        self.session.save(
            "users", {"id": command.user_id, "name": command.name, "email": command.email}
        )


class GetUserHandler(QueryHandler[GetUser]):
    session: PSQLSession

    def handle(self, query: GetUser) -> User | None:
        assert isinstance(self.session, InMemoryPSQLSession)
        result = self.session.select("users", query.user_id)
        if result is None:
            return None
        d = cast(dict[str, Any], result)
        return User(id=1, name=d["name"], email=d["email"])


class SyncUserUseCase(UseCase):
    save_handler: AppCommandHandler[SaveUser]
    get_handler: AppQueryHandler[GetUser]

    def run(self, user_id: str, name: str, email: str) -> None:
        self.save_handler.handle(SaveUser(user_id=user_id, name=name, email=email))


class UserServiceContainer(AdapterContainerBase):
    pass


def test_multi_session_handlers_with_double_sessions() -> None:
    in_memory_mongo = InMemoryMongoSession()
    in_memory_psql = InMemoryPSQLSession()

    original = UserServiceContainer(
        sessions={MongoSession, PSQLSession},
        handlers=[SaveUserHandler, GetUserHandler],
    )

    container = spy_adapter_container(
        original,
        double_sessions={
            MongoSession: in_memory_mongo,
            PSQLSession: in_memory_psql,
        },
    )

    save_handler = container.get_handler(SaveUser)
    get_handler = container.get_handler(GetUser)

    save_handler.handle(SaveUser(user_id="u1", name="Alice", email="alice@test.com"))

    assert len(in_memory_mongo._saved) == 1
    assert in_memory_mongo._saved[0]["collection"] == "users"
    assert in_memory_mongo._saved[0]["document"]["name"] == "Alice"

    user = get_handler.handle(GetUser(user_id="u1"))
    assert user is None

    result = get_handler.handle(GetUser(user_id="nonexistent"))
    assert result is None


def test_use_case_with_multi_session_handlers() -> None:
    in_memory_mongo = InMemoryMongoSession()
    in_memory_psql = InMemoryPSQLSession()

    original = UserServiceContainer(
        sessions={MongoSession, PSQLSession},
        handlers=[SaveUserHandler, GetUserHandler],
    )

    container = spy_adapter_container(
        original,
        double_sessions={
            MongoSession: in_memory_mongo,
            PSQLSession: in_memory_psql,
        },
    )

    save_handler = container.get_handler(SaveUser)
    get_handler = container.get_handler(GetUser)
    assert isinstance(save_handler, SaveUserHandler)
    assert isinstance(get_handler, GetUserHandler)

    uc = SyncUserUseCase(
        save_handler=save_handler,
        get_handler=get_handler,
    )
    uc.run(user_id="u1", name="Bob", email="bob@test.com")

    assert len(in_memory_mongo._saved) == 1
    saved = in_memory_mongo._saved[0]["document"]
    assert saved["name"] == "Bob"
    assert saved["email"] == "bob@test.com"


def test_spy_bundle_tracks_handler_calls() -> None:
    in_memory_mongo = InMemoryMongoSession()
    in_memory_psql = InMemoryPSQLSession()

    original = UserServiceContainer(
        sessions={MongoSession, PSQLSession},
        handlers=[SaveUserHandler, GetUserHandler],
    )

    container = spy_adapter_container(
        original,
        double_sessions={
            MongoSession: in_memory_mongo,
            PSQLSession: in_memory_psql,
        },
    )

    spy = container.spy_bundle
    assert isinstance(spy.sync_session, Session)
    assert spy.logger is not None
    assert spy.event_bus is not None
    assert spy.cache is not None

    save_handler = container.get_handler(SaveUser)
    save_handler.handle(SaveUser(user_id="u1", name="Alice", email="alice@test.com"))

    get_handler = container.get_handler(GetUser)
    get_handler.handle(GetUser(user_id="u1"))

    assert len(in_memory_mongo._saved) == 1
    assert len(in_memory_psql._selected) == 1


def test_handlers_use_different_sessions() -> None:
    in_memory_mongo = InMemoryMongoSession()
    in_memory_psql = InMemoryPSQLSession()

    original = UserServiceContainer(
        sessions={MongoSession, PSQLSession},
        handlers=[SaveUserHandler, GetUserHandler],
    )

    container = spy_adapter_container(
        original,
        double_sessions={
            MongoSession: in_memory_mongo,
            PSQLSession: in_memory_psql,
        },
    )

    save_handler = container.get_handler(SaveUser)
    get_handler = container.get_handler(GetUser)

    assert isinstance(save_handler.session, InMemoryMongoSession)
    assert isinstance(get_handler.session, InMemoryPSQLSession)

    save_handler.handle(SaveUser(user_id="u1", name="Alice", email="alice@test.com"))
    get_handler.handle(GetUser(user_id="u1"))

    assert len(in_memory_mongo._saved) == 1
    assert len(in_memory_psql._selected) == 1
