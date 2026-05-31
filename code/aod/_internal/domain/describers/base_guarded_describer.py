import inspect

from aod._internal.core.base_guarded import BaseGuarded
from aod._internal.domain.describe import TypeDoc, _extract_fields, _extract_methods


class BaseGuardedDescriber:
    @staticmethod
    def describe(cls: type[BaseGuarded], stereotype: str = "Entity") -> TypeDoc:
        return TypeDoc(
            name=cls.__name__,
            stereotype=stereotype,
            doc=inspect.getdoc(cls) or "",
            fields=_extract_fields(cls),
            methods=_extract_methods(cls),
        )
