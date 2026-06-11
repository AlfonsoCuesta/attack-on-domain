from typing import Any, Callable, NoReturn

from ...domain_exception import MutationForbiddenException


class ImmutableDict(dict):
    __immutable_class__ = dict

    def __init__(self, data: Any, factory: Callable[..., Any]) -> None:
        super().__init__(data)
        self.__factory__ = factory

    def _block_mutation(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise MutationForbiddenException("Cannot modify an immutable dict")

    __setitem__ = __delitem__ = update = _block_mutation
    pop = popitem = clear = setdefault = _block_mutation

    def __getitem__(self, key: Any) -> Any:
        item = super().__getitem__(key)
        return self.__factory__(item)

    def __iter__(self) -> Any:
        for key in super().__iter__():
            yield self.__factory__(key)

    def get(self, key: Any, default: Any = None) -> Any:
        if key not in self:
            return self.__factory__(default)
        return self.__factory__(self[key])

    def items(self) -> Any:
        for key, value in super().items():
            yield self.__factory__(key), self.__factory__(value)

    def keys(self) -> Any:
        for key in super().keys():
            yield self.__factory__(key)

    def values(self) -> Any:
        for value in super().values():
            yield self.__factory__(value)
