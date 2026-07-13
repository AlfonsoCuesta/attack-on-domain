from __future__ import annotations

from typing import Any, get_type_hints

from aod._internal.application.port import Port
from aod._internal.core.base_operation import BaseOperation
from aod._internal.core.infrastructure_exception import PortNotFoundError
from aod._internal.infrastructure.container.types import _is_port_type


class PortManager:
    def __init__(
        self,
        ports: dict[type[Port], Port] | None = None,
        instance: Any | None = None,
        extra_ports: dict[str, Port] | None = None,
    ) -> None:
        self.ports: dict[type[Port], Port] = ports if ports is not None else {}
        self.ports_by_name: dict[str, Port] = {}
        if instance is not None:
            self._build_index(instance, extra_ports)

    def _build_index(self, instance: Any, extra_ports: dict[str, Port] | None = None) -> None:
        model_fields = type(instance).__model_fields__
        hints = get_type_hints(type(instance))
        for name in model_fields:
            tp = hints.get(name)
            if tp is None or not _is_port_type(tp):
                continue
            value = object.__getattribute__(instance, name)
            if isinstance(value, Port):
                self.ports_by_name[name] = value
        if extra_ports is not None:
            self.ports_by_name.update(extra_ports)

    def resolve_by_type(self, field_type: type[Port]) -> Port | None:
        return self.ports.get(field_type)

    def get_port(self, name: str) -> Port:
        if name in self.ports_by_name:
            return self.ports_by_name[name]
        raise PortNotFoundError(name)

    def inject_ports(self, operation_cls: type[BaseOperation], kwargs: dict[str, Any]) -> None:
        own_annotations = getattr(operation_cls, "__annotations__", {})
        for field_name, field_info in operation_cls.__model_fields__.items():
            if field_name not in own_annotations:
                continue
            if field_name in kwargs:
                continue
            field_type = field_info.annotation
            if field_type is None or not _is_port_type(field_type):
                continue
            if field_name in self.ports_by_name:
                kwargs[field_name] = self.ports_by_name[field_name]
                continue
            if isinstance(field_type, type):
                resolved = self.resolve_by_type(field_type)
                if resolved is not None:
                    kwargs[field_name] = resolved
                    continue
            raise PortNotFoundError(field_name)
