from __future__ import annotations

import asyncio
from typing import ClassVar, cast

import pytest

from aod.application import (
    Command,
    CommandPort,
    PolicyContract,
    PolicyManager,
    Query,
    QueryPort,
    Transaction,
    UseCase,
)
from aod.application.async_ import QueryPort as AsyncQueryPort
from aod.domain import Field, PrivateField, RootEntity
from aod.infrastructure import (
    AdapterContainer,
    CommandHandler,
    PolicyHandler,
    QueryHandler,
    Session,
)
from aod.infrastructure.async_ import PolicyHandler as AsyncPolicyHandler
from aod.infrastructure.async_ import QueryHandler as AsyncQueryHandler
from aod.infrastructure.async_ import Session as AsyncSession
from aod.exceptions import InvalidUseCasePortFieldError, PolicyEnforcementError


class AccessContract(PolicyContract):
    user_id: str


class AccessHandler(PolicyHandler[AccessContract]):
    def handle(self, contract: AccessContract) -> None:
        if contract.user_id != "allowed":
            raise PermissionError("access denied")


class AsyncAccessHandler(AsyncPolicyHandler[AccessContract]):
    async def handle(self, contract: AccessContract) -> None:
        if contract.user_id != "allowed":
            raise PermissionError("access denied")


class ReportAccessContract(PolicyContract):
    user_id: str


class AsyncReportAccessHandler(AsyncPolicyHandler[ReportAccessContract]):
    async def handle(self, contract: ReportAccessContract) -> None:
        if contract.user_id != "allowed":
            raise PermissionError("access denied")


class Document(RootEntity):
    id: str = Field(id=True)
    owner_id: str
    admin_ids: list[str]


class GetDocument(Query[Document, Document | None]):
    document_id: str


class RecordDocumentAccess(Command[Document, None]):
    document_id: str


class DocumentSession(Session):
    _begin_count: int = PrivateField(default=0)
    _commit_count: int = PrivateField(default=0)
    _rollback_count: int = PrivateField(default=0)

    def execute(self, operation: object) -> object:
        return operation

    def query(self, operation: object) -> Document:
        query = cast(GetDocument, operation)
        return Document(id=query.document_id, owner_id="owner-1", admin_ids=["admin-1"])

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


class DocumentQueryHandler(QueryHandler[GetDocument]):
    session: DocumentSession

    def handle(self, query: GetDocument) -> Document:
        return self.session.query(query)


class RecordDocumentAccessHandler(CommandHandler[RecordDocumentAccess]):
    access_recorded: ClassVar[bool] = False

    def handle(self, command: RecordDocumentAccess) -> None:
        RecordDocumentAccessHandler.access_recorded = True


class OwnerContract(PolicyContract):
    user_id: str
    document_id: str


class AdminContract(PolicyContract):
    user_id: str
    document_id: str


class OwnerPolicyHandler(PolicyHandler[OwnerContract]):
    documents: QueryPort[GetDocument]

    def handle(self, contract: OwnerContract) -> None:
        document = self.documents.handle(GetDocument(document_id=contract.document_id))
        if document is None or document.owner_id != contract.user_id:
            raise PermissionError("not the document owner")


class AdminPolicyHandler(PolicyHandler[AdminContract]):
    documents: QueryPort[GetDocument]
    record_access: CommandPort[RecordDocumentAccess]

    def handle(self, contract: AdminContract) -> None:
        document = self.documents.handle(GetDocument(document_id=contract.document_id))
        if document is None or contract.user_id not in document.admin_ids:
            raise PermissionError("not a document administrator")
        self.record_access.handle(RecordDocumentAccess(document_id=contract.document_id))


class UpdateDocument(UseCase):
    _updated: bool = False

    def run(self) -> None:
        self._updated = True


class AsyncDocumentSession(AsyncSession):
    _begin_count: int = PrivateField(default=0)
    _commit_count: int = PrivateField(default=0)
    _rollback_count: int = PrivateField(default=0)

    async def execute(self, operation: object) -> object:
        return operation

    async def query(self, operation: object) -> Document:
        query = cast(GetDocument, operation)
        return Document(id=query.document_id, owner_id="owner-1", admin_ids=["admin-1"])

    async def begin(self) -> None:
        self._begin_count += 1

    async def commit(self) -> None:
        self._commit_count += 1

    async def rollback(self) -> None:
        self._rollback_count += 1

    async def close(self) -> None:
        pass

    def is_dirty(self) -> bool:
        return True


class AsyncDocumentQueryHandler(AsyncQueryHandler[GetDocument]):
    session: AsyncDocumentSession

    async def handle(self, query: GetDocument) -> Document:
        return await self.session.query(query)


class AsyncOwnerPolicyHandler(AsyncPolicyHandler[OwnerContract]):
    documents: AsyncQueryPort[GetDocument]

    async def handle(self, contract: OwnerContract) -> None:
        document = await self.documents.handle(GetDocument(document_id=contract.document_id))
        if document is None or document.owner_id != contract.user_id:
            raise PermissionError("not the document owner")


def test_container_builds_policy_manager_from_policy_handlers() -> None:
    container = AdapterContainer(handlers=[AccessHandler])

    manager = container.policy_manager()

    manager.enforce(AccessContract(user_id="allowed"))


def test_container_builds_async_policy_manager_from_policy_handlers() -> None:
    container = AdapterContainer(handlers=[AsyncAccessHandler])

    manager = container.async_policy_manager()

    async def run() -> None:
        await manager.enforce(AccessContract(user_id="allowed"))

    asyncio.run(run())


def test_manager_filters_policy_handlers_by_syncness() -> None:
    container = AdapterContainer(handlers=[AccessHandler, AsyncReportAccessHandler])

    sync_manager = container.policy_manager()
    sync_manager.enforce(AccessContract(user_id="allowed"))

    async def run() -> None:
        async_manager = container.async_policy_manager()
        await async_manager.enforce(ReportAccessContract(user_id="allowed"))

    asyncio.run(run())


def test_container_adapts_policy_handler_directly() -> None:
    container = AdapterContainer(
        sessions={DocumentSession},
        handlers=[DocumentQueryHandler, OwnerPolicyHandler],
    )
    handler = container.adapt(OwnerPolicyHandler)
    manager = PolicyManager(handler)

    with Transaction():
        manager.enforce(OwnerContract(user_id="owner-1", document_id="doc-1"))


def test_policy_handler_cannot_declare_session_fields() -> None:
    with pytest.raises(InvalidUseCasePortFieldError):

        class InvalidPolicyHandler(PolicyHandler[OwnerContract]):
            session: DocumentSession

            def handle(self, contract: OwnerContract) -> None:
                pass


def test_policy_can_use_query_handler_before_use_case_in_one_transaction() -> None:
    container = AdapterContainer(
        sessions={DocumentSession},
        handlers=[
            DocumentQueryHandler,
            RecordDocumentAccessHandler,
            OwnerPolicyHandler,
            AdminPolicyHandler,
        ],
    )
    manager = container.policy_manager()
    use_case = container.adapt(UpdateDocument)
    RecordDocumentAccessHandler.access_recorded = False

    with container.transaction():
        manager.enforce(
            AdminContract(user_id="admin-1", document_id="doc-1")
            | OwnerContract(user_id="owner-1", document_id="doc-1")
        )
        use_case.run()

    session = container.get_session(DocumentSession)
    assert use_case._updated
    assert RecordDocumentAccessHandler.access_recorded
    assert session._begin_count == 1
    assert session._commit_count == 1
    assert session._rollback_count == 0


def test_policy_failure_rolls_back_query_session_before_use_case() -> None:
    container = AdapterContainer(
        sessions={DocumentSession},
        handlers=[
            DocumentQueryHandler,
            RecordDocumentAccessHandler,
            OwnerPolicyHandler,
            AdminPolicyHandler,
        ],
    )
    manager = container.policy_manager()
    use_case = container.adapt(UpdateDocument)

    with pytest.raises(PolicyEnforcementError):
        with container.transaction():
            manager.enforce(
                AdminContract(user_id="visitor-1", document_id="doc-1")
                | OwnerContract(user_id="visitor-1", document_id="doc-1")
            )
            use_case.run()

    session = container.get_session(DocumentSession)
    assert not use_case._updated
    assert session._begin_count == 1
    assert session._commit_count == 0
    assert session._rollback_count == 1


def test_policy_can_be_constructed_without_container() -> None:
    session = DocumentSession()
    query_handler = DocumentQueryHandler(session=session)
    policy_handler = OwnerPolicyHandler(documents=query_handler)
    manager = PolicyManager(policy_handler)

    with Transaction():
        manager.enforce(OwnerContract(user_id="owner-1", document_id="doc-1"))

    assert session._begin_count == 1
    assert session._commit_count == 1


def test_async_policy_can_use_query_handler_before_use_case() -> None:
    container = AdapterContainer(
        sessions={AsyncDocumentSession},
        handlers=[AsyncDocumentQueryHandler, AsyncOwnerPolicyHandler],
    )
    manager = container.async_policy_manager()

    async def run() -> None:
        async with container.async_transaction():
            await manager.enforce(OwnerContract(user_id="owner-1", document_id="doc-1"))

    asyncio.run(run())

    session = container.get_session(AsyncDocumentSession)
    assert session._begin_count == 1
    assert session._commit_count == 1
    assert session._rollback_count == 0
