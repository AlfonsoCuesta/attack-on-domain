from typing import Annotated, Any, Self

from .base_mutable import BaseMutable
from .base_validator import BaseValidator
from .fields.fields import Field, PrivateField
from .validators import (
    AfterValidator,
    field_validator,
    post_init,
)

print(BaseValidator)
print(BaseMutable)


def text(value: Any) -> str:
    return "Hola"


def main() -> None:
    class Prueba:
        def __init__(self, a: int) -> None:
            self.a = a

    class User(BaseMutable):
        age: int = 0
        _prueba: int = PrivateField()

        @field_validator("age")
        def is_even(cls, value: int) -> int:
            return 22

        @post_init
        def validate_age(self) -> Self:
            return self

    class User2(User):
        a: int = Field()
        text: Annotated[str, AfterValidator(text)]
        prueba_attr: Prueba

        def change_text(self, text: str) -> None:
            self.text = text

        def can_mutate(self) -> bool:
            return self.text != "Adio"

        def prueba(self) -> None:
            print("prueba")

    prueba = Prueba(a=1)
    a = User2(text="Adio", age=2, a=1, prueba_attr=prueba)


if __name__ == "__main__":
    main()
