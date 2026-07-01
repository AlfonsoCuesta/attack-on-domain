from pydantic import BaseModel, ConfigDict


class DTO(BaseModel):
    """Application-layer Data Transfer Object.

    Pure data carrier with no mutation guards, event emission, or identity.
    Inherits directly from ``BaseModel`` for full FastAPI compatibility
    (``Depends()``, OpenAPI schema generation, ``model_validate_json()``, etc.).

    Use ``DTO`` for:
    - ``UseCase.run()`` input — avoids many-parameter signatures
    - API request/response contracts (FastAPI, Pydantic settings)
    - Projection input models (replaces ``ReadModel`` / ``WriteModel``)

    ``DTO`` is **not** part of the domain layer. It does not inherit from
    ``BaseValidator``, ``BaseGuarded``, or any domain framework base class.
    It has no ``_event_emitter``, no mutation restrictions, and no identity field.

    Example::

        from aod.application import DTO, UseCase

        class CreateUserInput(DTO):
            name: str
            email: str

        class CreateUser(UseCase):
            create_user: CommandPort[CreateUserCommand]

            def run(self, dto: CreateUserInput) -> User:
                user = User(id=generate_id(), name=dto.name, email=dto.email)
                self.create_user.handle(CreateUserCommand(
                    user_id=user.id, name=dto.name, email=dto.email,
                ))
                return user
    """

    model_config = ConfigDict(extra="forbid")
