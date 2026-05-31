import inspect

from aod._internal.domain.describe import TypeDoc, _extract_fields, _extract_methods
from aod._internal.domain.service import Service


class ServiceDescriber:
    @staticmethod
    def describe(cls: type[Service], stereotype: str = "Service") -> TypeDoc:
        return TypeDoc(
            name=cls.__name__,
            stereotype=stereotype,
            doc=inspect.getdoc(cls) or "",
            fields=_extract_fields(cls),
            methods=_extract_methods(cls),
        )
