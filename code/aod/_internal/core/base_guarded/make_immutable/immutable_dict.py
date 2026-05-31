from typing import Any, Callable

from ...domain_exception import MutationForbiddenException


class ImmutableDict(dict):
    __immutable_class__ = dict

    def __init__(self, object: Any, factory: Callable):
        super().__init__(object)
        self.__factory__ = factory

    def _raise(self, *args, **kwargs):
        raise MutationForbiddenException("Cannot modify an immutable dict")

    __setitem__ = __delitem__ = update = _raise
    pop = popitem = clear = setdefault = _raise

    def __getitem__(self, key):
        item = super().__getitem__(key)
        return self.__factory__(item)

    def __iter__(self):
        for key in super().__iter__():
            yield self.__factory__(key)

    def get(self, key, default=None):
        if key not in self:
            return self.__factory__(default)
        return self.__factory__(self[key])

    def items(self):
        for key, value in super().items():
            yield self.__factory__(key), self.__factory__(value)

    def keys(self):
        for key in super().keys():
            yield self.__factory__(key)

    def values(self):
        for value in super().values():
            yield self.__factory__(value)
