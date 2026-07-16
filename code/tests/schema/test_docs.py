"""Tests for all schema doc types."""

import inspect

from aod._internal.application.cache import AsyncCache, Cache
from aod._internal.application.contracts import Command, Query
from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.handler import (
    AsyncCommandPort,
    AsyncQueryPort,
    CommandPort,
    QueryPort,
)
from aod._internal.application.logger import AsyncLogger, Logger
from aod._internal.application.port import Port
from aod._internal.application.unit_of_work import AsyncUnitOfWork, UnitOfWork
from aod._internal.application.use_case import AsyncUseCase, UseCase
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.service import Service
from aod._internal.domain.value_object import ValueObject
from aod._internal.infrastructure.handlers import (
    AsyncCommandHandler,
    CommandHandler,
    QueryHandler,
)
from aod._internal.infrastructure.projection import (
    Projection,
    ProjectionBase,
    ReadProjection,
    WriteProjection,
)
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.schema.app import App
from aod._internal.schema.bounded_context import BoundedContext
from aod._internal.schema.describe_utils import extract_fields, extract_methods, extract_params
from aod._internal.schema.docs.app_doc import AppDoc
from aod._internal.schema.docs.bounded_context_doc import BoundedContextDoc
from aod._internal.schema.docs.contract_doc import ContractDoc
from aod._internal.schema.docs.entity_doc import EntityDoc
from aod._internal.schema.docs.generic_docs import (
    FieldDoc,
    MethodDoc,
    ParamDoc,
    default_str,
    type_str,
)
from aod._internal.schema.docs.handler_doc import HandlerDoc
from aod._internal.schema.docs.handler_doc import _session_name as handler_session_name
from aod._internal.schema.docs.handler_port_doc import HandlerPortDoc
from aod._internal.schema.docs.infrastructure_doc import InfrastructureDoc
from aod._internal.schema.docs.module_doc import ModuleDoc
from aod._internal.schema.docs.port_doc import PortDoc
from aod._internal.schema.docs.projection_doc import ProjectionDoc
from aod._internal.schema.docs.projection_doc import _session_name as projection_session_name
from aod._internal.schema.docs.root_entity_doc import RootEntityDoc
from aod._internal.schema.docs.service_doc import ServiceDoc
from aod._internal.schema.docs.session_doc import SessionDoc
from aod._internal.schema.docs.use_case_doc import UseCaseDoc
from aod._internal.schema.docs.value_object_doc import ValueObjectDoc
from aod._internal.schema.infrastructure import Infrastructure
from aod._internal.schema.module import Module
from aod.domain import Field
from pydantic import BaseModel as DTO
from pydantic.fields import FieldInfo

# ---- Domain types for tests ----


class OrderLine(ValueObject):
    product_id: str
    quantity: int = 1


class Order(RootEntity):
    id: str = Field(id=True)
    total: float = 0.0

    def add_line(self, product_id: str, quantity: int) -> None:
        pass


class LineItem(Entity):
    id: int = Field(id=True)
    sku: str


class Customer(ValueObject):
    name: str
    email: str


class PricingService(Service):
    def calculate_discount(self, total: float) -> float:
        return total * 0.1


# ---- Contracts ----


class PlaceOrder(Command[Order, None]):
    order_id: str
    product_id: str
    quantity: int = 1

    def validate(self) -> bool:
        return self.quantity > 0


class GetOrder(Query[Order, Order | None]):
    order_id: str


# ---- Infrastructure ----


class MySession(Session):
    _connection: object = None

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


class MyAsyncSession(AsyncSession):
    async def execute(self, operation: object) -> object:
        return None

    async def query(self, operation: object) -> object:
        return None

    async def begin(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def close(self) -> None:
        pass

    def is_dirty(self) -> bool:
        return False


class PlaceOrderHandler(CommandHandler[PlaceOrder]):
    session: MySession

    def handle(self, command: PlaceOrder) -> None:
        pass


class GetOrderHandler(QueryHandler[GetOrder]):
    session: MySession

    def handle(self, query: GetOrder) -> Order | None:
        return None


class AsyncPlaceOrderHandler(AsyncCommandHandler[PlaceOrder]):
    session: MyAsyncSession

    async def handle(self, command: PlaceOrder) -> None:
        pass


# ---- Projections ----


class OrderListModel(DTO):
    customer_id: str


class OrderSummary(DTO):
    order_id: str
    total: float


class MyReadProjection(ReadProjection):
    def read(self, model: OrderListModel) -> list[Order]:
        return []


class MyWriteProjection(WriteProjection):
    def write(self, model: OrderSummary) -> None:
        pass


class MyProjection(Projection):
    def read(self, model: OrderListModel) -> list[Order]:
        return []

    def write(self, model: OrderSummary) -> None:
        pass


# ---- Use Cases ----


class PlaceOrderUseCase(UseCase):
    place_order: CommandPort[PlaceOrder]
    get_order: QueryPort[GetOrder]
    logger: Logger

    def run(self, order_id: str, product_id: str) -> None:
        pass


class AsyncOrderUseCase(AsyncUseCase):
    place_order: AsyncCommandPort[PlaceOrder]
    logger: AsyncLogger

    async def run(self, order_id: str) -> None:
        pass


# ---- Custom Port ----


class EmailSender(Port):
    def send(self, to: str, subject: str) -> None:
        pass


class NotifyUseCase(UseCase):
    email: EmailSender

    def run(self, user_id: int) -> None:
        self.email.send("test@test.com", "Hello")


# ---- Callable without __name__ for edge-case testing ----


class _CallableNoName:
    def __call__(self) -> None:
        pass


# ============================================================
# Generic doc helpers
# ============================================================


class TestTypeStr:
    def test_simple_type(self) -> None:
        assert type_str(int) == "int"
        assert type_str(str) == "str"

    def test_generic_type(self) -> None:
        assert type_str(list[str]) == "list[str]"
        assert type_str(dict[str, int]) == "dict[str, int]"

    def test_union_type(self) -> None:
        assert type_str(Order | None) == "Union[Order, NoneType]"

    def test_empty(self) -> None:
        assert type_str(inspect.Parameter.empty) == ""
        assert type_str(inspect.Signature.empty) == ""


class TestDefaultStr:
    def test_undefined(self) -> None:
        from pydantic_core import PydanticUndefined

        assert default_str(PydanticUndefined) == ""

    def test_none(self) -> None:
        assert default_str(None) == "None"

    def test_value(self) -> None:
        assert default_str(42) == "42"
        assert default_str("hello") == "'hello'"

    def test_empty_param(self) -> None:
        assert default_str(inspect.Parameter.empty) == ""


class TestFieldDoc:
    def test_from_field_with_annotation(self) -> None:
        fi = FieldInfo(annotation=str, default="x", description="a field")
        doc = FieldDoc.from_field("name", fi)
        assert doc.name == "name"
        assert doc.type_name == "str"
        assert doc.default == "'x'"
        assert doc.description == "a field"

    def test_from_field_no_description(self) -> None:
        fi = FieldInfo(annotation=int)
        doc = FieldDoc.from_field("age", fi)
        assert doc.description == ""

    def test_from_field_integer_default(self) -> None:
        fi = FieldInfo(annotation=int, default=10)
        doc = FieldDoc.from_field("qty", fi)
        assert doc.default == "10"


class TestParamDoc:
    def test_defaults(self) -> None:
        p = ParamDoc(name="x", type_name="int", default="1")
        assert p.name == "x"
        assert p.type_name == "int"
        assert p.default == "1"


class TestMethodDoc:
    def test_from_method_basic(self) -> None:
        def foo(a: int, b: str) -> bool:
            """Check something."""
            return True

        doc = MethodDoc.from_method(foo)
        assert doc.name == "foo"
        assert doc.return_type == "bool"
        assert len(doc.params) == 2
        assert doc.params[0].name == "a"
        assert doc.params[0].type_name == "int"
        assert doc.params[1].name == "b"
        assert doc.params[1].type_name == "str"
        assert doc.description == "Check something."

    def test_from_method_skips_self(self) -> None:
        class Cls:
            def method(self, x: int) -> None:
                pass

        doc = MethodDoc.from_method(Cls.method)
        assert len(doc.params) == 1
        assert doc.params[0].name == "x"

    def test_from_method_skips_cls(self) -> None:
        class Cls:
            @classmethod
            def method(cls, x: int) -> None:
                pass

        doc = MethodDoc.from_method(Cls.method)
        assert len(doc.params) == 1
        assert doc.params[0].name == "x"

    def test_from_method_no_return(self) -> None:
        def foo() -> None:
            pass

        doc = MethodDoc.from_method(foo)
        assert doc.return_type == "None"

    def test_from_method_no_docstring(self) -> None:
        def foo() -> None:
            pass

        doc = MethodDoc.from_method(foo)
        assert doc.description == ""

    def test_from_method_with_union_return(self) -> None:
        doc = MethodDoc.from_method(GetOrderHandler.handle)
        assert doc.name == "handle"
        assert "Union" in doc.return_type or "Optional" in doc.return_type


# ============================================================
# describe_utils
# ============================================================


class TestExtractFields:
    def test_with_model_fields(self) -> None:
        fields = extract_fields(Order)
        names = {f.name for f in fields}
        assert "id" in names
        assert "total" in names

    def test_without_model_fields(self) -> None:
        class NoFields:
            x: int

        assert extract_fields(NoFields) == []

    def test_skips_private(self) -> None:
        fields = extract_fields(PlaceOrder)
        names = {f.name for f in fields}
        assert "_event_emitter" not in names


class TestExtractMethods:
    def test_with_methods(self) -> None:
        methods = extract_methods(Order)
        names = {m.name for m in methods}
        assert "add_line" in names

    def test_skips_dunders(self) -> None:
        methods = extract_methods(Order)
        for m in methods:
            assert not m.name.startswith("__")

    def test_empty_class(self) -> None:
        class Empty:
            pass

        assert extract_methods(Empty) == []

    def test_only_dunders(self) -> None:
        class OnlyDunders:
            def __init__(self) -> None:
                pass

            def __repr__(self) -> str:
                return ""

        assert extract_methods(OnlyDunders) == []


class TestExtractParams:
    def test_with_params(self) -> None:
        params = extract_params(PlaceOrderUseCase.run)
        names = {p.name for p in params}
        assert names == {"order_id", "product_id"}

    def test_skips_self(self) -> None:
        def method(self, a: int) -> None:
            pass

        params = extract_params(method)
        assert len(params) == 1
        assert params[0].name == "a"

    def test_extract_params_no_self(self) -> None:
        def no_self(a: int, b: str) -> None:
            pass

        params = extract_params(no_self)
        assert len(params) == 2


# ============================================================
# PortDoc
# ============================================================


class TestPortDoc:
    def test_sync_port(self) -> None:
        doc = PortDoc.from_port(Logger)
        assert doc.name == "Logger"
        assert doc.is_async is False
        assert doc.methods

    def test_async_port(self) -> None:
        doc = PortDoc.from_port(AsyncLogger)
        assert doc.is_async is True

    def test_cache_port(self) -> None:
        doc = PortDoc.from_port(Cache)
        assert doc.name == "Cache"

    def test_async_cache_port(self) -> None:
        doc = PortDoc.from_port(AsyncCache)
        assert doc.is_async is True

    def test_eventbus_port(self) -> None:
        doc = PortDoc.from_port(EventBus)
        assert doc.name == "EventBus"
        assert not doc.is_async

    def test_async_eventbus(self) -> None:
        doc = PortDoc.from_port(AsyncEventBus)
        assert doc.is_async is True

    def test_uow_port(self) -> None:
        doc = PortDoc.from_port(UnitOfWork)
        assert doc.name == "UnitOfWork"

    def test_async_uow_port(self) -> None:
        doc = PortDoc.from_port(AsyncUnitOfWork)
        assert doc.name == "AsyncUnitOfWork"
        assert doc.is_async is True

    def test_custom_port(self) -> None:
        doc = PortDoc.from_port(EmailSender)
        assert doc.name == "EmailSender"
        assert not doc.is_async
        method_names = {m.name for m in doc.methods}
        assert "send" in method_names


# ============================================================
# ContractDoc
# ============================================================


class TestContractDoc:
    def test_command_contract(self) -> None:
        doc = ContractDoc.from_contract(PlaceOrder)
        assert doc.name == "PlaceOrder"
        assert doc.kind == "command"
        field_names = {f.name for f in doc.fields}
        assert "order_id" in field_names
        assert "product_id" in field_names
        assert "quantity" in field_names
        method_names = {m.name for m in doc.methods}
        assert "validate" in method_names

    def test_query_contract(self) -> None:
        doc = ContractDoc.from_contract(GetOrder)
        assert doc.name == "GetOrder"
        assert doc.kind == "query"
        field_names = {f.name for f in doc.fields}
        assert "order_id" in field_names


# ============================================================
# HandlerPortDoc
# ============================================================


class TestHandlerPortDoc:
    def test_command_port(self) -> None:
        doc = HandlerPortDoc.from_handler_port("create", CommandPort[PlaceOrder])
        assert doc is not None
        assert doc.name == "create"
        assert doc.handler_type == "CommandPort"
        assert doc.kind == "command"
        assert not doc.is_async
        assert doc.contract_doc is not None
        assert doc.contract_doc.name == "PlaceOrder"
        assert doc.contract_doc.kind == "command"
        assert doc.contract_doc.fields

    def test_query_port(self) -> None:
        doc = HandlerPortDoc.from_handler_port("get", QueryPort[GetOrder])
        assert doc is not None
        assert doc.handler_type == "QueryPort"
        assert doc.kind == "query"
        assert not doc.is_async
        assert doc.contract_doc is not None
        assert doc.contract_doc.name == "GetOrder"

    def test_async_command_port(self) -> None:
        doc = HandlerPortDoc.from_handler_port("create", AsyncCommandPort[PlaceOrder])
        assert doc is not None
        assert doc.handler_type == "AsyncCommandPort"
        assert doc.kind == "command"
        assert doc.is_async

    def test_async_query_port(self) -> None:
        doc = HandlerPortDoc.from_handler_port("get", AsyncQueryPort[GetOrder])
        assert doc is not None
        assert doc.handler_type == "AsyncQueryPort"
        assert doc.kind == "query"
        assert doc.is_async

    def test_non_handler_port(self) -> None:
        assert HandlerPortDoc.from_handler_port("x", int) is None

    def test_no_origin(self) -> None:
        assert HandlerPortDoc.from_handler_port("x", "not an annotation") is None


# ============================================================
# EntityDoc / RootEntityDoc / ValueObjectDoc / ServiceDoc
# ============================================================


class TestRootEntityDoc:
    def test_with_contracts(self) -> None:
        doc = RootEntityDoc.from_root_entity(Order, [PlaceOrder, GetOrder])
        assert doc.name == "Order"
        assert not doc.description
        field_names = {f.name for f in doc.fields}
        assert "id" in field_names
        assert "total" in field_names
        method_names = {m.name for m in doc.methods}
        assert "add_line" in method_names
        assert doc.commands == ["PlaceOrder"]
        assert doc.queries == ["GetOrder"]

    def test_without_contracts(self) -> None:
        doc = RootEntityDoc.from_root_entity(Order, None)
        assert doc.commands == []
        assert doc.queries == []


class TestEntityDoc:
    def test_from_entity(self) -> None:
        doc = EntityDoc.from_entity(LineItem)
        assert doc.name == "LineItem"
        field_names = {f.name for f in doc.fields}
        assert "id" in field_names
        assert "sku" in field_names


class TestValueObjectDoc:
    def test_from_value_object(self) -> None:
        doc = ValueObjectDoc.from_value_object(OrderLine)
        assert doc.name == "OrderLine"
        field_names = {f.name for f in doc.fields}
        assert "product_id" in field_names
        assert "quantity" in field_names

    def test_with_methods(self) -> None:
        class TaxRate(ValueObject):
            rate: float

            def apply(self, amount: float) -> float:
                return amount * self.rate

        doc = ValueObjectDoc.from_value_object(TaxRate)
        method_names = {m.name for m in doc.methods}
        assert "apply" in method_names


class TestServiceDoc:
    def test_from_service(self) -> None:
        doc = ServiceDoc.from_service(PricingService)
        assert doc.name == "PricingService"
        method_names = {m.name for m in doc.methods}
        assert "calculate_discount" in method_names


# ============================================================
# UseCaseDoc
# ============================================================


class TestUseCaseDoc:
    def test_sync_use_case(self) -> None:
        doc = UseCaseDoc.from_use_case(PlaceOrderUseCase)
        assert doc.name == "PlaceOrderUseCase"
        assert not doc.is_async
        assert len(doc.handler_ports) == 2
        handler_names = {hp.name for hp in doc.handler_ports}
        assert "place_order" in handler_names
        assert "get_order" in handler_names
        port_names = {p.name for p in doc.ports}
        assert "Logger" in port_names
        param_names = {p.name for p in doc.params}
        assert "order_id" in param_names
        assert "product_id" in param_names

    def test_async_use_case(self) -> None:
        doc = UseCaseDoc.from_use_case(AsyncOrderUseCase)
        assert doc.name == "AsyncOrderUseCase"
        assert doc.is_async
        assert len(doc.handler_ports) == 1
        assert doc.handler_ports[0].is_async
        assert doc.handler_ports[0].handler_type == "AsyncCommandPort"

    def test_custom_port_use_case(self) -> None:
        doc = UseCaseDoc.from_use_case(NotifyUseCase)
        port_names = {p.name for p in doc.ports}
        assert "EmailSender" in port_names


# ============================================================
# BoundedContextDoc
# ============================================================


class TestBoundedContextDoc:
    def test_from_bounded_context(self) -> None:
        bc = BoundedContext(
            aggregate_roots=[Order],
            services=[PricingService],
            name="orders",
        )
        doc = BoundedContextDoc.from_bounded_context(bc)
        assert doc.name == "orders"
        assert len(doc.roots) == 1
        assert doc.roots[0].name == "Order"
        assert len(doc.value_objects) == 0
        assert len(doc.services) == 1
        assert doc.services[0].name == "PricingService"

    def test_from_bounded_context_no_name(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order])
        doc = BoundedContextDoc.from_bounded_context(bc)
        assert doc.name is None


# ============================================================
# HandlerDoc
# ============================================================


class TestHandlerDoc:
    def test_command_handler(self) -> None:
        doc = HandlerDoc.from_handler(PlaceOrderHandler)
        assert doc.name == "PlaceOrderHandler"
        assert doc.handler_type == "CommandHandler"
        assert not doc.is_async
        assert doc.contract == "PlaceOrder"
        assert doc.session == "MySession"
        assert doc.handle is not None
        assert doc.handle.name == "handle"
        param_names = {p.name for p in doc.handle.params}
        assert "command" in param_names

    def test_query_handler(self) -> None:
        doc = HandlerDoc.from_handler(GetOrderHandler)
        assert doc.name == "GetOrderHandler"
        assert doc.handler_type == "QueryHandler"
        assert doc.contract == "GetOrder"

    def test_async_command_handler(self) -> None:
        doc = HandlerDoc.from_handler(AsyncPlaceOrderHandler)
        assert doc.name == "AsyncPlaceOrderHandler"
        assert doc.handler_type == "AsyncCommandHandler"
        assert doc.is_async
        assert doc.contract == "PlaceOrder"
        assert doc.session == "MyAsyncSession"


# ============================================================
# SessionDoc
# ============================================================


class TestSessionDoc:
    def test_sync_session(self) -> None:
        doc = SessionDoc.from_session(MySession)
        assert doc.name == "MySession"
        assert not doc.is_async

    def test_async_session(self) -> None:
        doc = SessionDoc.from_session(MyAsyncSession)
        assert doc.name == "MyAsyncSession"
        assert doc.is_async


# ============================================================
# ProjectionDoc
# ============================================================


class TestProjectionDoc:
    def test_read_projection(self) -> None:
        doc = ProjectionDoc.from_projection(MyReadProjection)
        assert doc.name == "MyReadProjection"
        assert doc.projection_type == "ReadProjection"
        assert not doc.is_async
        assert doc.session == ""
        assert doc.read is not None
        assert doc.read.name == "read"
        assert doc.write is None

    def test_write_projection(self) -> None:
        doc = ProjectionDoc.from_projection(MyWriteProjection)
        assert doc.name == "MyWriteProjection"
        assert doc.projection_type == "WriteProjection"
        assert doc.read is None
        assert doc.write is not None
        assert doc.write.name == "write"

    def test_both_projection(self) -> None:
        doc = ProjectionDoc.from_projection(MyProjection)
        assert doc.projection_type == "Projection"
        assert doc.read is not None
        assert doc.write is not None


# ============================================================
# InfrastructureDoc
# ============================================================


class TestInfrastructureDoc:
    def test_from_infrastructure(self) -> None:
        infra = Infrastructure(
            handlers=[PlaceOrderHandler],
            projections=[MyReadProjection],
            ports=[EmailSender],
        )
        doc = InfrastructureDoc.from_infrastructure(infra)
        assert len(doc.handlers) == 1
        assert doc.handlers[0].name == "PlaceOrderHandler"
        session_names = {s.name for s in doc.sessions}
        assert "MySession" in session_names
        assert len(doc.projections) == 1
        assert doc.projections[0].name == "MyReadProjection"
        port_names = {p.name for p in doc.ports}
        assert "EmailSender" in port_names


# ============================================================
# ModuleDoc / AppDoc
# ============================================================


class TestModuleDoc:
    def test_from_module(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order], name="orders")
        infra = Infrastructure(handlers=[PlaceOrderHandler])
        mod = Module(name="orders_mod", context=bc, infrastructure=infra)
        doc = ModuleDoc.from_module(mod)
        assert doc.name == "orders_mod"
        assert doc.domain.name == "orders"
        assert len(doc.infrastructure.handlers) == 1


class TestAppDoc:
    def test_from_app(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order], name="orders")
        infra = Infrastructure(handlers=[PlaceOrderHandler])
        mod = Module(name="orders", context=bc, infrastructure=infra)
        app = App(name="ecommerce", modules=[mod])
        doc = AppDoc.from_app(app)
        assert doc.name == "ecommerce"
        assert len(doc.modules) == 1
        assert doc.modules[0].name == "orders"


class TestExtractFieldsEdgeCases:
    def test_private_field_skipped(self) -> None:
        class WithPrivate(ValueObject):
            x: int
            _secret: str = "hidden"

        fields = extract_fields(WithPrivate)
        names = {f.name for f in fields}
        assert "x" in names
        assert "_secret" not in names

    def test_class_without_model_fields(self) -> None:
        class NoFields:
            x: int

        assert extract_fields(NoFields) == []


# ============================================================
# HandlerDoc edge cases
# ============================================================


class TestHandlerDocEdgeCases:
    def test_handler_with_session_union(self) -> None:
        """Handler with a Union session type (e.g. MySession | None)."""

        class UnionSessionHandler(CommandHandler[PlaceOrder]):
            session: MySession | None

            def handle(self, command: PlaceOrder) -> None:
                pass

        doc = HandlerDoc.from_handler(UnionSessionHandler)
        assert doc.session == "MySession"

    def test_handler_with_non_generic_base(self) -> None:
        """Handler whose orig_bases includes a non-generic class."""

        class NonGenericBase:
            pass

        class HandlerWithNonGenericBase(NonGenericBase, CommandHandler[PlaceOrder]):
            session: MySession

            def handle(self, command: PlaceOrder) -> None:
                pass

        doc = HandlerDoc.from_handler(HandlerWithNonGenericBase)
        assert doc.name == "HandlerWithNonGenericBase"
        assert doc.session == "MySession"

    def test_handler_session_name_non_session_union(self) -> None:
        """handler _session_name with a Union not containing Session returns empty string."""
        result = handler_session_name(int | str)
        assert result == ""

    def test_handler_session_name_non_type(self) -> None:
        """handler _session_name with a non-type, non-origin value returns str()."""
        result = handler_session_name(42)
        assert result == "42"


# ============================================================
# ProjectionDoc edge cases
# ============================================================


class TestProjectionDocEdgeCases:
    def test_custom_projection_type_fallback(self) -> None:
        """Projection that doesn't match any known type returns empty type."""

        class BaseProj(ReadProjection):
            def read(self, model: object) -> list[Order]:
                return []

        class CustomProj(BaseProj):
            def read(self, model: object) -> list[Order]:
                return []

        doc = ProjectionDoc.from_projection(CustomProj)
        # Falls through to _resolve_projection_type which checks MRO
        assert doc.projection_type in ("ReadProjection", "")

    def test_unknown_projection_type_returns_empty(self) -> None:
        """Projection subclassing ProjectionBase directly returns empty type."""

        class UnknownProj(ProjectionBase):
            def read(self, model: object) -> list[Order]:
                return []

        doc = ProjectionDoc.from_projection(UnknownProj)
        assert doc.projection_type == ""

    def test_projection_with_ports(self) -> None:
        """Projection with a non-session Port field."""

        class ProjWithPort(ReadProjection):
            logger: Logger

            def read(self, model: object) -> list[Order]:
                return []

        doc = ProjectionDoc.from_projection(ProjWithPort)
        port_names = {p.name for p in doc.ports}
        assert "Logger" in port_names

    def test_projection_no_read_write(self) -> None:
        """Projection with neither read nor write gives None for both."""

        class EmptyProj(ReadProjection):
            pass

        doc = ProjectionDoc.from_projection(EmptyProj)
        assert doc.read is None

    def test_projection_with_session_field(self) -> None:
        """Projection with a session field resolves session name."""

        class ProjWithSession(ReadProjection):
            session: MySession

            def read(self, model: object) -> list[Order]:
                return []

        doc = ProjectionDoc.from_projection(ProjWithSession)
        assert doc.session == "MySession"

    def test_projection_with_private_field_skipped(self) -> None:
        """Projection fields starting with _ are skipped."""

        class ProjWithPrivate(ReadProjection):
            logger: Logger
            _internal: str = ""

            def read(self, model: object) -> list[Order]:
                return []

        doc = ProjectionDoc.from_projection(ProjWithPrivate)
        port_names = {p.name for p in doc.ports}
        assert "Logger" in port_names
        assert "_internal" not in [p.name for p in doc.ports]

    def test_projection_session_name_union_session(self) -> None:
        """_session_name with a Union containing Session resolves the Session arg."""
        result = projection_session_name(MySession | None)
        assert result == "MySession"

    def test_projection_session_type_session(self) -> None:
        """Projection with a type[Session] field resolves session name."""

        class ProjStr(ReadProjection):
            session: type[MySession]

            def read(self, model: object) -> list[Order]:
                return []

        doc = ProjectionDoc.from_projection(ProjStr)
        assert doc.session == "MySession"

    def test_projection_session_name_non_session_union(self) -> None:
        """_session_name with a Union not containing Session returns empty string."""
        result = projection_session_name(int | str)
        assert result == ""

    def test_projection_session_name_non_type(self) -> None:
        """_session_name with a non-type, non-origin value returns str()."""
        result = projection_session_name(42)
        assert result == "42"


# ============================================================
# UseCaseDoc edge cases
# ============================================================


class TestUseCaseDocEdgeCases:
    def test_use_case_with_private_fields_skipped(self) -> None:
        """Private fields on a UseCase are skipped."""

        class PrivateUseCase(UseCase):
            logger: Logger
            _secret: str = "hide"

            def run(self) -> None:
                pass

        doc = UseCaseDoc.from_use_case(PrivateUseCase)
        port_names = {p.name for p in doc.ports}
        assert "Logger" in port_names


# ============================================================
# BoundedContextDoc edge cases
# ============================================================


class TestBoundedContextDocEdgeCases:
    def test_from_bounded_context_with_use_cases(self) -> None:
        """BoundedContext with use cases exercises all branches."""
        bc = BoundedContext(
            aggregate_roots=[Order],
            use_cases=[PlaceOrderUseCase],
            name="orders",
        )
        doc = BoundedContextDoc.from_bounded_context(bc)
        assert doc.name == "orders"
        assert len(doc.use_cases) == 1
        assert doc.use_cases[0].name == "PlaceOrderUseCase"


# ============================================================
# describe_utils edge cases - extract_params with bad sig
# ============================================================


class TestExtractParamsEdgeCases:
    def test_non_callable(self) -> None:
        """Non-callable passed to extract_params returns empty list."""
        assert extract_params(42) == []  # ty: ignore[invalid-argument-type]
