from pathlib import Path

from aod._internal.docs.generate import _build_app_doc, _slug, generate_docs
from aod._internal.docs.zensical import generate_zensical_toml
from aod._internal.docs.introspect import (
    _extract_description,
    _extract_fields,
    _extract_methods,
    _extract_params,
    introspect_bounded_context,
    introspect_command,
    introspect_entity,
    introspect_event,
    introspect_exception,
    introspect_handler,
    introspect_port,
    introspect_projection,
    introspect_query,
    introspect_service,
    introspect_session,
    introspect_use_case,
    introspect_value_object,
)
from aod._internal.docs.model import (
    AppDoc,
    ContextDoc,
    ContractDoc,
    DocApp,
    DocInfra,
    EntityDoc,
    EventDoc,
    ExceptionDoc,
    FieldDoc,
    HandlerDoc,
    MethodDoc,
    ParamDoc,
    PortDoc,
    ProjectionDoc,
    ServiceDoc,
    SessionDoc,
    TypeDoc,
    UseCaseDoc,
    ValueObjectDoc,
)
from aod._internal.docs.renderer import (
    render_api_index,
    render_application_commands,
    render_application_index,
    render_application_ports,
    render_application_queries,
    render_application_use_cases,
    render_command,
    render_context,
    render_domain_entities,
    render_domain_events,
    render_domain_index,
    render_domain_services,
    render_domain_value_objects,
    render_entity,
    render_event,
    render_exception,
    render_exceptions,
    render_handler,
    render_home,
    render_infrastructure_handlers,
    render_infrastructure_implementations,
    render_infrastructure_index,
    render_infrastructure_projections,
    render_port,
    render_projection,
    render_query,
    render_service,
    render_session,
    render_use_case,
    render_value_object,
)
from aod._internal.infrastructure.session import Session
from aod.application import Command, Port, Query, UseCase
from aod.domain import BoundedContext, RootEntity, Service, ValueObject
from aod.domain import Field as AodField
from aod.events import Event
from aod.infrastructure import (
    CommandHandler,
    ReadModel,
    ReadProjection,
    WriteModel,
    WriteProjection,
)
from aod.testing.doubles import SpySession


class PetId(ValueObject):
    value: str


class PetName(ValueObject):
    value: str = AodField(description="Display name of the pet")


class Pet(RootEntity):
    id: PetId
    name: PetName
    species: str = AodField(description="Animal species")


class PetCreated(Event):
    pet_id: str
    name: str


class PetClient(Port):
    def save(self, pet: Pet) -> None: ...

    def find(self, pet_id: str) -> Pet | None: ...


PetContext = BoundedContext(aggregate_roots=[Pet], name="pets")


class CreatePet(Command[Pet, None]):
    pet_id: str = AodField(description="Unique identifier")
    name: str
    species: str


class GetPet(Query[Pet, Pet | None]):
    pet_id: str


class CreatePetUseCase(UseCase):
    pet_client: PetClient

    def run(self, pet_id: str, name: str, species: str) -> None:
        """Create a new pet in the system."""
        pass


class PetReadModel(ReadModel):
    pet_id: str


class PetListProjection(ReadProjection):
    def read(self, model: PetReadModel) -> list[Pet]:
        return []


class PetWriteModel(WriteModel):
    pet_id: str
    name: str


class PetUpdateProjection(WriteProjection):
    def write(self, model: PetWriteModel) -> None:
        pass


class SqlPetClient(PetClient):
    def save(self, pet: Pet) -> None: ...

    def find(self, pet_id: str) -> Pet | None: ...


class CreatePetHandler(CommandHandler[CreatePet]):
    session: Session

    def handle(self, command: CreatePet) -> None:
        pass


class PetNotFound(Exception):
    """Raised when a pet is not found."""


class TaxCalculator(Service):
    def calculate(self, amount: float, rate: float) -> float:
        """Calculate tax amount."""
        return amount * rate


def _full_app() -> DocApp:
    return DocApp(
        name="Pet Store",
        description="Sistema de tienda de mascotas",
        bounded_contexts=[PetContext],
        use_cases=[CreatePetUseCase],
        commands=[CreatePet],
        queries=[GetPet],
        ports=[PetClient],
        infra=DocInfra(
            sessions=[SpySession],
            handlers=[CreatePetHandler],
            projections=[PetListProjection, PetUpdateProjection],
            port_impls=[SqlPetClient],
            exceptions=[PetNotFound],
        ),
    )


def test_generate_docs_creates_all_files(tmp_path: Path) -> None:
    result = generate_docs(apps=[_full_app()], output_dir=str(tmp_path))
    assert result.exists()
    assert (result / "zensical.toml").exists()
    docs = result / "docs"
    assert (docs / "index.md").exists()
    app_dir = docs / "pet-store"
    for name in [
        "index.md",
        "domain/index.md",
        "domain/entities.md",
        "domain/value-objects.md",
        "domain/services.md",
        "domain/events.md",
        "application/index.md",
        "application/use-cases.md",
        "application/commands.md",
        "application/queries.md",
        "application/ports.md",
        "infrastructure/index.md",
        "infrastructure/handlers.md",
        "infrastructure/projections.md",
        "infrastructure/implementations.md",
        "exceptions.md",
    ]:
        assert (app_dir / name).exists(), f"Missing {name}"
    assert (docs / "api" / "index.md").exists()


def test_field_descriptions_in_entities(tmp_path: Path) -> None:
    result = generate_docs(apps=[_full_app()], output_dir=str(tmp_path))
    md = (result / "docs" / "pet-store" / "domain" / "entities.md").read_text()
    assert "Animal species" in md


def test_field_descriptions_in_value_objects(tmp_path: Path) -> None:
    result = generate_docs(apps=[_full_app()], output_dir=str(tmp_path))
    md = (result / "docs" / "pet-store" / "domain" / "value-objects.md").read_text()
    assert "Display name of the pet" in md


def test_field_descriptions_in_commands(tmp_path: Path) -> None:
    result = generate_docs(apps=[_full_app()], output_dir=str(tmp_path))
    md = (result / "docs" / "pet-store" / "application" / "commands.md").read_text()
    assert "Unique identifier" in md


def test_use_case_run_params(tmp_path: Path) -> None:
    result = generate_docs(apps=[_full_app()], output_dir=str(tmp_path))
    md = (result / "docs" / "pet-store" / "application" / "use-cases.md").read_text()
    assert "pet_id" in md
    assert "name" in md
    assert "species" in md
    assert "Create a new pet in the system" in md


def test_handler_contract_type(tmp_path: Path) -> None:
    result = generate_docs(apps=[_full_app()], output_dir=str(tmp_path))
    md = (result / "docs" / "pet-store" / "infrastructure" / "handlers.md").read_text()
    assert "CreatePet" in md


def test_exceptions_in_api_reference(tmp_path: Path) -> None:
    result = generate_docs(apps=[_full_app()], output_dir=str(tmp_path))
    md = (result / "docs" / "api" / "index.md").read_text()
    assert "PetNotFound" in md
    assert "Raised when a pet is not found" in md


def test_zensical_toml(tmp_path: Path) -> None:
    result = generate_docs(apps=[_full_app()], output_dir=str(tmp_path))
    toml = (result / "zensical.toml").read_text()
    assert "Pet Store" in toml
    assert "navigation.tabs" in toml
    assert 'variant = "classic"' in toml


def test_multiple_apps(tmp_path: Path) -> None:
    result = generate_docs(
        apps=[
            DocApp(name="App One", description="First"),
            DocApp(name="App Two", description="Second"),
        ],
        output_dir=str(tmp_path),
    )
    assert (result / "docs" / "app-one" / "index.md").exists()
    assert (result / "docs" / "app-two" / "index.md").exists()


def test_introspect_entity() -> None:
    doc = introspect_entity(Pet)
    assert doc.name == "Pet"
    assert doc.stereotype == "RootEntity"
    assert len(doc.fields) >= 3


def test_introspect_value_object() -> None:
    doc = introspect_value_object(PetName)
    assert doc.name == "PetName"
    assert doc.stereotype == "ValueObject"
    assert len(doc.fields) == 1
    assert doc.fields[0].description == "Display name of the pet"


def test_introspect_service() -> None:
    doc = introspect_service(TaxCalculator)
    assert doc.name == "TaxCalculator"
    assert doc.stereotype == "Service"
    assert any(m.name == "calculate" for m in doc.methods)


def test_introspect_event() -> None:
    doc = introspect_event(PetCreated)
    assert doc.name == "PetCreated"
    assert doc.stereotype == "Event"


def test_introspect_port() -> None:
    doc = introspect_port(PetClient)
    assert doc.name == "PetClient"
    assert doc.stereotype == "Port"
    assert any(m.name == "save" for m in doc.methods)


def test_introspect_command() -> None:
    doc = introspect_command(CreatePet)
    assert doc.name == "CreatePet"
    assert doc.stereotype == "Command"
    assert doc.entity_type != ""
    assert len(doc.fields) >= 3


def test_introspect_query() -> None:
    doc = introspect_query(GetPet)
    assert doc.name == "GetPet"
    assert doc.stereotype == "Query"
    assert doc.entity_type != ""


def test_introspect_use_case() -> None:
    doc = introspect_use_case(CreatePetUseCase)
    assert doc.name == "CreatePetUseCase"
    assert doc.stereotype == "UseCase"
    assert len(doc.run_params) == 3
    assert doc.run_returns == "None"
    assert "Create a new pet in the system" in doc.doc


def test_introspect_handler() -> None:
    doc = introspect_handler(CreatePetHandler)
    assert doc.name == "CreatePetHandler"
    assert doc.stereotype == "Handler"
    assert "CreatePet" in doc.contract_type


def test_introspect_projection_read() -> None:
    doc = introspect_projection(PetListProjection)
    assert doc.name == "PetListProjection"
    assert doc.method_name == "read"


def test_introspect_projection_write() -> None:
    doc = introspect_projection(PetUpdateProjection)
    assert doc.name == "PetUpdateProjection"
    assert doc.method_name == "write"


def test_introspect_session() -> None:
    doc = introspect_session(SpySession)
    assert doc.name == "StubSession"
    assert doc.stereotype == "Session"


def test_introspect_exception() -> None:
    doc = introspect_exception(PetNotFound)
    assert doc.name == "PetNotFound"
    assert doc.base == "Exception"
    assert "Raised when a pet is not found" in doc.doc


def test_introspect_bounded_context() -> None:
    doc = introspect_bounded_context(PetContext)
    assert doc.name == "pets"
    assert len(doc.aggregate_roots) == 1
    assert doc.aggregate_roots[0].name == "Pet"


def test_extract_fields_no_model_fields() -> None:
    class NoFields:
        pass

    assert _extract_fields(NoFields) == []


def test_extract_fields_private_field() -> None:
    class WithPrivate(RootEntity):
        _internal: str = "x"
        public: str = "y"

    fields = _extract_fields(WithPrivate)
    names = [f.name for f in fields]
    assert "public" in names
    assert "_internal" not in names


def test_extract_params_bad_signature() -> None:
    params, returns = _extract_params(None)
    assert params == []
    assert returns == ""


def test_extract_methods_empty() -> None:
    class Empty:
        pass

    methods = _extract_methods(Empty)
    assert len(methods) == 0


def test_render_entity_empty() -> None:
    doc = EntityDoc(name="E", stereotype="Entity", doc="", fields=[], methods=[])
    md = render_entity(doc)
    assert "# E" in md


def test_render_value_object_with_methods() -> None:
    doc = ValueObjectDoc(
        name="VO",
        stereotype="ValueObject",
        doc="A value object",
        fields=[FieldDoc(name="x", type_name="str", description="")],
        methods=[
            MethodDoc(name="validate", signature="()", doc="Validates", params=[], returns="bool")
        ],
    )
    md = render_value_object(doc)
    assert "A value object" in md
    assert "validate" in md


def test_render_service_with_fields() -> None:
    doc = ServiceDoc(
        name="S",
        stereotype="Service",
        doc="A service",
        fields=[FieldDoc(name="x", type_name="int", description="")],
        methods=[MethodDoc(name="run", signature="()", doc="", params=[], returns="None")],
    )
    md = render_service(doc)
    assert "A service" in md
    assert "run" in md


def test_render_event() -> None:
    doc = EventDoc(name="E", stereotype="Event", doc="An event", fields=[], methods=[])
    md = render_event(doc)
    assert "# E" in md
    assert "An event" in md


def test_render_port_with_fields_and_methods() -> None:
    doc = PortDoc(
        name="P",
        stereotype="Port",
        doc="A port",
        fields=[FieldDoc(name="x", type_name="str", description="")],
        methods=[MethodDoc(name="do", signature="()", doc="", params=[], returns="None")],
    )
    md = render_port(doc)
    assert "A port" in md


def test_render_command_with_types() -> None:
    doc = ContractDoc(
        name="C",
        stereotype="Command",
        doc="",
        fields=[],
        methods=[],
        entity_type="Pet",
        result_type="None",
    )
    md = render_command(doc)
    assert "Pet" in md


def test_render_query_with_types() -> None:
    doc = ContractDoc(
        name="Q",
        stereotype="Query",
        doc="",
        fields=[],
        methods=[],
        entity_type="Pet",
        result_type="Pet | None",
    )
    md = render_query(doc)
    assert "Pet" in md


def test_render_use_case_minimal() -> None:
    doc = UseCaseDoc(name="UC", stereotype="UseCase", doc="", fields=[], methods=[])
    md = render_use_case(doc)
    assert "# UC" in md


def test_render_handler_minimal() -> None:
    doc = HandlerDoc(name="H", stereotype="Handler", doc="", fields=[], methods=[])
    md = render_handler(doc)
    assert "# H" in md


def test_render_projection_minimal() -> None:
    doc = ProjectionDoc(name="P", stereotype="Projection", doc="", fields=[], methods=[])
    md = render_projection(doc)
    assert "# P" in md


def test_render_session_minimal() -> None:
    doc = SessionDoc(name="S", stereotype="Session", doc="", fields=[], methods=[])
    md = render_session(doc)
    assert "# S" in md


def test_render_exception_minimal() -> None:
    doc = ExceptionDoc(name="E", base="Exception", doc="")
    md = render_exception(doc)
    assert "E" in md


def test_render_context_full() -> None:
    ctx = ContextDoc(
        name="ctx",
        doc="Context",
        aggregate_roots=[
            EntityDoc(name="AR", stereotype="RootEntity", doc="", fields=[], methods=[])
        ],
        entities=[EntityDoc(name="E", stereotype="Entity", doc="", fields=[], methods=[])],
        value_objects=[
            ValueObjectDoc(name="VO", stereotype="ValueObject", doc="", fields=[], methods=[])
        ],
        services=[ServiceDoc(name="S", stereotype="Service", doc="", fields=[], methods=[])],
    )
    md = render_context(ctx)
    assert "ctx" in md
    assert "AR" in md
    assert "E" in md
    assert "VO" in md
    assert "S" in md


def test_render_domain_index_empty() -> None:
    app = AppDoc(
        name="A",
        description="",
        version="",
        repo_url=None,
        contexts=[],
        use_cases=[],
        commands=[],
        queries=[],
        ports=[],
        sessions=[],
        handlers=[],
        projections=[],
        port_impls=[],
        exceptions=[],
    )
    md = render_domain_index(app)
    assert "A" in md


def test_render_domain_entities_child() -> None:
    ctx = ContextDoc(
        name="ctx",
        doc="",
        aggregate_roots=[],
        entities=[EntityDoc(name="Child", stereotype="Entity", doc="", fields=[], methods=[])],
        value_objects=[],
        services=[],
    )
    app = AppDoc(
        name="A",
        description="",
        version="",
        repo_url=None,
        contexts=[ctx],
        use_cases=[],
        commands=[],
        queries=[],
        ports=[],
        sessions=[],
        handlers=[],
        projections=[],
        port_impls=[],
        exceptions=[],
    )
    md = render_domain_entities(app)
    assert "Child" in md


def test_render_domain_value_objects_empty() -> None:
    app = AppDoc(
        name="A",
        description="",
        version="",
        repo_url=None,
        contexts=[],
        use_cases=[],
        commands=[],
        queries=[],
        ports=[],
        sessions=[],
        handlers=[],
        projections=[],
        port_impls=[],
        exceptions=[],
    )
    md = render_domain_value_objects(app)
    assert "Value Objects" in md


def test_render_domain_services_empty() -> None:
    app = AppDoc(
        name="A",
        description="",
        version="",
        repo_url=None,
        contexts=[],
        use_cases=[],
        commands=[],
        queries=[],
        ports=[],
        sessions=[],
        handlers=[],
        projections=[],
        port_impls=[],
        exceptions=[],
    )
    md = render_domain_services(app)
    assert "Services" in md


def test_render_domain_events_empty() -> None:
    app = AppDoc(
        name="A",
        description="",
        version="",
        repo_url=None,
        contexts=[],
        use_cases=[],
        commands=[],
        queries=[],
        ports=[],
        sessions=[],
        handlers=[],
        projections=[],
        port_impls=[],
        exceptions=[],
    )
    md = render_domain_events(app)
    assert "Events" in md


def test_render_application_index_full() -> None:
    app = AppDoc(
        name="A",
        description="",
        version="",
        repo_url=None,
        contexts=[],
        use_cases=[UseCaseDoc(name="UC", stereotype="UseCase", doc="", fields=[], methods=[])],
        commands=[ContractDoc(name="C", stereotype="Command", doc="", fields=[], methods=[])],
        queries=[ContractDoc(name="Q", stereotype="Query", doc="", fields=[], methods=[])],
        ports=[PortDoc(name="P", stereotype="Port", doc="", fields=[], methods=[])],
        sessions=[],
        handlers=[],
        projections=[],
        port_impls=[],
        exceptions=[],
    )
    md = render_application_index(app)
    assert "UC" in md
    assert "C" in md
    assert "Q" in md
    assert "P" in md


def test_render_application_use_cases_empty() -> None:
    app = AppDoc(
        name="A",
        description="",
        version="",
        repo_url=None,
        contexts=[],
        use_cases=[],
        commands=[],
        queries=[],
        ports=[],
        sessions=[],
        handlers=[],
        projections=[],
        port_impls=[],
        exceptions=[],
    )
    md = render_application_use_cases(app)
    assert "Use Cases" in md


def test_render_application_commands_empty() -> None:
    app = AppDoc(
        name="A",
        description="",
        version="",
        repo_url=None,
        contexts=[],
        use_cases=[],
        commands=[],
        queries=[],
        ports=[],
        sessions=[],
        handlers=[],
        projections=[],
        port_impls=[],
        exceptions=[],
    )
    md = render_application_commands(app)
    assert "Commands" in md


def test_render_application_queries_empty() -> None:
    app = AppDoc(
        name="A",
        description="",
        version="",
        repo_url=None,
        contexts=[],
        use_cases=[],
        commands=[],
        queries=[],
        ports=[],
        sessions=[],
        handlers=[],
        projections=[],
        port_impls=[],
        exceptions=[],
    )
    md = render_application_queries(app)
    assert "Queries" in md


def test_render_application_ports_empty() -> None:
    app = AppDoc(
        name="A",
        description="",
        version="",
        repo_url=None,
        contexts=[],
        use_cases=[],
        commands=[],
        queries=[],
        ports=[],
        sessions=[],
        handlers=[],
        projections=[],
        port_impls=[],
        exceptions=[],
    )
    md = render_application_ports(app)
    assert "Ports" in md


def test_render_infrastructure_index_full() -> None:
    app = AppDoc(
        name="A",
        description="",
        version="",
        repo_url=None,
        contexts=[],
        use_cases=[],
        commands=[],
        queries=[],
        ports=[],
        sessions=[],
        handlers=[
            HandlerDoc(
                name="H", stereotype="Handler", doc="", fields=[], methods=[], contract_type="C"
            )
        ],
        projections=[
            ProjectionDoc(
                name="P", stereotype="Projection", doc="", fields=[], methods=[], method_name="read"
            )
        ],
        port_impls=[TypeDoc(name="I", stereotype="Implementation", doc="", fields=[], methods=[])],
        exceptions=[],
    )
    md = render_infrastructure_index(app)
    assert "H" in md
    assert "P" in md
    assert "I" in md


def test_render_infrastructure_handlers_empty() -> None:
    app = AppDoc(
        name="A",
        description="",
        version="",
        repo_url=None,
        contexts=[],
        use_cases=[],
        commands=[],
        queries=[],
        ports=[],
        sessions=[],
        handlers=[],
        projections=[],
        port_impls=[],
        exceptions=[],
    )
    md = render_infrastructure_handlers(app)
    assert "Handlers" in md


def test_render_infrastructure_projections_empty() -> None:
    app = AppDoc(
        name="A",
        description="",
        version="",
        repo_url=None,
        contexts=[],
        use_cases=[],
        commands=[],
        queries=[],
        ports=[],
        sessions=[],
        handlers=[],
        projections=[],
        port_impls=[],
        exceptions=[],
    )
    md = render_infrastructure_projections(app)
    assert "Projections" in md


def test_render_infrastructure_implementations_full() -> None:
    app = AppDoc(
        name="A",
        description="",
        version="",
        repo_url=None,
        contexts=[],
        use_cases=[],
        commands=[],
        queries=[],
        ports=[],
        sessions=[],
        handlers=[],
        projections=[],
        port_impls=[
            TypeDoc(
                name="Impl",
                stereotype="Implementation",
                doc="Impl doc",
                fields=[FieldDoc(name="x", type_name="str", description="")],
                methods=[MethodDoc(name="m", signature="()", doc="", params=[], returns="None")],
            )
        ],
        exceptions=[],
    )
    md = render_infrastructure_implementations(app)
    assert "Impl" in md
    assert "Impl doc" in md


def test_render_exceptions_full() -> None:
    app = AppDoc(
        name="A",
        description="",
        version="",
        repo_url=None,
        contexts=[],
        use_cases=[],
        commands=[],
        queries=[],
        ports=[],
        sessions=[],
        handlers=[],
        projections=[],
        port_impls=[],
        exceptions=[ExceptionDoc(name="Err", base="Exception", doc="An error")],
    )
    md = render_exceptions(app)
    assert "Err" in md
    assert "An error" in md


def test_render_api_index_multiple_apps() -> None:
    apps = [
        AppDoc(
            name="A1",
            description="",
            version="",
            repo_url=None,
            contexts=[],
            use_cases=[],
            commands=[],
            queries=[],
            ports=[],
            sessions=[],
            handlers=[],
            projections=[],
            port_impls=[],
            exceptions=[ExceptionDoc(name="E1", base="Exception", doc="")],
        ),
        AppDoc(
            name="A2",
            description="",
            version="",
            repo_url=None,
            contexts=[],
            use_cases=[],
            commands=[],
            queries=[],
            ports=[],
            sessions=[],
            handlers=[],
            projections=[],
            port_impls=[],
            exceptions=[ExceptionDoc(name="E2", base="Exception", doc="")],
        ),
    ]
    md = render_api_index(apps)
    assert "A1" in md
    assert "A2" in md
    assert "E1" in md
    assert "E2" in md


def test_render_home_multiple_apps() -> None:
    apps = [
        AppDoc(
            name="A1",
            description="Desc1",
            version="1.0",
            repo_url=None,
            contexts=[],
            use_cases=[],
            commands=[],
            queries=[],
            ports=[],
            sessions=[],
            handlers=[],
            projections=[],
            port_impls=[],
            exceptions=[],
        ),
        AppDoc(
            name="A2",
            description="Desc2",
            version="2.0",
            repo_url=None,
            contexts=[],
            use_cases=[],
            commands=[],
            queries=[],
            ports=[],
            sessions=[],
            handlers=[],
            projections=[],
            port_impls=[],
            exceptions=[],
        ),
    ]
    md = render_home(apps)
    assert "A1" in md
    assert "Desc1" in md
    assert "1.0" in md
    assert "A2" in md
    assert "Desc2" in md


def test_slug() -> None:
    assert _slug("Pet Store") == "pet-store"
    assert _slug("My App") == "my-app"
    assert _slug("simple") == "simple"


def test_build_app_doc_minimal() -> None:
    app = DocApp(name="Empty", description="Empty app")
    doc = _build_app_doc(app)
    assert doc.name == "Empty"
    assert doc.contexts == []
    assert doc.use_cases == []
    assert doc.commands == []
    assert doc.queries == []
    assert doc.ports == []
    assert doc.handlers == []
    assert doc.projections == []
    assert doc.port_impls == []
    assert doc.exceptions == []


def test_extract_description_none() -> None:
    class FakeFieldInfo:
        description = None

    assert _extract_description(FakeFieldInfo()) == ""


def test_extract_description_present() -> None:
    class FakeFieldInfo:
        description = "Hello"

    assert _extract_description(FakeFieldInfo()) == "Hello"


def test_methods_skip_init() -> None:
    md = render_entity(
        EntityDoc(
            name="E",
            stereotype="Entity",
            doc="",
            fields=[],
            methods=[MethodDoc(name="__init__", signature="()", doc="", params=[], returns="None")],
        )
    )
    assert "__init__" not in md


def test_methods_with_doc_and_params() -> None:
    md = render_entity(
        EntityDoc(
            name="E",
            stereotype="Entity",
            doc="",
            fields=[],
            methods=[
                MethodDoc(
                    name="do",
                    signature="(x: int)",
                    doc="Does something",
                    params=[ParamDoc(name="x", type_name="int")],
                    returns="bool",
                )
            ],
        )
    )
    assert "Does something" in md
    assert "x" in md
    assert "int" in md
    assert "bool" in md


def test_render_entity_with_doc() -> None:
    doc = EntityDoc(name="E", stereotype="Entity", doc="Entity doc", fields=[], methods=[])
    md = render_entity(doc)
    assert "Entity doc" in md


def test_render_event_with_fields_and_methods() -> None:
    doc = EventDoc(
        name="E",
        stereotype="Event",
        doc="An event",
        fields=[FieldDoc(name="x", type_name="str", description="")],
        methods=[MethodDoc(name="do", signature="()", doc="", params=[], returns="None")],
    )
    md = render_event(doc)
    assert "x" in md
    assert "do" in md


def test_render_command_with_methods() -> None:
    doc = ContractDoc(
        name="C",
        stereotype="Command",
        doc="",
        entity_type="Pet",
        result_type="None",
        fields=[FieldDoc(name="x", type_name="str", description="")],
        methods=[MethodDoc(name="validate", signature="()", doc="", params=[], returns="bool")],
    )
    md = render_command(doc)
    assert "validate" in md


def test_render_query_with_methods() -> None:
    doc = ContractDoc(
        name="Q",
        stereotype="Query",
        doc="",
        entity_type="Pet",
        result_type="Pet | None",
        fields=[FieldDoc(name="x", type_name="str", description="")],
        methods=[MethodDoc(name="validate", signature="()", doc="", params=[], returns="bool")],
    )
    md = render_query(doc)
    assert "validate" in md


def test_render_projection_with_doc() -> None:
    doc = ProjectionDoc(
        name="P",
        stereotype="Projection",
        doc="Projection doc",
        fields=[],
        methods=[],
        method_name="read",
        model_type="ReadModel",
    )
    md = render_projection(doc)
    assert "Projection doc" in md


def test_render_session_with_doc_fields_methods() -> None:
    doc = SessionDoc(
        name="S",
        stereotype="Session",
        doc="Session doc",
        fields=[FieldDoc(name="x", type_name="str", description="")],
        methods=[MethodDoc(name="execute", signature="()", doc="", params=[], returns="None")],
    )
    md = render_session(doc)
    assert "Session doc" in md
    assert "execute" in md


def test_render_exception_with_doc() -> None:
    doc = ExceptionDoc(name="E", base="Exception", doc="Error doc")
    md = render_exception(doc)
    assert "Error doc" in md
    assert "Exception" in md


def test_render_domain_services_with_services() -> None:
    ctx = ContextDoc(
        name="ctx",
        doc="",
        aggregate_roots=[],
        entities=[],
        value_objects=[],
        services=[ServiceDoc(name="S", stereotype="Service", doc="", fields=[], methods=[])],
    )
    app = AppDoc(
        name="A",
        description="",
        version="",
        repo_url=None,
        contexts=[ctx],
        use_cases=[],
        commands=[],
        queries=[],
        ports=[],
        sessions=[],
        handlers=[],
        projections=[],
        port_impls=[],
        exceptions=[],
    )
    md = render_domain_services(app)
    assert "S" in md


def test_render_domain_events_with_emit() -> None:
    ctx = ContextDoc(
        name="ctx",
        doc="",
        aggregate_roots=[
            EntityDoc(
                name="AR",
                stereotype="RootEntity",
                doc="",
                fields=[],
                methods=[MethodDoc(name="emit", signature="()", doc="", params=[], returns="None")],
            )
        ],
        entities=[],
        value_objects=[],
        services=[],
    )
    app = AppDoc(
        name="A",
        description="",
        version="",
        repo_url=None,
        contexts=[ctx],
        use_cases=[],
        commands=[],
        queries=[],
        ports=[],
        sessions=[],
        handlers=[],
        projections=[],
        port_impls=[],
        exceptions=[],
    )
    md = render_domain_events(app)
    assert "AR" in md


def test_render_home_with_repo_url() -> None:
    app = AppDoc(
        name="A",
        description="Desc",
        version="1.0",
        repo_url="https://github.com/test",
        contexts=[],
        use_cases=[],
        commands=[],
        queries=[],
        ports=[],
        sessions=[],
        handlers=[],
        projections=[],
        port_impls=[],
        exceptions=[],
    )
    md = render_home([app])
    assert "https://github.com/test" in md


def test_render_home_with_contexts() -> None:
    ctx = ContextDoc(
        name="ctx", doc="", aggregate_roots=[], entities=[], value_objects=[], services=[]
    )
    app = AppDoc(
        name="A",
        description="Desc",
        version="1.0",
        repo_url=None,
        contexts=[ctx],
        use_cases=[],
        commands=[],
        queries=[],
        ports=[],
        sessions=[],
        handlers=[],
        projections=[],
        port_impls=[],
        exceptions=[],
    )
    md = render_home([app])
    assert "ctx" in md


def test_zensical_empty_apps() -> None:
    toml = generate_zensical_toml([])
    assert "Documentation" in toml


def test_use_case_with_class_doc_and_run_doc() -> None:
    class MyUseCase(UseCase):
        """Class doc."""

        def run(self) -> None:
            """Run doc."""
            pass

    doc = introspect_use_case(MyUseCase)
    assert "Class doc" in doc.doc
    assert "Run doc" in doc.doc
