from __future__ import annotations

from typing import Any, cast

import pytest

from aod._internal.application.contracts import Command, Query
from aod._internal.application.handler import CommandPort as AppCommandPort
from aod._internal.application.handler import QueryPort as AppQueryPort
from aod._internal.application.transaction import Transaction
from aod._internal.application.use_case import UseCase
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.domain.entity import RootEntity
from aod._internal.infrastructure.container import AdapterContainer
from aod._internal.infrastructure.handlers import CommandHandler, QueryHandler
from aod._internal.infrastructure.session import Session
from aod._internal.testing.doubles.infrastructure.container import spy_adapter_container


class User(RootEntity):
    id: int = Field(id=True)
    name: str
    email: str


class SaveUser(Command[User, None]):
    user_id: str
    name: str
    email: str


class GetUser(Query[User, User | None]):
    user_id: str


class MongoSession(Session):
    _begin_count: int = PrivateField(default=0)
    _commit_count: int = PrivateField(default=0)
    _rollback_count: int = PrivateField(default=0)

    def execute(self, operation: object) -> object:
        return None

    def query(self, operation: object) -> object:
        return None

    def begin(self) -> None:
        self._begin_count += 1

    def commit(self) -> None:
        self._commit_count += 1

    def rollback(self) -> None:
        self._rollback_count += 1

    def close(self) -> None:
        pass

    def is_dirty(self) -> bool:
        return True


class PSQLSession(Session):
    _begin_count: int = PrivateField(default=0)
    _commit_count: int = PrivateField(default=0)
    _rollback_count: int = PrivateField(default=0)

    def execute(self, operation: object) -> object:
        return None

    def query(self, operation: object) -> object:
        return None

    def begin(self) -> None:
        self._begin_count += 1

    def commit(self) -> None:
        self._commit_count += 1

    def rollback(self) -> None:
        self._rollback_count += 1

    def close(self) -> None:
        pass

    def is_dirty(self) -> bool:
        return True


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
    save_handler: AppCommandPort[SaveUser]
    get_handler: AppQueryPort[GetUser]

    def run(self, user_id: str, name: str, email: str) -> None:
        self.save_handler.handle(SaveUser(user_id=user_id, name=name, email=email))


class ContainerSaveUserHandler(SaveUserHandler):
    session: InMemoryMongoSession


class ContainerGetUserHandler(GetUserHandler):
    session: InMemoryPSQLSession


def test_multi_session_handlers_with_real_sessions() -> None:
    mongo = InMemoryMongoSession()
    psql = InMemoryPSQLSession()

    save_handler = SaveUserHandler(session=mongo)
    get_handler = GetUserHandler(session=psql)

    save_handler.handle(SaveUser(user_id="u1", name="Alice", email="alice@test.com"))

    assert len(mongo._saved) == 1
    assert mongo._saved[0]["collection"] == "users"
    assert mongo._saved[0]["document"]["name"] == "Alice"

    result = get_handler.handle(GetUser(user_id="u1"))
    assert result is None


def test_use_case_with_multi_session_handlers() -> None:
    mongo = InMemoryMongoSession()
    psql = InMemoryPSQLSession()

    save_handler = SaveUserHandler(session=mongo)
    get_handler = GetUserHandler(session=psql)

    uc = SyncUserUseCase(
        save_handler=save_handler,
        get_handler=get_handler,
    )
    uc.run(user_id="u1", name="Bob", email="bob@test.com")

    assert len(mongo._saved) == 1
    saved = mongo._saved[0]["document"]
    assert saved["name"] == "Bob"
    assert saved["email"] == "bob@test.com"


def test_spy_bundle_tracks_handler_calls() -> None:
    original = AdapterContainer(
        sessions={MongoSession, PSQLSession},
        handlers=[SaveUserHandler, GetUserHandler],
    )

    container = spy_adapter_container(original)

    assert container.get_session_stub(MongoSession) is not None
    assert container.get_session_stub(PSQLSession) is not None

    save_handler = container.get_handler(SaveUser)
    get_handler = container.get_handler(GetUser)

    save_handler.handle(SaveUser(user_id="u1", name="Alice", email="alice@test.com"))
    get_handler.handle(GetUser(user_id="u1"))

    assert isinstance(save_handler, SaveUserHandler)
    assert isinstance(get_handler, GetUserHandler)
    assert save_handler.handle.call_count == 1
    assert get_handler.handle.call_count == 1


def test_handlers_use_different_sessions() -> None:
    original = AdapterContainer(
        sessions={MongoSession, PSQLSession},
        handlers=[SaveUserHandler, GetUserHandler],
    )

    container = spy_adapter_container(original)

    save_handler = container.get_handler(SaveUser)
    get_handler = container.get_handler(GetUser)

    assert isinstance(save_handler, SaveUserHandler)
    assert isinstance(get_handler, GetUserHandler)
    assert object.__getattribute__(save_handler, "session") is not object.__getattribute__(
        get_handler, "session"
    )


def test_handlers_register_a_shared_session_once_per_transaction() -> None:
    session = InMemoryMongoSession()
    first = SaveUserHandler(session=session)
    second = SaveUserHandler(session=session)

    with Transaction() as transaction:
        assert transaction.sessions == []

        first.handle(SaveUser(user_id="u1", name="Alice", email="alice@test.com"))
        assert transaction.sessions == [session]
        assert session._is_begun

        second.handle(SaveUser(user_id="u2", name="Bob", email="bob@test.com"))
        assert transaction.sessions == [session]

    assert session._begin_count == 1
    assert session._commit_count == 1
    assert session._rollback_count == 0


def test_instantiating_a_handler_does_not_register_its_session() -> None:
    session = InMemoryMongoSession()

    with Transaction() as transaction:
        SaveUserHandler(session=session)

        assert transaction.sessions == []
        assert not session._is_begun


def test_container_handlers_share_one_transaction_with_distinct_sessions() -> None:
    container = AdapterContainer(
        sessions={InMemoryMongoSession, InMemoryPSQLSession},
        handlers=[ContainerSaveUserHandler, ContainerGetUserHandler],
    )
    save_handler = container.get_handler(SaveUser)
    get_handler = container.get_handler(GetUser)

    with container.transaction() as transaction:
        save_handler.handle(SaveUser(user_id="u1", name="Alice", email="alice@test.com"))
        get_handler.handle(GetUser(user_id="u1"))

        assert len(transaction.sessions) == 2
        assert object.__getattribute__(save_handler, "session") is not object.__getattribute__(
            get_handler, "session"
        )

    assert save_handler.session._begin_count == 1
    assert save_handler.session._commit_count == 1
    assert save_handler.session._rollback_count == 0
    assert get_handler.session._begin_count == 1
    assert get_handler.session._commit_count == 1
    assert get_handler.session._rollback_count == 0


def test_container_handlers_roll_back_all_distinct_sessions_on_failure() -> None:
    container = AdapterContainer(
        sessions={InMemoryMongoSession, InMemoryPSQLSession},
        handlers=[ContainerSaveUserHandler, ContainerGetUserHandler],
    )
    save_handler = container.get_handler(SaveUser)
    get_handler = container.get_handler(GetUser)

    with pytest.raises(ValueError, match="transaction failed"):
        with container.transaction():
            save_handler.handle(SaveUser(user_id="u1", name="Alice", email="alice@test.com"))
            get_handler.handle(GetUser(user_id="u1"))
            raise ValueError("transaction failed")

    for handler in (save_handler, get_handler):
        session = object.__getattribute__(handler, "session")
        assert session._begin_count == 1
        assert session._commit_count == 0
        assert session._rollback_count == 1
        assert not session._is_begun
